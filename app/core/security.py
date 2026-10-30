import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

load_dotenv()

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


async def get_current_role(
    api_key: str | None = Security(api_key_header)
):
    admin_key = os.getenv("EKR_ADMIN_API_KEY")

    if not admin_key:
        raise HTTPException(
            status_code=503,
            detail="Admin API key is not configured."
        )

    # No API key means free public access
    if not api_key:
        return "public"

    # Admin access
    if secrets.compare_digest(api_key, admin_key):
        return "admin"

    # Any other supplied key is invalid
    raise HTTPException(
        status_code=401,
        detail="Invalid API key."
    )