import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from document_store import DocumentStore, ChatStats
from vectorstore import VectorStore
from ingestion import extract_text
from chunking import chunk_document
from rag import answer_question

app = FastAPI(title="DevSynt RAG Chatbot API")

# Allow the Streamlit dashboard (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "../data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

doc_store = DocumentStore()
vs = VectorStore()
chat_stats = ChatStats()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_id = doc_store.add_document(file.filename)
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}{ext}")

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        pages = extract_text(save_path)
        chunks = chunk_document(doc_id=doc_id, doc_name=file.filename, pages=pages)

        if not chunks:
            doc_store.mark_failed(doc_id, "No extractable text found in document.")
            raise HTTPException(status_code=422, detail="No extractable text found in document.")

        vs.add_chunks(chunks)
        doc_store.mark_processed(doc_id, chunk_count=len(chunks))

        return {"doc_id": doc_id, "filename": file.filename, "status": "processed", "chunks": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        doc_store.mark_failed(doc_id, str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/documents")
async def list_documents():
    return doc_store.get_all()


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for candidate_ext in ALLOWED_EXTENSIONS:
        path = os.path.join(UPLOAD_DIR, f"{doc_id}{candidate_ext}")
        if os.path.exists(path):
            os.remove(path)
            break

    vs.remove_by_doc_id(doc_id)
    doc_store.delete(doc_id)

    return {"deleted": doc_id}


@app.post("/documents/{doc_id}/reprocess")
async def reprocess_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ext = None
    for candidate_ext in ALLOWED_EXTENSIONS:
        path = os.path.join(UPLOAD_DIR, f"{doc_id}{candidate_ext}")
        if os.path.exists(path):
            ext = candidate_ext
            break

    if not ext:
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}{ext}")
    vs.remove_by_doc_id(doc_id)

    try:
        pages = extract_text(save_path)
        chunks = chunk_document(doc_id=doc_id, doc_name=doc["filename"], pages=pages)
        vs.add_chunks(chunks)
        doc_store.mark_processed(doc_id, chunk_count=len(chunks))
        return {"doc_id": doc_id, "status": "processed", "chunks": len(chunks)}
    except Exception as e:
        doc_store.mark_failed(doc_id, str(e))
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = answer_question(vs, request.question)
        chat_stats.increment()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@app.get("/stats")
async def get_stats():
    docs = doc_store.get_all()
    return {
        "total_documents": len(docs),
        "processed": len([d for d in docs if d["status"] == "processed"]),
        "processing": len([d for d in docs if d["status"] == "processing"]),
        "failed": len([d for d in docs if d["status"] == "failed"]),
        "total_indexed_chunks": vs.index.ntotal if vs.index else 0,
        "total_chats": chat_stats.total_chats,
    }