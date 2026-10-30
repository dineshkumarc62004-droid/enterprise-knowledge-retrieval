
from pathlib import Path
import mimetypes
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import get_current_role
from app.storage.qdrant_store import QdrantStore


router = APIRouter(
    prefix="/api",
    tags=["Document Management"],
)

UPLOAD_DIR = Path("data/raw")


def validate_document_id(document_id: str):
    if not re.fullmatch(r"[a-fA-F0-9]{32}", document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )


def find_document(store, document_id, role):
    access_tags = (
        ["general", "restricted"]
        if role == "admin"
        else ["general"]
    )

    records = store.list_documents(
        allowed_access_tags=access_tags
    )

    for record in records:
        payload = record.get("payload") or {}

        if payload.get("document_id") == document_id:
            return payload

    return None


@router.get("/documents")
def get_documents(
    role: str = Depends(get_current_role),
):
    store = None

    try:
        store = QdrantStore()

        access_tags = (
            ["general", "restricted"]
            if role == "admin"
            else ["general"]
        )

        records = store.list_documents(
            allowed_access_tags=access_tags
        )

        documents = {}

        for record in records:
            payload = record.get("payload") or {}
            document_id = payload.get("document_id")

            if not document_id:
                continue

            if document_id not in documents:
                documents[document_id] = {
                    "document_id": document_id,
                    "filename": payload.get("filename", "Unknown"),
                    "access_tag": payload.get("access_tag", ""),
                    "chunks": 0,
                }

            documents[document_id]["chunks"] += 1

        return {
            "total_documents": len(documents),
            "documents": list(documents.values()),
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve documents.",
        )

    finally:
        if store is not None:
            store.close()


@router.get("/documents/{document_id}/file")
def view_document(
    document_id: str,
    role: str = Depends(get_current_role),
):
    validate_document_id(document_id)
    store = None

    try:
        store = QdrantStore()

        payload = find_document(store, document_id, role)

        if payload is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found or access denied.",
            )

        files = list(UPLOAD_DIR.glob(f"{document_id}.*"))

        if not files:
            raise HTTPException(
                status_code=404,
                detail="Original document file not found.",
            )

        file_path = files[0]
        media_type = mimetypes.guess_type(file_path.name)[0]

        return FileResponse(
            path=file_path,
            media_type=media_type or "application/octet-stream",
            filename=payload.get("filename", file_path.name),
            content_disposition_type="inline",
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to open document.",
        )

    finally:
        if store is not None:
            store.close()


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    role: str = Depends(get_current_role),
):
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin users can delete documents.",
        )

    validate_document_id(document_id)
    store = None

    try:
        store = QdrantStore()

        payload = find_document(store, document_id, role)

        if payload is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        files = list(UPLOAD_DIR.glob(f"{document_id}.*"))

        deleted_chunks = store.delete_document(document_id)

        for file_path in files:
            file_path.unlink(missing_ok=True)

        return {
            "status": "deleted",
            "document_id": document_id,
            "filename": payload.get("filename", "Unknown"),
            "deleted_chunks": deleted_chunks,
            "message": "Document and its indexed chunks deleted successfully.",
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to delete document.",
        )

    finally:
        if store is not None:
            store.close()
