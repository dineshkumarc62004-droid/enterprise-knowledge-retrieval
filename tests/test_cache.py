
from app.services.cache_service import CacheService


def test_cache_behavior():
    cache = CacheService(ttl_seconds=600)

    try:
        # Redis connection check
        assert cache.ping(), "Redis connection failed"
        print("Redis connection: SUCCESS")

        question = "How many days per week can employees work from home?"
        access_tags = ["general"]

        # First, cache miss expected
        cached = cache.get(question, access_tags)
        print("Initial cache:", "MISS" if cached is None else "HIT")

        # Save a test answer
        cache.set(
            question,
            access_tags,
            "Employees can work from home up to 2 days a week.",
            [{"document": "test_policy.docx", "chunk": 2}],
        )

        # Same question should return cached answer
        cached = cache.get(
            "  HOW MANY DAYS PER WEEK CAN EMPLOYEES WORK FROM HOME?  ",
            access_tags,
        )

        assert cached is not None, "Cache retrieval failed"
        assert "2 days a week" in cached["answer"]
        assert len(cached["sources"]) == 1

        # Different permission scope must not share the same cache entry
        different_scope = cache.get(question, ["confidential"])
        assert different_scope is None, "Permission scope isolation failed"

        print("Cache retrieval: SUCCESS")
        print("Permission scope isolation: SUCCESS")
        print("REDIS CACHE TEST PASSED")

    finally:
        cache.close()



