
from pathlib import Path

from app.services.document_reader import read_docx
from app.services.chunking import create_chunks
from app.services.embeddings import EmbeddingService


files = list(Path("data/raw").glob("*.docx"))

if not files:
    print("ERROR: No DOCX file found in data/raw")
else:
    document = read_docx(files[0])
    chunks = create_chunks(document["full_text"])

    embedding_service = EmbeddingService()
    vectors = embedding_service.embed_texts(chunks)

    print("EMBEDDING SUCCESS")
    print("Chunks:", len(chunks))
    print("Vectors:", len(vectors))
    print("Vector dimensions:", len(vectors[0]) if vectors else 0)
    print("First vector values:", vectors[0][:5] if vectors else [])
