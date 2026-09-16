import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from vectorstore import VectorStore

load_dotenv()

CHAT_MODEL = "gemini-3.6-flash"  # fast + cheap, good for this use case
DISTANCE_THRESHOLD = 1.35  # tuned up from 1.2 — compound/multi-topic questions were being filtered out

llm = ChatGoogleGenerativeAI(model=CHAT_MODEL, temperature=0)

SYSTEM_PROMPT = """You are a helpful assistant answering questions ONLY using the provided document excerpts.

Rules:
- Only use information found in the excerpts below. Do not use outside knowledge.
- If the excerpts do not contain the answer, respond exactly: "I couldn't find that information in the uploaded documents."
- Be concise and direct.
- Do not make up details, prices, or facts not present in the excerpts.
"""

def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Source: {c['doc_name']} - Page {c['page']}]\n{c['text']}"
        for c in chunks
    )
    return f"""{SYSTEM_PROMPT}

Document excerpts:
{context}

Question: {question}

Answer:"""


def extract_text(response) -> str:
    """Handle both plain string and structured content block responses."""
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
        return "".join(parts).strip()
    return str(content)


def answer_question(vs: VectorStore, question: str, top_k: int = 6) -> dict:
    chunks = vs.search(question, top_k=top_k)
    relevant_chunks = [c for c in chunks if c["distance"] < DISTANCE_THRESHOLD]

    if not relevant_chunks:
        return {"answer": "I couldn't find that information in the uploaded documents.", "sources": [], "grounded": False}

    prompt = build_prompt(question, relevant_chunks)
    response = llm.invoke(prompt)
    answer_text = extract_text(response)

    # Don't show sources if the model itself says it couldn't find the answer
    if "couldn't find" in answer_text.lower():
        return {"answer": answer_text, "sources": [], "grounded": False}

    sources = [{"doc_name": c["doc_name"], "page": c["page"]} for c in relevant_chunks]
    seen = set()
    unique_sources = []
    for s in sources:
        key = (s["doc_name"], s["page"])
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)

    return {"answer": answer_text, "sources": unique_sources, "grounded": True}