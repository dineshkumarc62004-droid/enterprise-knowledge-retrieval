
from pathlib import Path

from app.services.document_reader import read_docx
from app.services.chunking import create_chunks

files = list(Path("data/raw").glob("*.docx"))

if not files:
    print("ERROR: No DOCX file found.")
else:
    result = read_docx(files[0])
    chunks = create_chunks(result["full_text"])

    print("CHUNKING SUCCESS")
    print("Document:", result["filename"])
    print("Total chunks:", len(chunks))

    for index, chunk in enumerate(chunks[:3], start=1):
        print(f"\n--- CHUNK {index} ---")
        print(chunk)
