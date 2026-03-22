from .upload import router as upload_router
from .chat import router as chat_router
from .demo import router as demo_router
from .session import router as session_router
# from .delete import router as delete_router

__all__ = ["chat_router", "upload_router", "demo_router", "session_router"]