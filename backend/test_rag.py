from ingestion import extract_text
from chunking import chunk_document
from vectorstore import VectorStore
from rag import answer_question

# Only run this once to build the index — comment out after first run
vs = VectorStore()

result = answer_question(vs, "What is the price of the Sunridge Villa?")
print("ANSWER:", result["answer"])
print("SOURCES:", result["sources"])

print("\n---\n")

result2 = answer_question(vs, "Do you sell commercial office buildings?")
print("ANSWER:", result2["answer"])
print("SOURCES:", result2["sources"])