
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be non-negative and smaller than chunk_size."
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )


def create_chunks(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[str]:
    """Split plain text into overlapping chunks."""

    if not text or not text.strip():
        return []

    splitter = get_splitter(chunk_size, chunk_overlap)

    return splitter.split_text(text)


def create_document_chunks(
    segments: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict]:
    """
    Split document segments while preserving source metadata.

    Each returned item contains:
    - text
    - page_number
    - section
    - slide_number
    - sheet_name
    - table_number
    - row_number
    """

    if not segments:
        return []

    splitter = get_splitter(chunk_size, chunk_overlap)
    document_chunks = []

    for segment in segments:
        text = str(segment.get("text", "")).strip()

        if not text:
            continue

        metadata = {
            "page_number": segment.get("page_number"),
            "section": segment.get("section"),
            "slide_number": segment.get("slide_number"),
            "sheet_name": segment.get("sheet_name"),
            "table_number": segment.get("table_number"),
            "row_number": segment.get("row_number"),
        }

        text_chunks = splitter.split_text(text)

        for chunk in text_chunks:
            document_chunks.append({
                "text": chunk,
                **metadata,
            })

    return document_chunks
