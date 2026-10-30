
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import traceback

from app.services.embeddings import EmbeddingService
from app.services.answer_generator import generate_answer
from app.services.cache_service import CacheService
from app.storage.qdrant_store import QdrantStore
from app.core.security import get_current_role


router = APIRouter(
    prefix="/api",
    tags=["Question Answering"]
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SourceItem(BaseModel):
    document: str
    document_id: str
    chunk: int | str
    score: float
    text: str = ""
    page_number: int | str | None = None
    section: str | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    table_number: int | None = None
    row_number: int | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceItem]
    cache_status: str


@router.post("/ask", response_model=AskResponse)
def ask_question(
    request: AskRequest,
    role: str = Depends(get_current_role)
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    access_tags = (
        ["general", "restricted"]
        if role == "admin"
        else ["general"]
    )

    cache = CacheService(ttl_seconds=600)
    store = None

    try:
        if not cache.ping():
            raise HTTPException(
                status_code=503,
                detail="Redis is unavailable."
            )

        # Check Redis cache
        cached = cache.get(question, access_tags)

        print(
            "EKR CACHE CHECK:",
            "HIT" if cached is not None else "MISS"
        )

        if cached is not None:
            return AskResponse(
                question=question,
                answer=cached["answer"],
                sources=cached["sources"],
                cache_status="HIT",
            )

        # Generate query embedding
        embedding_service = EmbeddingService()
        query_vector = embedding_service.embed_query(question)

        # Search Qdrant
        store = QdrantStore()

        results = store.search(
            query_vector,
            limit=8,
            allowed_access_tags=access_tags,
        )

        results = [
            result for result in results
            if result["score"] >= 0.60
        ]

        context_chunks = []

        for result in results:
            payload = result["payload"]

            context_chunks.append({
                "text": payload.get("text", ""),
                "document_id": payload.get("document_id", ""),
                "filename": payload.get(
                    "filename", "Unknown document"
                ),
                "chunk_index": payload.get("chunk_index", ""),
                "score": result["score"],
                "page_number": payload.get("page_number"),
                "section": payload.get("section"),
                "slide_number": payload.get("slide_number"),
                "sheet_name": payload.get("sheet_name"),
                "table_number": payload.get("table_number"),
                "row_number": payload.get("row_number"),
            })

        # Generate answer
        answer = generate_answer(
            question,
            context_chunks
        )

        sources = [
            {
                "document": item["filename"],
                "document_id": item["document_id"],
                "chunk": item["chunk_index"],
                "score": item["score"],
                "text": item["text"],
                "page_number": item["page_number"],
                "section": item["section"],
                "slide_number": item["slide_number"],
                "sheet_name": item["sheet_name"],
                "table_number": item["table_number"],
                "row_number": item["row_number"],
            }
            for item in context_chunks
        ]

        # Save answer in Redis
        cache.set(
            question,
            access_tags,
            answer,
            sources
        )

        return AskResponse(
            question=question,
            answer=answer,
            sources=sources,
            cache_status="MISS",
        )

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to process the question.",
        )

    finally:
        if store is not None:
            store.close()

        cache.close()
