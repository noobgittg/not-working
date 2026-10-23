import asyncio
import os
import time
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import Config
from app.database.repositories.chat_repo import chat_repo
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.utils.helpers import humanbytes

router = APIRouter()

# Locate templates directory robustly
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Default branding constants
BRAND_WATERMARK: str = getattr(Config, "WATERMARK", "MMW BOTZ")
BRAND_WATERMARK_URL: str = getattr(
    Config, "WATERMARK_URL", "https://t.me/mallumovieworldmain2"
)


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """
    Optimized homepage rendering with parallel repository execution.
    """
    # Fetch database stats concurrently for sub-millisecond response latency
    users_count, chats_count, files_count = await asyncio.gather(
        user_repo.get_total_users(),
        chat_repo.get_total_chats(),
        file_repo.get_total_files(),
        return_exceptions=True,
    )

    # Fallbacks in case of non-fatal connection glitches
    users_val = users_count if isinstance(users_count, int) else 0
    chats_val = chats_count if isinstance(chats_count, int) else 0
    files_val = files_count if isinstance(files_count, int) else 0

    start_time = getattr(request.app.state, "start_time", float(time.time()))
    uptime_sec = int(float(time.time()) - start_time)

    context: Dict[str, Any] = {
        "request": request,
        "watermark": BRAND_WATERMARK,
        "watermark_url": BRAND_WATERMARK_URL,
        "users_count": users_val,
        "chats_count": chats_val,
        "files_count": files_val,
        "uptime_sec": uptime_sec,
        "base_url": Config.BASE_URL.rstrip("/"),
    }

    response = templates.TemplateResponse(
        request=request, name="index.html", context=context
    )
    # Enable aggressive client cache for shell assets
    response.headers["Cache-Control"] = "public, max-age=60"
    return response


@router.get("/health", response_class=JSONResponse)
async def health_check():
    """
    Health check probe endpoint.
    """
    return {
        "status": "healthy",
        "service": "MMW-BOTZ-PRO",
        "engine": "Turbo-Stream 5MB/s Dual-Core",
        "timestamp": float(time.time()),
        "watermark": BRAND_WATERMARK,
        "watermark_url": BRAND_WATERMARK_URL,
    }


@router.get("/watch/{file_id}", response_class=HTMLResponse)
async def watch_page(request: Request, file_id: str):
    """
    High-speed video / audio stream playback interface.
    """
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    base_url = Config.BASE_URL.rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    download_url = f"{base_url}/download/{file_id}"

    mime_type = file_doc.get("mime_type", "video/mp4") or "video/mp4"
    is_audio = mime_type.startswith("audio/")
    file_size_raw = file_doc.get("file_size", 0)

    context: Dict[str, Any] = {
        "request": request,
        "file_id": file_id,
        "file_name": file_doc.get("file_name", "Media File"),
        "file_size": humanbytes(file_size_raw),
        "mime_type": mime_type,
        "is_audio": is_audio,
        "stream_url": stream_url,
        "download_url": download_url,
        "watermark": BRAND_WATERMARK,
        "watermark_url": BRAND_WATERMARK_URL,
    }

    response = templates.TemplateResponse(
        request=request, name="watch.html", context=context
    )
    # Hint proxies and clients to allow immediate streaming pipe
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@router.get("/download/{file_id}", response_class=HTMLResponse)
@router.get("/dl/{file_id}", response_class=HTMLResponse)
async def download_page(request: Request, file_id: str):
    """
    Direct file download and fast routing portal.
    """
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    base_url = Config.BASE_URL.rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    watch_url = f"{base_url}/watch/{file_id}"
    file_size_raw = file_doc.get("file_size", 0)

    context: Dict[str, Any] = {
        "request": request,
        "file_id": file_id,
        "file_name": file_doc.get("file_name", "Downloadable File"),
        "file_size": humanbytes(file_size_raw),
        "mime_type": file_doc.get("mime_type", "application/octet-stream"),
        "stream_url": stream_url,
        "watch_url": watch_url,
        "watermark": BRAND_WATERMARK,
        "watermark_url": BRAND_WATERMARK_URL,
    }

    return templates.TemplateResponse(request=request, name="dl.html", context=context)
