import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
def chunk_document(doc_id: str, doc_name: str, pages: list[dict],
                    chunk_size: int = 500, chunk_overlap: int = 80) -> list[dict]:
    """
    Takes pages (from ingestion.py) and returns a list of chunk dicts:
    { "chunk_id", "doc_id", "doc_name", "page", "text" }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for page in pages:
        page_chunks = splitter.split_text(page["text"])
        for chunk_text in page_chunks:
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page": page["page"],
                "text": chunk_text,
            })
    return chunks