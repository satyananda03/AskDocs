# src/infrastructure/redis_events.py
import json
from typing import Optional, Dict, Any
from src.infrastructure.redis import redis_client

async def stream_event(session_id: str, status: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Logging ke Redis menggunakan Redis Streams (XADD)"""
    stream_key = f"aidocs:{session_id}:stream"
    data = {
        "status": status,
        "message": message,
        "details": json.dumps(details) if details else "{}"
    }
    # Masukkan event ke dalam Stream
    await redis_client.client.xadd(stream_key, data)
    # Set TTL 24 jam agar stream tidak memenuhi memori selamanya
    await redis_client.client.expire(stream_key, 86400)