
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(path="data/qdrant")

COLLECTION = "enterprise_documents"

# Keep this latest document
KEEP_ID = "3d042cc9ec6d46beaae9d6b58bd5567a"

# Only these three old documents will be deleted
DELETE_IDS = [
    "0b3a5c85f9b340059f7a6f38f7833a64",
    "3c9ceb98226b4b16abc0f42c2ef46f8b",
    "70e0bba62d334bf0a6f28719e6f13075",
]

try:
    for document_id in DELETE_IDS:

        if document_id == KEEP_ID:
            raise ValueError("Safety check failed!")

        # Count existing points
        points, _ = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            print(f"Not found: {document_id}")
            continue

        # Delete only points belonging to this document ID
        client.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            wait=True,
        )

        print(
            f"Deleted: {document_id} | "
            f"Points removed: {len(points)}"
        )

    print("\nCleanup completed.")

finally:
    client.close()
