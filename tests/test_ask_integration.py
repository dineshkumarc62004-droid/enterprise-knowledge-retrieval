import uuid

from fastapi.testclient import TestClient

from main import app
from app.services.embeddings import EmbeddingService
from app.storage.qdrant_store import QdrantStore


client = TestClient(app)


def test_real_document_retrieval(monkeypatch, tmp_path):

    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    # Temporary Qdrant database
    qdrant_path = str(tmp_path / "qdrant")
    collection_name = "test_ekr_" + uuid.uuid4().hex[:8]

    # Real embedding generation
    embedding_service = EmbeddingService()

    document_text = (
        "Employees can work from home two days per week "
        "with manager approval."
    )

    vector = embedding_service.embed_texts([document_text])[0]

    # Insert actual vector into Qdrant
    store = QdrantStore(
        storage_path=qdrant_path,
        collection_name=collection_name,
        vector_size=384,
    )

    store.upsert_chunks([
        {
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": {
                "document_id": "integration-doc-001",
                "filename": "company_policy.docx",
                "chunk_index": 0,
                "text": document_text,
                "access_tag": "general",
            },
        }
    ])

    store.close()

    # Use temporary Qdrant for API retrieval
    monkeypatch.setattr(
        "app.api.ask.QdrantStore",
        lambda: QdrantStore(
            storage_path=qdrant_path,
            collection_name=collection_name,
            vector_size=384,
        ),
    )

    captured = {}

    def fake_generate_answer(question, context_chunks):
        captured["context"] = context_chunks
        return "Employees can work from home two days per week."

    monkeypatch.setattr(
        "app.api.ask.generate_answer",
        fake_generate_answer,
    )

    # Unique question avoids old Redis cache entries
    question = (
        "Tell me the work from home policy "
        + uuid.uuid4().hex
    )

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={"question": question},
    )

    assert response.status_code == 200
    assert response.json()["cache_status"] == "MISS"
    assert len(response.json()["sources"]) > 0
    assert len(captured["context"]) > 0

    print("REAL EMBEDDING: SUCCESS")
    print("ACTUAL QDRANT RETRIEVAL: SUCCESS")
    print("API RETRIEVAL: SUCCESS")