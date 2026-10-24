import os
from urllib.parse import quote
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from config import Config

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def build_external_player_urls(stream_url: str):
    """Generates direct Android/Desktop launch intents for 4 specific players."""
    return {
        "mx_player": f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;type=video/*;end",
        "vlc": f"vlc://{stream_url.replace('https://', '').replace('http://', '')}",
        "playit": f"playit://playvideo?link={quote(stream_url)}",
        "kmplayer": f"intent:{stream_url}#Intent;package=com.kmplayer;type=video/*;end"
    }

@router.get("/")
async def index(request: Request):
    users_cnt = await user_repo.get_total_users()
    chats_cnt = await chat_repo.get_total_chats()
    files_cnt = await file_repo.get_total_files()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "users_count": users_cnt,
        "chats_count": chats_cnt,
        "files_count": files_cnt,
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })

@router.get("/watch/{file_id}")
async def watch_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="Stream link expired or revoked.")

    file_name = file_doc.get("file_name", "Media Stream")
    file_size = file_doc.get("file_size", 0)

    base_url = str(request.base_url).rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    download_url = f"{base_url}/download/{file_id}"

    players = build_external_player_urls(stream_url)

    return templates.TemplateResponse("watch.html", {
        "request": request,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "stream_url": stream_url,
        "download_url": download_url,
        "mx_url": players["mx_player"],
        "vlc_url": players["vlc"],
        "playit_url": players["playit"],
        "kmplayer_url": players["kmplayer"],
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })

@router.get("/dl/{file_id}")
async def download_page(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found or revoked.")

    file_name = file_doc.get("file_name", "Download")
    file_size = file_doc.get("file_size", 0)
    base_url = str(request.base_url).rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    download_url = f"{base_url}/download/{file_id}"

    players = build_external_player_urls(stream_url)

    return templates.TemplateResponse("dl.html", {
        "request": request,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "download_url": download_url,
        "watch_url": f"{base_url}/watch/{file_id}",
        "mime_type": file_doc.get("mime_type", "video/mp4"),
        "mx_url": players["mx_player"],
        "vlc_url": players["vlc"],
        "playit_url": players["playit"],
        "kmplayer_url": players["kmplayer"],
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })
