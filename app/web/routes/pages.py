import os
import time
import inspect
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from config import Config
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.helpers import humanbytes, time_formatter

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)
PAGE_START_TIME = time.time()

def render_template(templates: Jinja2Templates, request: Request, name: str, context: dict = None) -> HTMLResponse:
    """
    Renders a Jinja2 template with universal compatibility across all Starlette/FastAPI versions.
    Supports both Starlette >= 0.36 (where 'request' is first parameter) and older Starlette
    (where 'name' is first parameter).
    """
    ctx = dict(context or {})
    ctx["request"] = request
    params = list(inspect.signature(templates.TemplateResponse).parameters.keys())
    if params and params[0] == "request":
        return templates.TemplateResponse(request, name, ctx)
    try:
        return templates.TemplateResponse(request=request, name=name, context=ctx)
    except TypeError:
        return templates.TemplateResponse(name, ctx)

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return render_template(
        templates, request, "index.html",
        {"watermark": Config.WATERMARK, "watermark_url": Config.WATERMARK_URL}
    )

@router.get("/health", response_class=JSONResponse)
async def health_check():
    return {
        "status": "healthy",
        "service": "MMW-BOT-PRO",
        "engine": "Super-Sonic Ultra-Fast",
        "watermark": Config.WATERMARK
    }

@router.get("/status", response_class=JSONResponse)
async def status_endpoint():
    total_users = await user_repo.get_total_users()
    total_files = await file_repo.get_total_files()
    return {
        "status": "online",
        "total_users": total_users,
        "total_files": total_files,
        "watermark": Config.WATERMARK,
        "url": Config.WATERMARK_URL
    }

@router.get("/watch/{file_id}", response_class=HTMLResponse)
async def watch_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    download_url = f"{Config.BASE_URL}/download/{file_id}"
    embed_url = f"{Config.BASE_URL}/embed/{file_id}"

    return render_template(
        templates, request, "watch.html",
        {
            "file_id": file_id,
            "file_name": file_doc.get("file_name", "Media"),
            "file_size": humanbytes(file_doc.get("file_size", 0)),
            "mime_type": file_doc.get("mime_type", "video/mp4"),
            "stream_url": stream_url,
            "download_url": download_url,
            "embed_url": embed_url,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL
        }
    )

@router.get("/embed/{file_id}", response_class=HTMLResponse)
async def embed_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    return render_template(
        templates, request, "embed.html",
        {
            "file_id": file_id,
            "file_name": file_doc.get("file_name", "Media"),
            "mime_type": file_doc.get("mime_type", "video/mp4"),
            "stream_url": stream_url,
            "watermark": Config.WATERMARK
        }
    )

@router.get("/download/{file_id}", response_class=HTMLResponse)
async def download_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    return render_template(
        templates, request, "dl.html",
        {
            "file_id": file_id,
            "file_name": file_doc.get("file_name", "File"),
            "file_size": humanbytes(file_doc.get("file_size", 0)),
            "stream_url": stream_url,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL
        }
    )

@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    total_users = await user_repo.get_total_users()
    total_chats = await chat_repo.get_total_chats()
    total_files = await file_repo.get_total_files()
    uptime = time_formatter(seconds=round(time.time() - PAGE_START_TIME))

    return render_template(
        templates, request, "stats.html",
        {
            "total_users": total_users,
            "total_chats": total_chats,
            "total_files": total_files,
            "uptime": uptime,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL
        }
    )

@router.get("/help", response_class=HTMLResponse)
async def web_help_page(request: Request):
    return render_template(
        templates, request, "help.html",
        {
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL
        }
    )

@router.get("/search", response_class=HTMLResponse)
async def search_web_page(request: Request, q: str = Query(None)):
    results = []
    if q and q.strip():
        raw_results = await file_repo.search_files(q.strip(), limit=20)
        for r in raw_results:
            results.append({
                "file_id": r.get("file_id"),
                "file_name": r.get("file_name", "Unknown"),
                "file_size": humanbytes(r.get("file_size", 0)),
                "mime_type": r.get("mime_type", "video/mp4"),
                "watch_url": f"{Config.BASE_URL}/watch/{r.get('file_id')}",
                "download_url": f"{Config.BASE_URL}/download/{r.get('file_id')}"
            })

    return render_template(
        templates, request, "search.html",
        {
            "query": q or "",
            "results": results,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL
        }
    )
