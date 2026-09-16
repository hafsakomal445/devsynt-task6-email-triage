import os
import pickle
import faiss
import numpy as np
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
INDEX_PATH = "../data/faiss_index.bin"
METADATA_PATH = "../data/chunk_metadata.pkl"

embedder = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)


class VectorStore:
    def __init__(self):
        self.index = None
        self.metadata = []  # list of chunk dicts, same order as vectors in FAISS
        self._load()

    def _load(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(METADATA_PATH, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = None
            self.metadata = []

    def _save(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(METADATA_PATH, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_chunks(self, chunks: list[dict]):
        """Embed and add a list of chunk dicts (from chunking.py) to the index."""
        texts = [c["text"] for c in chunks]
        vectors = embedder.embed_documents(texts)
        vectors = np.array(vectors, dtype="float32")

        if self.index is None:
            dim = vectors.shape[1]
            self.index = faiss.IndexFlatL2(dim)

        self.index.add(vectors)
        self.metadata.extend(chunks)
        self._save()

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        """Return the top_k most relevant chunks for a query."""
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vector = np.array([embedder.embed_query(query)], dtype="float32")
        distances, indices = self.index.search(query_vector, top_k)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            chunk = self.metadata[idx].copy()
            chunk["distance"] = float(dist)
            results.append(chunk)
        return results
    def remove_by_doc_id(self, doc_id: str):
        """Remove all chunks belonging to a document, then rebuild the index."""
        keep = [c for c in self.metadata if c["doc_id"] != doc_id]
        if not keep:
            self.index = None
            self.metadata = []
            if os.path.exists(INDEX_PATH):
                os.remove(INDEX_PATH)
            if os.path.exists(METADATA_PATH):
                os.remove(METADATA_PATH)
            return

        texts = [c["text"] for c in keep]
        vectors = embedder.embed_documents(texts)
        vectors = np.array(vectors, dtype="float32")

        dim = vectors.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(vectors)
        self.metadata = keep
        self._save()