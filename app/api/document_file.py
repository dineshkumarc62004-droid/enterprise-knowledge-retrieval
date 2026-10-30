
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import get_current_role
from app.storage.qdrant_store import QdrantStore


router = APIRouter(
    prefix="/api",
    tags=["Document Viewer"],
)

UPLOAD_DIR = Path("data/raw")


@router.get("/documents/{document_id}/file")
def view_document_file(
    document_id: str,
    role: str = Depends(get_current_role),
):
    store = None

    try:
        store = QdrantStore()

        allowed_tags = (
            ["general", "restricted"]
            if role == "admin"
            else ["general"]
        )

        records = store.list_documents(
            allowed_access_tags=allowed_tags
        )

        matching_records = [
            record for record in records
            if (record.get("payload") or {}).get("document_id")
            == document_id
        ]

        if not matching_records:
            raise HTTPException(
                status_code=404,
                detail="Document not found or access denied.",
            )

        payload = matching_records[0]["payload"]
        filename = payload.get("filename", "document")

        extension = Path(filename).suffix.lower()

        if extension != ".pdf":
            raise HTTPException(
                status_code=415,
                detail="PDF preview is available only for PDF files.",
            )

        file_path = UPLOAD_DIR / f"{document_id}.pdf"

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Original PDF file not found.",
            )

        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline"
            },
        )

    finally:
        if store is not None:
            store.close()
