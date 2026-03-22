import redis.asyncio as redis
from typing import Optional
from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError

logger = get_logger(__name__)

class RedisClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance.client = redis.from_url(
                    settings.redis_url, 
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise ExternalServiceError(f"Redis connection failed: {e}")
        return cls._instance

    async def save_user_data(self, session_id: str, user_data: dict) -> None:
        if not user_data:
            logger.warning(f"Skipping to save empty user data")
            return
        try:
            key = f"user:{session_id}"
            async with self.client.pipeline(transaction=False) as pipe:
                pipe.hset(key, mapping=user_data)
                pipe.expire(key, settings.redis_ttl)
                await pipe.execute()
            logger.debug(f"Saved user data for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")
            raise ExternalServiceError(f"Failed to save user data: {e}")
    
    async def get_user_data(self, session_id: str) -> Optional[dict]:
        try:
            data = await self.client.hgetall(f"user:{session_id}")
            return data if data else None
        except Exception as e:
            logger.error(f"Failed to get user data: {e}")
            return None
    
    async def delete_user_data(self, session_id: str) -> None:
        try:
            await self.client.delete(f"user:{session_id}")
            logger.debug(f"Deleted user data for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            raise ExternalServiceError(f"Failed to delete user data: {e}")
    
    async def health_check(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def create_pubsub(self):
        """Buat koneksi pubsub untuk streaming ingestion proses"""
        streaming_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=None
        )
        return streaming_client, streaming_client.pubsub()
    
redis_client = RedisClient()