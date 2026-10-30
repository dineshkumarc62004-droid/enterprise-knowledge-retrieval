
from collections import defaultdict
from qdrant_client import QdrantClient

client = QdrantClient(path="data/qdrant")

collection_name = "enterprise_documents"

records = defaultdict(lambda: {
    "document_ids": set(),
    "chunks": 0
})

offset = None

while True:
    points, offset = client.scroll(
        collection_name=collection_name,
        limit=100,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )

    for point in points:
        payload = point.payload or {}

        filename = payload.get("filename", "Unknown")
        document_id = payload.get("document_id", "Missing ID")

        records[filename]["document_ids"].add(document_id)
        records[filename]["chunks"] += 1

    if offset is None:
        break

print("\n===== QDRANT DOCUMENT REPORT =====")

for filename, details in records.items():
    print(f"\nFilename: {filename}")
    print(f"Document IDs: {details['document_ids']}")
    print(f"Total chunks: {details['chunks']}")

    if len(details["document_ids"]) > 1:
        print("WARNING: Multiple document IDs found!")
    else:
        print("OK: Single document ID")

client.close()
