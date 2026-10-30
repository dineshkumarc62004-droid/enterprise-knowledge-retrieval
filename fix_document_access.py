
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="data/qdrant")

document_id = "ce01af1c185142c0b9e2197b91e991ec"

result = client.set_payload(
    collection_name="enterprise_documents",
    payload={"access_tag": "restricted"},
    points=Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        ]
    ),
    wait=True,
)

print("Document access updated successfully.")
print("New access tag: restricted")

client.close()
