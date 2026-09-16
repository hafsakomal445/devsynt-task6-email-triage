print("Script started")

from ingestion import extract_text
from chunking import chunk_document

print("Imports OK")

pages = extract_text("../data/sample_pdfs/Property_Listings.pdf")
print(f"Pages extracted: {len(pages)}")

chunks = chunk_document(doc_id="doc-001", doc_name="Property_Listings.pdf", pages=pages)
print(f"Total chunks: {len(chunks)}")

for c in chunks[:3]:
    print(f"\n[{c['chunk_id'][:8]}] page {c['page']}")
    print(c['text'])