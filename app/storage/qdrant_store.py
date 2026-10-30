
from pathlib import Path

from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    FieldCondition,
    Filter,
    MatchValue,
)


class QdrantStore:
    def __init__(
        self,
        storage_path: str = "data/qdrant",
        collection_name: str = "enterprise_documents",
        vector_size: int = 384,
    ):
        self.storage_path = str(Path(storage_path))
        self.collection_name = collection_name
        self.client = QdrantClient(path=self.storage_path)

        collections = self.client.get_collections().collections
        collection_exists = any(
            item.name == self.collection_name for item in collections
        )

        if not collection_exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return

        points = [
            PointStruct(
                id=chunk["id"],
                vector=chunk["vector"],
                payload=chunk["payload"],
            )
            for chunk in chunks
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        allowed_access_tags: list[str] | None = None,
    ) -> list[dict]:

        query_filter = None

        if allowed_access_tags is not None:
            if not allowed_access_tags:
                return []

            query_filter = Filter(
                should=[
                    FieldCondition(
                        key="access_tag",
                        match=MatchValue(value=tag),
                    )
                    for tag in allowed_access_tags
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
            }
            for point in results
        ]

    # NEW: Retrieve document chunks from Qdrant
    def list_documents(
        self,
        allowed_access_tags: list[str] | None = None,
    ) -> list[dict]:

        query_filter = None

        if allowed_access_tags is not None:
            if not allowed_access_tags:
                return []

            query_filter = Filter(
                should=[
                    FieldCondition(
                        key="access_tag",
                        match=MatchValue(value=tag),
                    )
                    for tag in allowed_access_tags
                ]
            )

        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        return [
            {
                "id": record.id,
                "payload": record.payload,
            }
            for record in records
        ]

    def close(self) -> None:
        self.client.close()

    def delete_document(self, document_id: str) -> int:
        """
        Delete all Qdrant chunks belonging to one document.
        Returns the number of deleted chunks.
        """
        document_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

        # Count matching chunks before deletion
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=document_filter,
            limit=10000,
            with_payload=False,
            with_vectors=False,
        )

        chunk_count = len(records)

        if chunk_count == 0:
            return 0

        # Delete only this document's chunks
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=document_filter,
            wait=True,
        )

        return chunk_count
