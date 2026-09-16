import os
from pypdf import PdfReader
from docx import Document

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """Returns a list of {"page": int, "text": str} for each page."""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    return pages

def extract_text_from_docx(file_path: str) -> list[dict]:
    """DOCX has no real 'pages', so we treat the whole doc as page 1."""
    doc = Document(file_path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"page": 1, "text": text}] if text else []

def extract_text_from_txt(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    return [{"page": 1, "text": text}] if text else []

def extract_text(file_path: str) -> list[dict]:
    """Dispatch based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")