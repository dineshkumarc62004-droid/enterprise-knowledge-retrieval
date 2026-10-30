
import hashlib
import json
import os

import redis


class CacheService:
    def __init__(self, ttl_seconds: int = 600):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
            socket_connect_timeout=3,
        )
        self.ttl_seconds = ttl_seconds

    def _make_key(
        self,
        question: str,
        access_tags: list[str],
        selected_document_ids: list[str] | None = None,
    ) -> str:
        normalized_question = " ".join(question.lower().split())
        normalized_tags = sorted(set(access_tags))
        normalized_ids = sorted(set(selected_document_ids or []))

        cache_data = json.dumps(
            {
                "question": normalized_question,
                "access_tags": normalized_tags,
                "selected_document_ids": normalized_ids,
            },
            sort_keys=True,
        )

        key_hash = hashlib.sha256(cache_data.encode()).hexdigest()
        return f"ekr:answer:{key_hash}"

    def get(
        self,
        question: str,
        access_tags: list[str],
        selected_document_ids: list[str] | None = None,
    ):
        key = self._make_key(
            question,
            access_tags,
            selected_document_ids,
        )

        cached_value = self.client.get(key)

        if cached_value is None:
            return None

        return json.loads(cached_value)

    def set(
        self,
        question: str,
        access_tags: list[str],
        answer: str,
        sources: list[dict],
        selected_document_ids: list[str] | None = None,
    ):
        key = self._make_key(
            question,
            access_tags,
            selected_document_ids,
        )

        cache_value = json.dumps(
            {
                "answer": answer,
                "sources": sources,
            }
        )

        self.client.set(key, cache_value, ex=self.ttl_seconds)

    def ping(self) -> bool:
        return bool(self.client.ping())

    def close(self):
        self.client.close()
