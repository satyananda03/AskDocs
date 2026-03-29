import json
from typing import Optional, Dict, Any
from src.infrastructure.redis import redis_client
from src.core.config import settings

async def stream_event(session_id: str, status: str, message: str, details: Optional[Dict[str, Any]] = None):
    stream_key = f"aidocs:{session_id}:stream"
    data = {
        "status": status,
        "message": message,
        "details": json.dumps(details) if details else "{}"
    }
    await redis_client.client.xadd(stream_key, data)
    await redis_client.client.expire(stream_key, settings.redis_ttl)