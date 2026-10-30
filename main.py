
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.ask import router as ask_router
from app.api.documents import router as documents_router

from app.api.document_file import router as document_file_router

from fastapi import Depends
from app.core.security import get_current_role

app = FastAPI(
    title="Enterprise Knowledge Retrieval",
    description="Document upload and knowledge retrieval API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.include_router(document_file_router)


@app.get("/")
def home():
    return {
        "project": "Enterprise Knowledge Retrieval",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/auth/me")
async def verify_user_role(
    role: str = Depends(get_current_role),
):
    return {"role": role}