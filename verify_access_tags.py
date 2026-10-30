from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="data/qdrant")

document_ids = [
    "0adb9095117b4079ac41b9956da00e2e",
    "1d2cf19e1e9b42b9996bdc6b47c9c5e0",
    "a62a0384ac094b95b28f6bb2c4713db5",
]

for doc_id in document_ids:
    points, _ = client.scroll(
        collection_name="enterprise_documents",
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=doc_id),
                )
            ]
        ),
        limit=100,
        with_payload=True,
    )

    tags = {
        point.payload.get("access_tag")
        for point in points
    }

    print(doc_id, "->", tags)

client.close()