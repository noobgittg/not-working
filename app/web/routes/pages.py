import os
import time
import json
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

def detect_file_category(mime_type: str, file_name: str) -> str:
    mime = (mime_type or "").lower()
    ext = os.path.splitext(file_name or "")[1].lower().replace(".", "")
    if mime.startswith("video/") or ext in ["mp4", "mkv", "webm", "avi", "mov", "flv", "ts", "m4v", "wmv", "3gp"]:
        return "video"
    if mime.startswith("audio/") or ext in ["mp3", "aac", "wav", "flac", "ogg", "m4a", "opus", "wma"]:
        return "audio"
    if mime.startswith("image/") or ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]:
        return "image"
    if mime == "application/pdf" or ext == "pdf":
        return "pdf"
    if ext in ["zip", "rar", "7z", "tar", "gz", "apk", "iso"]:
        return "archive"
    return "document"

@router.get("/watch/{file_id}", response_class=HTMLResponse)
async def watch_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    file_name = file_doc.get("file_name", "Media")
    file_size_bytes = file_doc.get("file_size", 0)
    file_size_str = humanbytes(file_size_bytes)
    mime_type = file_doc.get("mime_type", "video/mp4")
    category = detect_file_category(mime_type, file_name)

    raw_meta = file_doc.get("metadata") or {}
    duration_sec = raw_meta.get("duration", 0)
    duration_str = time_formatter(seconds=duration_sec) if duration_sec > 0 else "N/A"
    width = raw_meta.get("width", 0)
    height = raw_meta.get("height", 0)
    resolution = f"{width}x{height}" if width and height else ("HD" if category == "video" else "N/A")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    download_url = f"{Config.BASE_URL}/dl/{file_id}"
    direct_file_url = f"{Config.BASE_URL}/file/{file_id}"
    embed_url = f"{Config.BASE_URL}/embed/{file_id}"
    metadata_url = f"{Config.BASE_URL}/metadata/{file_id}"

    # Rich audio tracks
    audio_tracks = raw_meta.get("audio_streams", [])
    if not audio_tracks:
        audio_tracks = [
            {"index": 1, "language": "Default", "language_code": "und", "title": "Audio Track 1", "codec": "AAC", "channels": 2}
        ]

    # Subtitles
    subtitle_tracks = raw_meta.get("subtitle_streams", [])

    # Format languages
    languages_list = sorted(list(set([a.get("language", "English").title() for a in audio_tracks if a.get("language")])))
    languages_str = ", ".join(languages_list) if languages_list else "Undetermined"

    client_data = {
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size_str,
        "file_size_bytes": file_size_bytes,
        "mime_type": mime_type,
        "category": category,
        "duration_str": duration_str,
        "duration_sec": duration_sec,
        "resolution": resolution,
        "video_codec": raw_meta.get("video_codec", "H.264 / AVC"),
        "audio_codec": raw_meta.get("audio_codec", "AAC Stereo"),
        "stream_url": stream_url,
        "download_url": download_url,
        "direct_file_url": direct_file_url,
        "embed_url": embed_url,
        "metadata_url": metadata_url,
        "audio_tracks": audio_tracks,
        "subtitle_tracks": subtitle_tracks,
        "languages_str": languages_str,
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    }

    return render_template(
        templates, request, "watch.html",
        {
            **client_data,
            "client_json": json.dumps(client_data)
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
@router.get("/dl/{file_id}/page", response_class=HTMLResponse)
async def download_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    dl_url = f"{Config.BASE_URL}/dl/{file_id}"
    return render_template(
        templates, request, "dl.html",
        {
            "file_id": file_id,
            "file_name": file_doc.get("file_name", "File"),
            "file_size": humanbytes(file_doc.get("file_size", 0)),
            "stream_url": stream_url,
            "download_url": dl_url,
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
