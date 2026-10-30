import uuid

from app.storage.qdrant_store import QdrantStore


def test_real_qdrant_permission_isolation(tmp_path):

    store = QdrantStore(
        storage_path=str(tmp_path / "qdrant"),
        collection_name="permission_test",
        vector_size=384,
    )

    vector = [0.1] * 384

    store.upsert_chunks([
        {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": {
                "document_id": "public-doc",
                "filename": "public_policy.docx",
                "chunk_index": 0,
                "text": "Public company policy",
                "access_tag": "general",
            },
        },
        {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": {
                "document_id": "admin-doc",
                "filename": "restricted_policy.docx",
                "chunk_index": 0,
                "text": "Restricted company policy",
                "access_tag": "restricted",
            },
        },
    ])

    # Public user
    public_results = store.search(
        query_vector=vector,
        limit=5,
        allowed_access_tags=["general"],
    )

    # Admin user
    admin_results = store.search(
        query_vector=vector,
        limit=5,
        allowed_access_tags=["general", "restricted"],
    )

    public_tags = {
        item["payload"]["access_tag"]
        for item in public_results
    }

    admin_tags = {
        item["payload"]["access_tag"]
        for item in admin_results
    }

    assert public_tags == {"general"}
    assert admin_tags == {"general", "restricted"}

    store.close()

    print("PUBLIC ACCESS ISOLATION: SUCCESS")
    print("ADMIN ACCESS: SUCCESS")