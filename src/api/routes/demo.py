from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

current_file_dir = Path(__file__).resolve().parent.parent.parent
templates_path = current_file_dir / "templates"
templates = Jinja2Templates(directory=templates_path)

@router.get("/demo", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("aidocs.html", {
        "request": request,
    })