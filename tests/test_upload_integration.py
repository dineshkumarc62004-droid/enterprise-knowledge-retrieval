
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from main import app
from app.storage.qdrant_store import QdrantStore


client = TestClient(app)


def test_actual_docx_upload_and_qdrant_indexing(monkeypatch, tmp_path):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    upload_dir = tmp_path / "uploads"
    qdrant_dir = tmp_path / "qdrant"

    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "app.api.upload.UPLOAD_DIR",
        upload_dir,
    )

    monkeypatch.setattr(
        "app.api.upload.QdrantStore",
        lambda: QdrantStore(
            storage_path=str(qdrant_dir),
            collection_name="upload_integration_test",
            vector_size=384,
        ),
    )

    # Create a real DOCX document
    document = Document()
    document.add_paragraph(
        "Integration testing document. "
        "The company leave policy allows twenty annual leave days."
    )

    file_data = BytesIO()
    document.save(file_data)
    file_data.seek(0)

    # Admin uploads the document
    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-admin-key"},
        files={
            "file": (
                "integration_test.docx",
                file_data,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["status"] == "uploaded_and_indexed"
    assert result["role"] == "admin"
    assert result["access_tag"] == "restricted"
    assert result["chunks_created"] > 0
    assert result["embeddings_created"] == result["chunks_created"]
    assert result["qdrant_points_submitted"] == result["chunks_created"]

    # Verify actual stored vectors in Qdrant
    store = QdrantStore(
        storage_path=str(qdrant_dir),
        collection_name="upload_integration_test",
        vector_size=384,
    )

    try:
        records, _ = store.client.scroll(
            collection_name="upload_integration_test",
            scroll_filter=None,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )

        matching_records = [
            record
            for record in records
            if record.payload["document_id"] == result["document_id"]
        ]

        assert len(matching_records) == result["chunks_created"]

        assert all(
            record.payload["access_tag"] == "restricted"
            for record in matching_records
        )

        print("REAL DOCX EXTRACTION: SUCCESS")
        print("REAL EMBEDDING GENERATION: SUCCESS")
        print("ACTUAL QDRANT INDEXING: SUCCESS")
        print("ADMIN ACCESS TAG: RESTRICTED")

    finally:
        store.close()
