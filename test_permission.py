
from app.services.embeddings import EmbeddingService
from app.storage.qdrant_store import QdrantStore


def main():
    question = "How many days per week can employees work from home?"

    embedding_service = EmbeddingService()
    query_vector = embedding_service.embed_query(question)

    store = QdrantStore()

    try:
        allowed_results = store.search(
            query_vector,
            limit=3,
            allowed_access_tags=["general"],
        )

        denied_results = store.search(
            query_vector,
            limit=3,
            allowed_access_tags=[],
        )

        print("PERMISSION FILTER TEST")
        print("General access results:", len(allowed_results))
        print("Empty permission results:", len(denied_results))

        if allowed_results:
            print("\nFirst result:")
            print(allowed_results[0]["payload"].get("text", "")[:300])

        if allowed_results and not denied_results:
            print("\nPERMISSION FILTER TEST PASSED")
        else:
            print("\nPERMISSION FILTER TEST NEEDS REVIEW")

    finally:
        store.close()


if __name__ == "__main__":
    main()
