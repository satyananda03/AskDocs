from fastapi import APIRouter, HTTPException
from src.infrastructure.redis import redis_client

router = APIRouter()

@router.get("/sessions")
async def verify_session(session_id: str):
    doc_name_key = f"aidocs:{session_id}:doc_name"
    doc_name = await redis_client.client.get(doc_name_key)
    if doc_name:
        return {
            "is_valid": True,
            "docs_name": doc_name
        }
    else:
        # Jika tidak ada (expired)
        return {
            "is_valid": False,
            "docs_name": None
        }