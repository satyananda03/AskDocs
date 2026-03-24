from fastapi import APIRouter, HTTPException
from src.infrastructure.redis import redis_client
from pydantic import BaseModel
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["sessions"])

class DeleteResponse(BaseModel):
    message: str
    status_code: int
    
@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str) -> DeleteResponse:
    try:
        session_key = f"aidocs:{session_id}*"
        deleted_count = 0
        
        # Gunakan scan_iter agar tidak memblokir server Redis (Best Practice dibanding KEYS)
        async for key in redis_client.client.scan_iter(match=session_key):
            await redis_client.client.delete(key)
            deleted_count += 1
        if deleted_count == 0:
            # Opsional: Kembalikan 404 jika memang tidak ada yang dihapus
            raise HTTPException(status_code=404, detail="Session not found")

        return DeleteResponse(
            message=f"Session {session_id} deleted successfully.", 
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while deleting session.")