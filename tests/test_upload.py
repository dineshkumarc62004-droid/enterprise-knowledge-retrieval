
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def set_test_keys(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")


def test_upload_rejects_unsupported_file(monkeypatch):
    set_test_keys(monkeypatch)

    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-admin-key"},
        files={
            "file": (
                "sample.doc",
                b"Legacy Word file",
                "application/msword",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported file format."


def test_upload_rejects_empty_file(monkeypatch):
    set_test_keys(monkeypatch)

    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-admin-key"},
        files={
            "file": (
                "empty.docx",
                b"",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty files are not allowed."


def test_upload_rejects_large_file(monkeypatch):
    set_test_keys(monkeypatch)

    large_content = b"A" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-admin-key"},
        files={
            "file": (
                "large.docx",
                large_content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File exceeds the 10 MB limit."


def test_public_user_upload_is_forbidden(monkeypatch):
    set_test_keys(monkeypatch)

    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-public-key"},
        files={
            "file": (
                "sample.docx",
                b"Fake DOCX content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only admin users can upload documents."
    )


def test_admin_upload_gets_restricted_tag(monkeypatch):
    set_test_keys(monkeypatch)

    captured_points = []

    # Mock document extraction
    monkeypatch.setattr(
        "app.api.upload.read_document",
        lambda path: {
            "full_text": "Sample company policy document."
        }
    )

    # Mock chunking
    monkeypatch.setattr(
        "app.api.upload.create_chunks",
        lambda text: ["Sample policy chunk"]
    )

    # Mock embeddings
    class FakeEmbeddingService:
        def embed_texts(self, chunks):
            return [[0.1] * 384 for _ in chunks]

    monkeypatch.setattr(
        "app.api.upload.EmbeddingService",
        FakeEmbeddingService
    )

    # Mock Qdrant
    class FakeQdrantStore:
        def upsert_chunks(self, points):
            captured_points.extend(points)

        def close(self):
            pass

    monkeypatch.setattr(
        "app.api.upload.QdrantStore",
        FakeQdrantStore
    )

    response = client.post(
        "/api/upload",
        headers={"X-API-Key": "test-admin-key"},
        files={
            "file": (
                "sample.docx",
                b"Fake DOCX content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["access_tag"] == "restricted"
    assert len(captured_points) == 1
    assert captured_points[0]["payload"]["access_tag"] == "restricted"
