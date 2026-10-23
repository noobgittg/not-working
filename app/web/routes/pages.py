import os
import time
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from config import Config
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.helpers import humanbytes

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    users_count = await user_repo.get_total_users()
    chats_count = await chat_repo.get_total_chats()
    files_count = await file_repo.get_total_files()
    start_time = getattr(request.app.state, "start_time", float(time.time()))
    uptime_sec = int(float(time.time()) - start_time)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL,
            "users_count": users_count,
            "chats_count": chats_count,
            "files_count": files_count,
            "uptime_sec": uptime_sec,
            "base_url": Config.BASE_URL
        }
    )

@router.get("/health", response_class=JSONResponse)
async def health_check():
    return {
        "status": "healthy",
        "service": "MMW-BOT-PRO",
        "engine": "Super-Sonic Ultra-Fast",
        "timestamp": float(time.time()),
        "watermark": Config.WATERMARK
    }

@router.get("/watch/{file_id}", response_class=HTMLResponse)
async def watch_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    download_url = f"{Config.BASE_URL}/download/{file_id}"
    mime = file_doc.get("mime_type", "video/mp4")
    is_audio = mime.startswith("audio/")

    return templates.TemplateResponse(
        "watch.html",
        {
            "request": request,
            "file_name": file_doc.get("file_name", "Media"),
            "file_size": humanbytes(file_doc.get("file_size", 0)),
            "mime_type": mime,
            "is_audio": is_audio,
            "stream_url": stream_url,
            "download_url": download_url,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL,
            "file_id": file_id
        }
    )

@router.get("/download/{file_id}", response_class=HTMLResponse)
@router.get("/dl/{file_id}", response_class=HTMLResponse)
async def download_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    watch_url = f"{Config.BASE_URL}/watch/{file_id}"
    return templates.TemplateResponse(
        "dl.html",
        {
            "request": request,
            "file_name": file_doc.get("file_name", "File"),
            "file_size": humanbytes(file_doc.get("file_size", 0)),
            "mime_type": file_doc.get("mime_type", "application/octet-stream"),
            "stream_url": stream_url,
            "watch_url": watch_url,
            "watermark": Config.WATERMARK,
            "watermark_url": Config.WATERMARK_URL,
            "file_id": file_id
        }
    )
