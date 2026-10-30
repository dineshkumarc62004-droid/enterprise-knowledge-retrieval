
from app.storage.qdrant_store import QdrantStore
from qdrant_client.models import Filter, FieldCondition, MatchValue

DOCUMENT_ID = "ce01af1c185142c0b9e2197b91e991ec"

store = QdrantStore()

try:
    records, _ = store.client.scroll(
        collection_name=store.collection_name,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=DOCUMENT_ID),
                )
            ]
        ),
        limit=20,
        with_payload=True,
        with_vectors=False,
    )

    print("GENERAL DOCUMENT VERIFICATION")
    print("Points found:", len(records))

    if records:
        tags = set()

        for point in records:
            print("Filename:", point.payload.get("filename"))
            print("Access tag:", point.payload.get("access_tag"))
            tags.add(point.payload.get("access_tag"))

        if tags == {"general"} and len(records) == 5:
            print("\nPASSED: All 5 document chunks are general.")
        else:
            print("\nFAILED: Access tags or chunk count incorrect:", tags)
    else:
        print("Document not found in Qdrant.")

finally:
    store.close()
