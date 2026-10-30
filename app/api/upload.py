
from pathlib import Path
from uuid import uuid4
import traceback

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    Depends,
)

from app.core.security import get_current_role
from app.services.document_reader import (
    read_document,
    SUPPORTED_EXTENSIONS,
)
from app.services.chunking import create_document_chunks
from app.services.embeddings import EmbeddingService
from app.storage.qdrant_store import QdrantStore


router = APIRouter(
    prefix="/api",
    tags=["Document Upload"],
)

UPLOAD_DIR = Path("data/raw")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    role: str = Depends(get_current_role),
):
    # 1. Admin-only upload
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin users can upload documents.",
        )

    original_name = Path(file.filename or "").name.strip()

    if not original_name:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    extension = Path(original_name).suffix.lower()

    # 2. Validate file format
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format.",
        )

    # 3. Validate file size
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty files are not allowed.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    document_id = uuid4().hex
    stored_name = f"{document_id}{extension}"
    destination = UPLOAD_DIR / stored_name

    store = None

    try:
        # 4. Save document
        destination.write_bytes(content)

        # 5. Extract document content and metadata
        document = read_document(destination)
        full_text = document.get("full_text", "")

        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Document contains no readable text.",
            )

        # 6. Create chunks while preserving metadata
        document_chunks = create_document_chunks(
            document.get("segments", [])
        )

        if not document_chunks:
            raise HTTPException(
                status_code=400,
                detail="No chunks could be created.",
            )

        # Extract text for embedding generation
        texts = [
            item["text"]
            for item in document_chunks
        ]

        # 7. Generate embeddings
        embedding_service = EmbeddingService()
        vectors = embedding_service.embed_texts(texts)

        if len(document_chunks) != len(vectors):
            raise HTTPException(
                status_code=500,
                detail="Chunk and embedding counts do not match.",
            )

        # 8. Prepare Qdrant points with source metadata
        points = []

        for index, (item, vector) in enumerate(
            zip(document_chunks, vectors),
            start=1,
        ):
            points.append({
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "document_id": document_id,
                    "filename": original_name,
                    "chunk_index": index,
                    "text": item["text"],
                    "access_tag": "general",

                    # Source metadata
                    "page_number": item.get("page_number"),
                    "section": item.get("section"),
                    "slide_number": item.get("slide_number"),
                    "sheet_name": item.get("sheet_name"),
                    "table_number": item.get("table_number"),
                    "row_number": item.get("row_number"),
                },
            })

        # 9. Store in Qdrant
        store = QdrantStore()
        store.upsert_chunks(points)

        return {
            "status": "uploaded_and_indexed",
            "document_id": document_id,
            "filename": original_name,
            "size_bytes": len(content),
            "chunks_created": len(document_chunks),
            "embeddings_created": len(vectors),
            "qdrant_points_submitted": len(points),
            "role": role,
            "access_tag": "general",
            "message": "Document uploaded and indexed successfully.",
        }

    except HTTPException:
        destination.unlink(missing_ok=True)
        raise

    except Exception:
        traceback.print_exc()
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Document processing or indexing failed.",
        )

    finally:
        if store is not None:
            store.close()

        await file.close()
 