
from app.services.embeddings import EmbeddingService
from app.storage.qdrant_store import QdrantStore


def main():
    question = "How many days per week can employees work from home?"

    embedding_service = EmbeddingService()
    query_vector = embedding_service.embed_query(question)

    store = QdrantStore()

    try:
        results = store.search(query_vector, limit=3)

        print("SEMANTIC SEARCH RESULTS")
        print("Question:", question)
        print("Results found:", len(results))

        for result in results:
            payload = result["payload"]
            print("\nScore:", round(result["score"], 4))
            print("Chunk:", payload.get("chunk_index"))
            print("Text:", payload.get("text", "")[:500])

    finally:
        store.close()


if __name__ == "__main__":
    main()
