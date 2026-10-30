
import csv
from pathlib import Path

from docx import Document
from pypdf import PdfReader
from openpyxl import load_workbook
import xlrd
from pptx import Presentation
from bs4 import BeautifulSoup


SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls",
    ".pptx", ".txt", ".csv", ".md",
    ".html", ".htm",
}


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to decode text file.")


def _read_docx(path: Path) -> tuple[list, list, list]:
    doc = Document(path)

    paragraphs = []
    tables = []
    segments = []
    current_section = None

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()

        if not text:
            continue

        style_name = paragraph.style.name if paragraph.style else ""

        if style_name.startswith("Heading"):
            current_section = text

        paragraphs.append(text)

        segments.append({
            "text": text,
            "section": current_section,
            "page_number": None,
        })

    for table_no, table in enumerate(doc.tables, start=1):
        for row_no, row in enumerate(table.rows, start=1):
            cells = [
                cell.text.strip().replace("\n", " ")
                for cell in row.cells
            ]

            if any(cells):
                content = " | ".join(cells)

                tables.append({
                    "table_number": table_no,
                    "row_number": row_no,
                    "content": content,
                })

                segments.append({
                    "text": content,
                    "section": current_section,
                    "table_number": table_no,
                    "row_number": row_no,
                    "page_number": None,
                })

    return paragraphs, tables, segments


def _read_pdf(path: Path) -> tuple[list, list, list]:
    reader = PdfReader(path)

    paragraphs = []
    segments = []

    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            content = text.strip()
            paragraphs.append(f"[Page {page_no}]\n{content}")

            segments.append({
                "text": content,
                "page_number": page_no,
            })

    return paragraphs, [], segments


def _read_excel_xlsx(path: Path) -> tuple[list, list, list]:
    workbook = load_workbook(
        path,
        read_only=True,
        data_only=True
    )

    paragraphs = []
    segments = []

    try:
        for sheet in workbook.worksheets:
            paragraphs.append(f"[Sheet: {sheet.title}]")

            for row_no, row in enumerate(
                sheet.iter_rows(values_only=True),
                start=1,
            ):
                values = [
                    str(value) if value is not None else ""
                    for value in row
                ]

                if any(value.strip() for value in values):
                    content = " | ".join(values)
                    paragraphs.append(content)

                    segments.append({
                        "text": content,
                        "sheet_name": sheet.title,
                        "row_number": row_no,
                    })
    finally:
        workbook.close()

    return paragraphs, [], segments


def _read_excel_xls(path: Path) -> tuple[list, list, list]:
    workbook = xlrd.open_workbook(str(path))

    paragraphs = []
    segments = []

    for sheet in workbook.sheets():
        paragraphs.append(f"[Sheet: {sheet.name}]")

        for row_no in range(sheet.nrows):
            values = [
                str(value) if value is not None else ""
                for value in sheet.row_values(row_no)
            ]

            if any(value.strip() for value in values):
                content = " | ".join(values)
                paragraphs.append(content)

                segments.append({
                    "text": content,
                    "sheet_name": sheet.name,
                    "row_number": row_no + 1,
                })

    return paragraphs, [], segments


def _read_pptx(path: Path) -> tuple[list, list, list]:
    presentation = Presentation(path)

    paragraphs = []
    segments = []

    for slide_no, slide in enumerate(
        presentation.slides,
        start=1,
    ):
        paragraphs.append(f"[Slide {slide_no}]")

        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text.strip()

                if text:
                    paragraphs.append(text)

                    segments.append({
                        "text": text,
                        "slide_number": slide_no,
                    })

            if shape.has_table:
                for row_no, row in enumerate(
                    shape.table.rows,
                    start=1,
                ):
                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                    ]

                    if any(cells):
                        content = " | ".join(cells)
                        paragraphs.append(content)

                        segments.append({
                            "text": content,
                            "slide_number": slide_no,
                            "table_number": 1,
                            "row_number": row_no,
                        })

    return paragraphs, [], segments


def _read_csv(path: Path) -> tuple[list, list, list]:
    text = _read_text_file(path)

    paragraphs = []
    segments = []

    for row_no, row in enumerate(
        csv.reader(text.splitlines()),
        start=1,
    ):
        if any(cell.strip() for cell in row):
            content = " | ".join(row)
            paragraphs.append(content)

            segments.append({
                "text": content,
                "row_number": row_no,
            })

    return paragraphs, [], segments


def _read_html(path: Path) -> tuple[list, list, list]:
    html = _read_text_file(path)
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    paragraphs = []
    segments = []
    current_section = None

    for element in soup.find_all(
        ["h1", "h2", "h3", "p", "li", "td", "th"]
    ):
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if element.name in {"h1", "h2", "h3"}:
            current_section = text

        paragraphs.append(text)

        segments.append({
            "text": text,
            "section": current_section,
        })

    return paragraphs, [], segments


def read_document(file_path: str | Path) -> dict:
    """Extract text and source metadata from supported documents."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    if extension == ".docx":
        paragraphs, tables, segments = _read_docx(path)

    elif extension == ".pdf":
        paragraphs, tables, segments = _read_pdf(path)

    elif extension == ".xlsx":
        paragraphs, tables, segments = _read_excel_xlsx(path)

    elif extension == ".xls":
        paragraphs, tables, segments = _read_excel_xls(path)

    elif extension == ".pptx":
        paragraphs, tables, segments = _read_pptx(path)

    elif extension == ".csv":
        paragraphs, tables, segments = _read_csv(path)

    elif extension in {".html", ".htm"}:
        paragraphs, tables, segments = _read_html(path)

    else:
        text = _read_text_file(path)

        paragraphs = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        segments = [
            {"text": line}
            for line in paragraphs
        ]

        tables = []

    full_text = "\n".join(
        segment["text"] for segment in segments
    )

    return {
        "filename": path.name,
        "paragraph_count": len(paragraphs),
        "table_row_count": len(tables),
        "paragraphs": paragraphs,
        "tables": tables,
        "segments": segments,
        "full_text": full_text,
    }


def read_docx(file_path: str | Path) -> dict:
    path = Path(file_path)

    if path.suffix.lower() != ".docx":
        raise ValueError("Only DOCX files are supported.")

    return read_document(path)
