import os
import json
import uuid
from datetime import datetime

REGISTRY_PATH = "../data/documents.json"


class DocumentStore:
    def __init__(self):
        self.documents = {}  # doc_id -> metadata dict
        self._load()

    def _load(self):
        if os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, "r") as f:
                self.documents = json.load(f)
        else:
            self.documents = {}

    def _save(self):
        with open(REGISTRY_PATH, "w") as f:
            json.dump(self.documents, f, indent=2)

    def add_document(self, filename: str) -> str:
        doc_id = str(uuid.uuid4())
        self.documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "status": "processing",   # processing | processed | failed
            "chunk_count": 0,
            "uploaded_at": datetime.utcnow().isoformat(),
            "error": None,
        }
        self._save()
        return doc_id

    def mark_processed(self, doc_id: str, chunk_count: int):
        self.documents[doc_id]["status"] = "processed"
        self.documents[doc_id]["chunk_count"] = chunk_count
        self._save()

    def mark_failed(self, doc_id: str, error: str):
        self.documents[doc_id]["status"] = "failed"
        self.documents[doc_id]["error"] = error
        self._save()

    def get_all(self) -> list[dict]:
        return list(self.documents.values())

    def get(self, doc_id: str) -> dict | None:
        return self.documents.get(doc_id)

    def delete(self, doc_id: str):
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save()
class ChatStats:
    def __init__(self):
        self.path = "../data/chat_stats.json"
        self.total_chats = 0
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.total_chats = json.load(f).get("total_chats", 0)

    def increment(self):
        self.total_chats += 1
        with open(self.path, "w") as f:
            json.dump({"total_chats": self.total_chats}, f)