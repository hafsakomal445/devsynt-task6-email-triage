from ingestion import extract_text
from chunking import chunk_document
from vectorstore import VectorStore

pages = extract_text("../data/sample_pdfs/Property_Listings.pdf")
chunks = chunk_document(doc_id="doc-001", doc_name="Property_Listings.pdf", pages=pages)

vs = VectorStore()
vs.add_chunks(chunks)
print(f"Indexed {len(chunks)} chunks. Total in store: {vs.index.ntotal}")

results = vs.search("What is the price of the Sunridge Villa?", top_k=3)
for r in results:
    print(f"\n[dist={r['distance']:.3f}] {r['doc_name']} - page {r['page']}")
    print(r['text'][:150])