from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from src.api.routes import upload_router, chat_router, demo_router, session_router, delete_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.infrastructure.langwatch import init_langwatch

def create_app() -> FastAPI:
    setup_logging(settings.log_level)
    init_langwatch()
    
    app = FastAPI()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    static_path = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    app.include_router(upload_router)
    app.include_router(chat_router)
    app.include_router(demo_router)
    app.include_router(session_router)
    app.include_router(delete_router)
    return app

app = create_app()