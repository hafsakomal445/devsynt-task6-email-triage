from ingestion import extract_text

pages = extract_text("../data/sample_pdfs/Company_Overview.pdf")
for p in pages:
    print(f"--- Page {p['page']} ---")
    print(p['text'][:200])  # first 200 chars
    print()