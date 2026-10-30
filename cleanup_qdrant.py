from qdrant_client import QdrantClient

client = QdrantClient(path="data/qdrant")

keep_ids = {
    "a62a0384ac094b95b28f6bb2c4713db5",
    "70e0bba62d334bf0a6f28719e6f13075",
    "0b3a5c85f9b340059f7a6f38f7833a64",
}

all_points = []
offset = None

while True:
    points, offset = client.scroll(
        collection_name="enterprise_documents",
        limit=100,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )

    all_points.extend(points)

    if offset is None:
        break

delete_ids = [
    point.id
    for point in all_points
    if (point.payload or {}).get("document_id") not in keep_ids
]

print("Points to retain:", len(all_points) - len(delete_ids))
print("Points to delete:", len(delete_ids))

if len(all_points) != 50 or len(delete_ids) != 35:
    print("Unexpected count. Deletion cancelled.")
else:
    client.delete(
        collection_name="enterprise_documents",
        points_selector=delete_ids,
        wait=True,
    )
    print("Duplicate points deleted successfully!")

client.close()