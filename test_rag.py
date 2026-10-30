
from app.services.embeddings import EmbeddingService
from app.services.answer_generator import generate_answer
from app.services.cache_service import CacheService
from app.storage.qdrant_store import QdrantStore


def main():
    question = "How many days per week can employees work from home?"
    access_tags = ["general"]

    cache = CacheService(ttl_seconds=600)
    store = None

    try:
        # Step 1: Check Redis cache first
        cached = cache.get(question, access_tags)

        if cached is not None:
            print("\nCACHE STATUS: HIT")
            answer = cached["answer"]
            sources = cached["sources"]

        else:
            print("\nCACHE STATUS: MISS")
            print("Searching Qdrant and generating answer...")

            # Step 2: Embed the question
            embedding_service = EmbeddingService()
            query_vector = embedding_service.embed_query(question)

            # Step 3: Search Qdrant
            store = QdrantStore()

            results = store.search(
                query_vector,
                limit=3,
                allowed_access_tags=access_tags,
            )

            context_chunks = [
                {
                    "text": result["payload"].get("text", ""),
                    "document_id": result["payload"].get("document_id", ""),
                    "chunk_index": result["payload"].get("chunk_index", ""),
                    "score": result["score"],
                }
                for result in results
            ]

            # Step 4: Generate the answer
            answer = generate_answer(question, context_chunks)

            # Step 5: Prepare source details
            sources = [
                {
                    "document": item["document_id"],
                    "chunk": item["chunk_index"],
                    "score": item["score"],
                }
                for item in context_chunks
            ]

            # Step 6: Save answer and sources in Redis
            cache.set(
                question,
                access_tags,
                answer,
                sources,
            )

            print("Answer saved to Redis cache.")

        print("\nQUESTION:")
        print(question)

        print("\nANSWER:")
        print(answer)

        print("\nSOURCES:")
        if sources:
            for item in sources:
                print(
                    f"- Document: {item['document']}, "
                    f"Chunk: {item['chunk']}, "
                   f"Score: {item.get('score', 0):.4f}"
                )
        else:
            print("No sources retrieved.")

    finally:
        if store is not None:
            store.close()
        cache.close()


if __name__ == "__main__":
    main()
