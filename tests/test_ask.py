
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_ask_rejects_whitespace_question(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={"question": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."


def test_ask_rejects_empty_question(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={"question": ""},
    )

    assert response.status_code == 422


def test_ask_rejects_missing_api_key():
    response = client.post(
        "/api/ask",
        json={"question": "What is the company policy?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key."


def test_ask_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "wrong-api-key"},
        json={"question": "What is the company policy?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key."


def test_ask_returns_cached_answer(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    class FakeCache:
        def __init__(self, ttl_seconds):
            pass

        def ping(self):
            return True

        def get(self, question, access_tags):
            return {
                "answer": "Employees can work from home 2 days a week.",
                "sources": [
                    {
                        "document_id": "doc-001",
                        "document": "policy.docx",
                        "chunk": 1,
                        "score": 0.9,
                    }
                ],
            }

        def close(self):
            pass

    monkeypatch.setattr("app.api.ask.CacheService", FakeCache)

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={
            "question": "How many days can employees work from home?"
        },
    )

    assert response.status_code == 200
    assert response.json()["cache_status"] == "HIT"
    assert "2 days a week" in response.json()["answer"]


def test_ask_cache_miss_generates_answer(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    saved = {}

    class FakeCache:
        def __init__(self, ttl_seconds):
            pass

        def ping(self):
            return True

        def get(self, question, access_tags):
            return None

        def set(self, question, access_tags, answer, sources):
            saved["answer"] = answer
            saved["sources"] = sources

        def close(self):
            pass

    class FakeEmbedding:
        def embed_query(self, question):
            return [0.1] * 384

    class FakeStore:
        def search(self, vector, limit, allowed_access_tags):
            return [{
                "score": 0.90,
                "payload": {
                    "text": "Employees can work from home 2 days a week.",
                    "document_id": "doc-001",
                    "chunk_index": 1,
                },
            }]

        def close(self):
            pass

    monkeypatch.setattr("app.api.ask.CacheService", FakeCache)
    monkeypatch.setattr("app.api.ask.EmbeddingService", FakeEmbedding)
    monkeypatch.setattr("app.api.ask.QdrantStore", FakeStore)

    monkeypatch.setattr(
        "app.api.ask.generate_answer",
        lambda question, context: (
            "Employees can work from home 2 days a week."
        )
    )

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={
            "question": "How many days can employees work from home?"
        },
    )

    assert response.status_code == 200
    assert response.json()["cache_status"] == "MISS"
    assert len(response.json()["sources"]) == 1
    assert "answer" in saved


def test_public_user_searches_general_documents_only(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    captured = {}

    class FakeCache:
        def __init__(self, ttl_seconds):
            pass

        def ping(self):
            return True

        def get(self, question, access_tags):
            return None

        def set(self, *args):
            pass

        def close(self):
            pass

    class FakeEmbedding:
        def embed_query(self, question):
            return [0.1] * 384

    class FakeStore:
        def search(self, vector, limit, allowed_access_tags):
            captured["access_tags"] = allowed_access_tags
            return []

        def close(self):
            pass

    monkeypatch.setattr("app.api.ask.CacheService", FakeCache)
    monkeypatch.setattr("app.api.ask.EmbeddingService", FakeEmbedding)
    monkeypatch.setattr("app.api.ask.QdrantStore", FakeStore)

    monkeypatch.setattr(
        "app.api.ask.generate_answer",
        lambda question, context: (
            "Not found in the provided documents."
        )
    )

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-public-key"},
        json={"question": "What is the company policy?"},
    )

    assert response.status_code == 200
    assert captured["access_tags"] == ["general"]


def test_admin_user_searches_general_and_restricted_documents(monkeypatch):
    monkeypatch.setenv("EKR_PUBLIC_API_KEY", "test-public-key")
    monkeypatch.setenv("EKR_ADMIN_API_KEY", "test-admin-key")

    captured = {}

    class FakeCache:
        def __init__(self, ttl_seconds):
            pass

        def ping(self):
            return True

        def get(self, question, access_tags):
            return None

        def set(self, *args):
            pass

        def close(self):
            pass

    class FakeEmbedding:
        def embed_query(self, question):
            return [0.1] * 384

    class FakeStore:
        def search(self, vector, limit, allowed_access_tags):
            captured["access_tags"] = allowed_access_tags
            return []

        def close(self):
            pass

    monkeypatch.setattr("app.api.ask.CacheService", FakeCache)
    monkeypatch.setattr("app.api.ask.EmbeddingService", FakeEmbedding)
    monkeypatch.setattr("app.api.ask.QdrantStore", FakeStore)

    monkeypatch.setattr(
        "app.api.ask.generate_answer",
        lambda question, context: (
            "Not found in the provided documents."
        )
    )

    response = client.post(
        "/api/ask",
        headers={"X-API-Key": "test-admin-key"},
        json={"question": "What is the company policy?"},
    )

    assert response.status_code == 200
    assert captured["access_tags"] == ["general", "restricted"]
