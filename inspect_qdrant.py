from collections import defaultdict
from qdrant_client import QdrantClient

client = QdrantClient(path="data/qdrant")

documents = defaultdict(lambda: {
    "filename": "",
    "access_tag": "",
    "chunks": 0,
})

points, _ = client.scroll(
    collection_name="enterprise_documents",
    limit=100,
    with_payload=True,
    with_vectors=False,
)

for point in points:
    payload = point.payload or {}
    doc_id = payload.get("document_id")

    documents[doc_id]["filename"] = payload.get("filename")
    documents[doc_id]["access_tag"] = payload.get("access_tag")
    documents[doc_id]["chunks"] += 1

print("===== FINAL QDRANT REPORT =====")

for doc_id, details in documents.items():
    print("\nDocument ID:", doc_id)
    print("Filename:", details["filename"])
    print("Access Tag:", details["access_tag"])
    print("Chunks:", details["chunks"])

print("\nTotal documents:", len(documents))
print("Total points:", len(points))

client.close()