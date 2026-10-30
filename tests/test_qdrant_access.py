from app.storage.qdrant_store import QdrantStore


def test_actual_qdrant_access_control(tmp_path):
    store = QdrantStore(
        storage_path=str(tmp_path / "qdrant_test"),
        collection_name="access_test",
        vector_size=384,
    )

    try:
        vector = [0.1] * 384

        chunks = [
            {
                "id": 1,
                "vector": vector,
                "payload": {
                    "text": "Public document",
                    "access_tag": "general",
                },
            },
            {
                "id": 2,
                "vector": vector,
                "payload": {
                    "text": "Restricted document",
                    "access_tag": "restricted",
                },
            },
        ]

        store.upsert_chunks(chunks)

        public_results = store.search(
            query_vector=vector,
            allowed_access_tags=["general"],
        )

        admin_results = store.search(
            query_vector=vector,
            allowed_access_tags=["general", "restricted"],
        )

        assert len(public_results) == 1
        assert public_results[0]["payload"]["access_tag"] == "general"

        assert len(admin_results) == 2

        print("PUBLIC ACCESS: SUCCESS")
        print("ADMIN ACCESS: SUCCESS")

    finally:
        store.close()