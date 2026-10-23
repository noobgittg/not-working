import time
from fastapi import APIRouter, HTTPException, Request
from config import Config
from app.database.repositories.file_repo import file_repo
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.cache import cache
from app.utils.helpers import humanbytes

router = APIRouter(prefix="/api")

@router.get("/status")
async def api_status(request: Request):
    users_count = await user_repo.get_total_users()
    chats_count = await chat_repo.get_total_chats()
    files_count = await file_repo.get_total_files()
    cache_stats = await cache.get_stats()
    start_time = getattr(request.app.state, "start_time", float(time.time()))
    uptime_sec = int(float(time.time()) - start_time)

    return {
        "status": "operational",
        "service": "MMW All-In-One Pro Engine",
        "version": "2.5.0-pro",
        "uptime_seconds": uptime_sec,
        "users": users_count,
        "chats": chats_count,
        "files": files_count,
        "cache": cache_stats,
        "server_time": float(time.time()),
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    }

@router.get("/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "MMW-BOT-PRO",
        "engine": "Super-Sonic Ultra-Fast",
        "timestamp": float(time.time()),
        "watermark": Config.WATERMARK
    }

@router.get("/stats")
async def api_system_stats(request: Request):
    return await api_status(request)

@router.get("/ping")
async def api_ping():
    return {
        "status": "ok",
        "pong": True,
        "timestamp": float(time.time())
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
        "file_size_formatted": humanbytes(file_doc.get("file_size", 0)),
        "mime_type": file_doc.get("mime_type"),
        "created_at": file_doc.get("created_at"),
        "stream_url": f"{Config.BASE_URL}/stream/{file_id}",
        "watch_url": f"{Config.BASE_URL}/watch/{file_id}",
        "download_url": f"{Config.BASE_URL}/download/{file_id}",
        "direct_download_url": f"{Config.BASE_URL}/file/{file_id}",
        "watermark": Config.WATERMARK
    }

@router.get("/search")
async def api_search_files(q: str = ""):
    if not q or not q.strip():
        return {"query": "", "count": 0, "results": []}
    files = await file_repo.search_files(q.strip(), limit=20)
    results = []
    for f in files:
        fid = f.get("file_id")
        results.append({
            "file_id": fid,
            "file_name": f.get("file_name", "Media"),
            "file_size": f.get("file_size", 0),
            "file_size_formatted": humanbytes(f.get("file_size", 0)),
            "mime_type": f.get("mime_type", "application/octet-stream"),
            "created_at": f.get("created_at"),
            "stream_url": f"{Config.BASE_URL}/stream/{fid}",
            "watch_url": f"{Config.BASE_URL}/watch/{fid}",
            "download_url": f"{Config.BASE_URL}/download/{fid}",
            "direct_download_url": f"{Config.BASE_URL}/file/{fid}"
        })
    return {"query": q, "count": len(results), "results": results}
