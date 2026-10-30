
from pathlib import Path
from docx import Document


def read_docx(file_path: str | Path) -> dict:
    """Extract paragraphs and table content from a DOCX file."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    if path.suffix.lower() != ".docx":
        raise ValueError("Only DOCX files are supported.")

    document = Document(path)

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    tables = []

    for table_number, table in enumerate(document.tables, start=1):
        for row_number, row in enumerate(table.rows, start=1):
            cells = [
                cell.text.strip().replace("\n", " ")
                for cell in row.cells
            ]

            if any(cells):
                tables.append({
                    "table_number": table_number,
                    "row_number": row_number,
                    "content": " | ".join(cells),
                })

    return {
        "filename": path.name,
        "paragraph_count": len(paragraphs),
        "table_row_count": len(tables),
        "paragraphs": paragraphs,
        "tables": tables,
        "full_text": "\n".join(
            paragraphs + [item["content"] for item in tables]
        ),
    }
