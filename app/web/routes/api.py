import time
from fastapi import APIRouter, HTTPException, Query
from config import Config
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.helpers import time_formatter, humanbytes

router = APIRouter(prefix="/api")
API_START_TIME = time.time()

@router.get("/status")
async def api_status():
    users_count = await user_repo.get_total_users()
    files_count = await file_repo.get_total_files()
    return {
        "status": "operational",
        "users": users_count,
        "files": files_count,
        "watermark": Config.WATERMARK,
        "engine": "Super-Sonic Ultra-Fast",
        "version": "2.5.0"
    }

@router.get("/stats")
async def api_stats():
    users_count = await user_repo.get_total_users()
    chats_count = await chat_repo.get_total_chats()
    files_count = await file_repo.get_total_files()
    banned_count = await user_repo.get_banned_users_count()
    uptime_sec = round(time.time() - API_START_TIME)

    return {
        "status": "online",
        "uptime": time_formatter(seconds=uptime_sec),
        "total_users": users_count,
        "total_chats": chats_count,
        "total_files": files_count,
        "banned_users": banned_count,
        "keepalive_frequency": "10s",
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL,
        "version": "2.5.0"
    }

@router.get("/info/{file_id}")
async def api_file_info(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": file_doc["file_id"],
        "file_name": file_doc.get("file_name"),
        "file_size": file_doc.get("file_size"),
        "file_size_human": humanbytes(file_doc.get("file_size", 0)),
        "mime_type": file_doc.get("mime_type"),
        "stream_url": f"{Config.BASE_URL}/stream/{file_id}",
        "watch_url": f"{Config.BASE_URL}/watch/{file_id}",
        "download_url": f"{Config.BASE_URL}/file/{file_id}",
        "embed_url": f"{Config.BASE_URL}/embed/{file_id}",
        "watermark": Config.WATERMARK
    }

@router.get("/search")
async def api_search(q: str = Query(..., min_length=1)):
    results = await file_repo.search_files(q, limit=25)
    formatted = []
    for f in results:
        fid = f.get("file_id")
        formatted.append({
            "file_id": fid,
            "file_name": f.get("file_name"),
            "file_size": f.get("file_size"),
            "file_size_human": humanbytes(f.get("file_size", 0)),
            "mime_type": f.get("mime_type"),
            "watch_url": f"{Config.BASE_URL}/watch/{fid}",
            "stream_url": f"{Config.BASE_URL}/stream/{fid}",
            "download_url": f"{Config.BASE_URL}/file/{fid}"
        })
    return {
        "query": q,
        "total_results": len(formatted),
        "results": formatted
    }
