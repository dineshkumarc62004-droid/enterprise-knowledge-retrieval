
from pathlib import Path
from app.services.document_reader import read_docx

upload_folder = Path("data/raw")
files = list(upload_folder.glob("*.docx"))

if not files:
    print("ERROR: No DOCX file found in data/raw")
else:
    file_path = files[0]
    result = read_docx(file_path)

    print("DOCUMENT READING SUCCESS")
    print("Filename:", result["filename"])
    print("Paragraph count:", result["paragraph_count"])
    print("Table rows:", result["table_row_count"])
    print("\nEXTRACTED TEXT PREVIEW:\n")
    print(result["full_text"][:2000])
