import langwatch
import httpx
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)
client = None

def init_langwatch():
    if settings.langwatch_enabled and settings.langwatch_api_key:
        try:
            langwatch.setup(
                api_key=settings.langwatch_api_key,  
                endpoint_url=settings.langwatch_endpoint,  
            )
            logger.info("LangWatch tracing initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize LangWatch: {e}")
    else:
        logger.info("LangWatch tracing disabled")

def get_langwatch_metadata(session_id: str, user_id: str = None, **kwargs):
    """Get LangWatch metadata for tracing"""
    if not settings.langwatch_enabled:
        return {}
    metadata = {
        "session_id": session_id,
        "user_id": user_id or session_id,
        "environment": settings.environment,
        "app_version": settings.app_version,
    }
    metadata.update(kwargs)
    return metadata

def get_client():
    global client
    if client is None:
        client = httpx.AsyncClient(timeout=10)
    return client

async def log_metrics(trace_id: str, metrics: dict):
    payload = {
        "trace_id": trace_id,
        "event_type": "retriever_metrics",
        "metrics": metrics,
    }
    headers = {
        "X-Auth-Token": settings.langwatch_api_key,
        "Content-Type": "application/json",
    }
    # logger.info(f"Logging metrics to LangWatch") 
    client = get_client()
    try:
        await client.post(
            f"{settings.langwatch_endpoint}/api/track_event", 
            headers=headers, 
            json=payload
        )
    except Exception as e:
        logger.error(f"Network error logging metrics: {e}")