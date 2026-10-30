
from pathlib import Path
from uuid import uuid4

from app.services.document_reader import read_docx
from app.services.chunking import create_chunks
from app.services.embeddings import EmbeddingService
from app.storage.qdrant_store import QdrantStore


def main():
    files = list(Path("data/raw").glob("*.docx"))

    if not files:
        print("ERROR: No DOCX file found in data/raw")
        return

    document = read_docx(files[0])
    chunks = create_chunks(document["full_text"])

    embedding_service = EmbeddingService()
    vectors = embedding_service.embed_texts(chunks)

    store = QdrantStore()

    try:
        points = []

        for index, (chunk, vector) in enumerate(
            zip(chunks, vectors), start=1
        ):
            points.append({
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "document_id": document["filename"],
                    "chunk_index": index,
                    "text": chunk,
                    "access_tag": "general",
                },
            })

        store.upsert_chunks(points)

        info = store.client.get_collection(
            collection_name=store.collection_name
        )

        print("QDRANT STORAGE SUCCESS")
        print("Collection:", store.collection_name)
        print("Chunks submitted:", len(points))
        print("Stored vectors:", info.points_count)

    finally:
        store.close()


if __name__ == "__main__":
    main()
