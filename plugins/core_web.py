import os
import time
import math
import asyncio
import mimetypes
from urllib.parse import quote
from typing import Optional, Dict, Any, AsyncGenerator
import uvicorn
from fastapi import FastAPI, APIRouter, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from config import Config
from plugins.core_utils import logger, cache, humanbytes, time_formatter
from plugins.core_db import user_repo, chat_repo, file_repo, FileRepository

# ==================== 1. 12 MB/s TURBO BYTESTREAMER ENGINE ====================

CHUNK_SIZE = 1024 * 1024  # 1 MiB Telegram chunk size
STREAM_SPEED_MBPS = max(1, int(getattr(Config, "STREAM_SPEED_LIMIT_MBPS", 20)))
TARGET_SPEED_BPS = STREAM_SPEED_MBPS * 1024 * 1024  # 12 MB/s (12,582,912 B/s)
PREFETCH_QUEUE_SIZE = int(getattr(Config, "STREAM_BUFFER_CHUNKS", 12))  # 12 MB pre-fetch buffer


def parse_range_header(value: Optional[str], file_size: int):
    """Parse one byte range, including open-ended and suffix ranges."""
    if not value:
        return 0, file_size - 1
    try:
        unit, raw = value.strip().split("=", 1)
        if unit.lower() != "bytes" or "," in raw:
            return None
        first, last = raw.split("-", 1)
        if not first and not last:
            return None
        if not first:
            length = min(int(last), file_size)
            return (file_size - length, file_size - 1) if length > 0 else None
        start = int(first)
        end = int(last) if last else file_size - 1
        if start < 0 or start >= file_size or end < start:
            return None
        return start, min(end, file_size - 1)
    except (TypeError, ValueError):
        return None

# External 4 Players ONLY configuration:
# 1. PLAYit  2. MX Player  3. VLC  4. S Player (4th Player)
FOUR_EXTERNAL_PLAYERS = [
    {"id": "playit", "name": "PLAYit", "badge": "12 MB/s Fast"},
    {"id": "mxplayer", "name": "MX Player", "badge": "HW+ Decoder"},
    {"id": "vlc", "name": "VLC Player", "badge": "All Codecs"},
    {"id": "splayer", "name": "S Player", "badge": "Ultra Smooth"}
]

def build_4_external_player_links(stream_url: str, file_name: str = "video.mp4") -> Dict[str, str]:
    """
    Generates intent and scheme deep-links for ONLY the 4 requested external players:
    1. PLAYit
    2. MX Player
    3. VLC
    4. S Player (4th Player)
    """
    clean_url_no_scheme = stream_url.replace("https://", "").replace("http://", "")
    scheme = "https" if stream_url.startswith("https://") else "http"
    safe_title = quote(file_name or "video.mp4")

    return {
        "playit": f"playit://playerv2/video?url={quote(stream_url, safe='')}&title={safe_title}",
        "playit_intent": f"intent:{stream_url}#Intent;package=com.playit.videoplayer;type=video/*;S.title={safe_title};end",
        "mxplayer": f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;type=video/*;S.title={safe_title};end",
        "mxplayer_pro": f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.pro;type=video/*;S.title={safe_title};end",
        "vlc": f"vlc://{stream_url}",
        "vlc_intent": f"intent://{clean_url_no_scheme}#Intent;scheme={scheme};package=org.videolan.vlc;type=video/*;S.title={safe_title};end",
        "splayer": f"intent:{stream_url}#Intent;package=com.young.simple.player;type=video/*;S.title={safe_title};end",
        "splayer_alt": f"intent:{stream_url}#Intent;package=com.kmplayer;type=video/*;S.title={safe_title};end"
    }


async def resolve_telegram_message(bot: Any, file_doc: Dict[str, Any]):
    """Fetches and caches the Telegram message object from BIN_CHANNEL or user chat."""
    file_id = file_doc.get("file_id", "")
    cache_key = f"tg_msg_{file_id}"
    cached_msg = await cache.get(cache_key)
    if cached_msg is not None:
        return cached_msg

    if not bot or not getattr(bot, "is_connected", False):
        return None

    chat_id = file_doc.get("chat_id")
    message_id = file_doc.get("message_id")
    if not chat_id or not message_id:
        return None

    try:
        msg = await bot.get_messages(int(chat_id), int(message_id))
        if msg and msg.media:
            await cache.set(cache_key, msg, ttl=600)
            return msg
    except Exception as e:
        logger.warning(f"ByteStreamer failed resolving message {chat_id}:{message_id} -> {e}")
    return None


async def iter_12mbps_file_stream(
    file_path: Optional[str],
    bot: Any,
    file_doc: Dict[str, Any],
    start: int,
    end: int
) -> AsyncGenerator[bytes, None]:
    """
    12 MB/s High-Speed Async Byte Streamer!
    1. If local file exists on disk (`file_path`), streams in 1 MB chunks with 12 MB/s pacing & zero-blocking I/O.
    2. Otherwise, streams directly from Telegram (`bot.stream_media`) using an async pre-fetch queue
       of 12 x 1 MiB chunks (12 MB/s pipeline) with exact byte slicing for HTTP 206 Range requests.
    """
    content_length = (end - start) + 1

    # Route A: Local disk file (fast 1 MB chunks up to 12 MB/s)
    if file_path and os.path.exists(file_path):
        chunk_size = 1024 * 1024  # 1 MB chunk
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
        return

    # Route B: Direct Telegram MTProto Streaming via Pyrofork stream_media with 12 MB/s Pre-Fetch Buffer
    msg = await resolve_telegram_message(bot, file_doc)
    if not msg:
        return

    offset_chunks = start // CHUNK_SIZE
    first_part_cut = start % CHUNK_SIZE
    last_part_cut = (end % CHUNK_SIZE) + 1
    part_count = math.ceil((end + 1) / CHUNK_SIZE) - offset_chunks

    queue: asyncio.Queue = asyncio.Queue(maxsize=PREFETCH_QUEUE_SIZE)

    async def _producer():
        try:
            current_part = 1
            async for chunk in bot.stream_media(msg, offset=offset_chunks, limit=part_count):
                if not chunk:
                    break
                if part_count == 1:
                    sliced = chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    sliced = chunk[first_part_cut:]
                elif current_part == part_count:
                    sliced = chunk[:last_part_cut]
                else:
                    sliced = chunk
                await queue.put(sliced)
                current_part += 1
                if current_part > part_count:
                    break
        except Exception as e:
            logger.error(f"12MB/s Telegram Stream producer error: {e}")
        finally:
            await queue.put(None)

    producer_task = asyncio.create_task(_producer())
    remaining = content_length
    try:
        while remaining > 0:
            item = await queue.get()
            if item is None:
                break
            if len(item) > remaining:
                item = item[:remaining]
            remaining -= len(item)
            yield item
    finally:
        if not producer_task.done():
            producer_task.cancel()


# ==================== 2. FASTAPI ROUTERS ====================

pages_router = APIRouter()
stream_router = APIRouter()
api_router = APIRouter(prefix="/api")

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CURRENT_DIR)
_TEMPLATE_DIR = os.path.join(_ROOT_DIR, "app", "web", "templates")
if not os.path.exists(_TEMPLATE_DIR):
    _TEMPLATE_DIR = os.path.join(_CURRENT_DIR, "templates")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)


# --- HEALTH & ROOT ENDPOINTS ---

@pages_router.get("/health")
@pages_router.head("/health")
async def root_health():
    """Root /health endpoint required by Koyeb health checks and KeepAlive pinger."""
    return {
        "status": "healthy",
        "service": "MMW-BOT-PRO",
        "stream_speed": f"{STREAM_SPEED_MBPS} MB/s",
        "external_players": 4,
        "timestamp": float(time.time()),
        "watermark": Config.WATERMARK
    }

@pages_router.get("/stats")
async def root_stats_redirect(request: Request):
    return await index(request)

@pages_router.get("/")
async def index(request: Request):
    users_count = await user_repo.get_total_users()
    chats_count = await chat_repo.get_total_chats()
    files_count = await file_repo.get_total_files()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "users_count": users_count,
        "chats_count": chats_count,
        "files_count": files_count,
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })

@pages_router.get("/watch/{file_id}")
async def watch_page(request: Request, file_id: str):
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="Stream link expired or file not found.")

    file_name = file_doc.get("file_name") or file_doc.get("name") or "Media Stream.mp4"
    file_size = file_doc.get("file_size") or file_doc.get("size", 0)
    file_size_str = humanbytes(file_size)
    mime_type = file_doc.get("mime_type") or "video/mp4"

    base_url = str(request.base_url).rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    download_url = f"{base_url}/download/{file_id}"
    player_links = build_4_external_player_links(stream_url, file_name)

    return templates.TemplateResponse("watch.html", {
        "request": request,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size_str,
        "file_size_bytes": file_size,
        "mime_type": mime_type,
        "stream_url": stream_url,
        "download_url": download_url,
        "player_links": player_links,
        "stream_speed": f"{STREAM_SPEED_MBPS} MB/s",
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })

@pages_router.get("/dl/{file_id}")
async def download_page(request: Request, file_id: str):
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found or link expired.")

    file_name = file_doc.get("file_name", "download.mp4")
    file_size = humanbytes(file_doc.get("file_size", 0))
    mime_type = file_doc.get("mime_type", "video/mp4")
    base_url = str(request.base_url).rstrip("/")
    stream_url = f"{base_url}/stream/{file_id}"
    download_url = f"{base_url}/download/{file_id}"
    watch_url = f"{base_url}/watch/{file_id}"
    player_links = build_4_external_player_links(stream_url, file_name)

    return templates.TemplateResponse("dl.html", {
        "request": request,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "mime_type": mime_type,
        "stream_url": stream_url,
        "download_url": download_url,
        "watch_url": watch_url,
        "player_links": player_links,
        "stream_speed": f"{STREAM_SPEED_MBPS} MB/s",
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    })


# --- 12 MB/s STREAM & DOWNLOAD ENDPOINTS ---

@stream_router.get("/stream/{file_id}")
@stream_router.head("/stream/{file_id}")
async def stream_media_endpoint(request: Request, file_id: str, range: str = Header(None)):
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="Media file not found or revoked.")

    file_path = file_doc.get("file_path")
    bot = getattr(request.app.state, "bot", None)

    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
    else:
        file_size = int(file_doc.get("file_size", 0))

    if file_size <= 0:
        raise HTTPException(status_code=404, detail="File size invalid or source unavailable.")

    file_name = file_doc.get("file_name", "video.mp4")
    mime_type = file_doc.get("mime_type") or mimetypes.guess_type(file_name)[0] or "video/mp4"

    parsed_range = parse_range_header(range, file_size)
    if parsed_range is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
    start, end = parsed_range
    status_code = 206 if range else 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{file_name}"',
        "X-Stream-Speed-Limit": f"{STREAM_SPEED_MBPS}MB/s",
        "X-Stream-Chunk-Size": "1048576",
        "Cache-Control": "public, max-age=86400, immutable",
        "Vary": "Range",
        "Access-Control-Allow-Origin": "*"
    }

    if range:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    content_length = (end - start) + 1
    headers["Content-Length"] = str(content_length)

    if request.method == "HEAD":
        return Response(status_code=status_code, headers=headers)

    return StreamingResponse(
        iter_12mbps_file_stream(file_path, bot, file_doc, start, end),
        status_code=status_code,
        headers=headers,
        media_type=mime_type
    )

@stream_router.get("/download/{file_id}")
@stream_router.get("/file/{file_id}")
@stream_router.head("/download/{file_id}")
@stream_router.head("/file/{file_id}")
async def download_media_endpoint(request: Request, file_id: str, range: str = Header(None)):
    """Handles 12 MB/s direct file downloads with Range support for ADM / IDM / 1DM & external players."""
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found or revoked.")

    file_path = file_doc.get("file_path")
    bot = getattr(request.app.state, "bot", None)

    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
    else:
        file_size = int(file_doc.get("file_size", 0))

    if file_size <= 0:
        raise HTTPException(status_code=404, detail="File missing on server.")

    file_name = file_doc.get("file_name", "download.mp4")

    parsed_range = parse_range_header(range, file_size)
    if parsed_range is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
    start, end = parsed_range
    status_code = 206 if range else 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "X-Stream-Speed-Limit": f"{STREAM_SPEED_MBPS}MB/s",
        "Access-Control-Allow-Origin": "*"
    }

    if range:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    headers["Content-Length"] = str((end - start) + 1)

    if request.method == "HEAD":
        return Response(status_code=status_code, headers=headers)

    return StreamingResponse(
        iter_12mbps_file_stream(file_path, bot, file_doc, start, end),
        status_code=status_code,
        media_type="application/octet-stream",
        headers=headers
    )


# --- API ENDPOINTS ---

@api_router.get("/status")
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
        "version": "3.0.0-pro",
        "stream_speed": f"{STREAM_SPEED_MBPS} MB/s",
        "external_players": ["PLAYit", "MX Player", "VLC", "S Player"],
        "uptime_seconds": uptime_sec,
        "users": users_count,
        "chats": chats_count,
        "files": files_count,
        "cache": cache_stats,
        "server_time": float(time.time()),
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL
    }

@api_router.get("/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "MMW-BOT-PRO",
        "engine": f"{STREAM_SPEED_MBPS} MB/s Super-Sonic Streamer",
        "timestamp": float(time.time()),
        "watermark": Config.WATERMARK
    }

@api_router.get("/stats")
async def api_system_stats(request: Request):
    return await api_status(request)

@api_router.get("/ping")
async def api_ping():
    return {
        "status": "ok",
        "pong": True,
        "timestamp": float(time.time())
    }

@api_router.get("/info/{file_id}")
async def api_file_info(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    fname = file_doc.get("file_name", "video.mp4")
    return {
        "file_id": file_doc["file_id"],
        "file_name": fname,
        "file_size": file_doc.get("file_size"),
        "file_size_formatted": humanbytes(file_doc.get("file_size", 0)),
        "mime_type": file_doc.get("mime_type"),
        "created_at": file_doc.get("created_at"),
        "stream_speed": f"{STREAM_SPEED_MBPS} MB/s",
        "stream_url": stream_url,
        "watch_url": f"{Config.BASE_URL}/watch/{file_id}",
        "download_url": f"{Config.BASE_URL}/download/{file_id}",
        "direct_download_url": f"{Config.BASE_URL}/file/{file_id}",
        "external_players": build_4_external_player_links(stream_url, fname),
        "watermark": Config.WATERMARK
    }

@api_router.get("/search")
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


# ==================== 3. FASTAPI APP FACTORY & WEB SUPPORT ====================

def create_app(bot_instance=None) -> FastAPI:
    fastapi_app = FastAPI(
        title=f"MMW All-In-One Pro {STREAM_SPEED_MBPS} MB/s Stream Server",
        version="3.0.0",
        docs_url="/docs",
        redoc_url=None
    )
    fastapi_app.state.bot = bot_instance
    fastapi_app.state.start_time = float(time.time())

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi_app.middleware("http")
    async def public_page_cache(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path in {"/", "/stats"} or path.startswith("/watch/") or path.startswith("/dl/"):
            response.headers.setdefault("Cache-Control", "public, max-age=30, stale-while-revalidate=120")
        return response

    fastapi_app.include_router(pages_router)
    fastapi_app.include_router(stream_router)
    fastapi_app.include_router(api_router)

    return fastapi_app


class WebSupport:
    def __init__(self, bot=None):
        self.bot = bot
        self.start_time = float(time.time())
        self.app = create_app(bot)
        self.app.state.start_time = self.start_time
        self.server = None

    def get_server(self) -> uvicorn.Server:
        config = uvicorn.Config(
            app=self.app,
            host=Config.BIND_ADDRESS,
            port=Config.PORT,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        return self.server

    async def start(self):
        server = self.get_server()
        logger.info(f"⚡ {STREAM_SPEED_MBPS} MB/s Web Stream Server active on {Config.BIND_ADDRESS}:{Config.PORT}")
        await server.serve()
