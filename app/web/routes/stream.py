import os
import math
import mimetypes
from urllib.parse import quote
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, Response
from app.database.repositories.file_repo import file_repo
from app.utils.cache import cache
from app.utils.logger import logger

router = APIRouter()

# 1MB buffer chunk for high throughput (12MB/s+ transfer capable)
STREAM_CHUNK_SIZE = 1024 * 1024 

async def get_target_media(bot, file_doc: dict):
    """Retrieves and caches Telegram media object from storage channel."""
    cache_key = f"tg_msg_{file_doc['chat_id']}_{file_doc['message_id']}"
    cached_media = await cache.get(cache_key)
    if cached_media:
        return cached_media

    msg = await bot.get_messages(file_doc["chat_id"], file_doc["message_id"])
    if not msg or not msg.media:
        return None
    media = msg.video or msg.document or msg.audio
    if media:
        await cache.set(cache_key, media, ttl=1800)
    return media

@router.get("/stream/{file_id}")
@router.get("/file/{file_id}")
async def stream_media(request: Request, file_id: str, range: str = Header(None)):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="Media file not found or expired.")

    bot = getattr(request.app.state, "bot", None)
    if not bot:
        raise HTTPException(status_code=500, detail="Bot engine offline.")

    media = await get_target_media(bot, file_doc)
    if not media:
        raise HTTPException(status_code=404, detail="Original media missing on Telegram servers.")

    file_size = getattr(media, "file_size", 0) or file_doc.get("file_size", 0)
    file_name = file_doc.get("file_name") or getattr(media, "file_name", "video.mp4")
    mime_type = file_doc.get("mime_type") or getattr(media, "mime_type", None)
    if not mime_type or mime_type == "application/octet-stream":
        mime_type, _ = mimetypes.guess_type(file_name)
    mime_type = mime_type or "video/mp4"

    start = 0
    end = file_size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range, Content-Type",
        "Content-Disposition": f'inline; filename="{quote(file_name)}"'
    }

    if range:
        try:
            range_val = range.strip()
            if range_val.startswith("bytes="):
                range_parts = range_val[6:].split("-")
                if range_parts[0]:
                    start = int(range_parts[0])
                if len(range_parts) > 1 and range_parts[1]:
                    end = int(range_parts[1])

                if start >= file_size or end >= file_size or start > end:
                    return Response(
                        status_code=416,
                        headers={"Content-Range": f"bytes */{file_size}"}
                    )
                status_code = 206
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        except Exception as e:
            logger.debug(f"Range parse error: {e}")

    content_length = (end - start) + 1
    headers["Content-Length"] = str(content_length)

    async def telegram_chunk_generator():
        start_chunk = start // STREAM_CHUNK_SIZE
        skip_in_first_chunk = start % STREAM_CHUNK_SIZE
        bytes_to_send = content_length
        is_first = True

        try:
            async for chunk in bot.stream_media(media, offset=start_chunk):
                if is_first:
                    chunk = chunk[skip_in_first_chunk:]
                    is_first = False

                if len(chunk) > bytes_to_send:
                    chunk = chunk[:bytes_to_send]

                yield chunk
                bytes_to_send -= len(chunk)
                if bytes_to_send <= 0:
                    break
        except Exception as err:
            logger.debug(f"Streaming pipe disconnected: {err}")

    return StreamingResponse(
        telegram_chunk_generator(),
        status_code=status_code,
        headers=headers
    )

@router.get("/download/{file_id}")
async def download_media(request: Request, file_id: str, range: str = Header(None)):
    """High-speed direct file download route with attachment header."""
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found or revoked.")

    bot = getattr(request.app.state, "bot", None)
    media = await get_target_media(bot, file_doc)
    if not media:
        raise HTTPException(status_code=404, detail="Media source missing on Telegram.")

    file_size = getattr(media, "file_size", 0) or file_doc.get("file_size", 0)
    file_name = file_doc.get("file_name") or getattr(media, "file_name", "file.mp4")

    start = 0
    end = file_size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "application/octet-stream",
        "Content-Disposition": f'attachment; filename="{quote(file_name)}"'
    }

    if range:
        try:
            range_val = range.strip()
            if range_val.startswith("bytes="):
                parts = range_val[6:].split("-")
                if parts[0]:
                    start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = int(parts[1])
                status_code = 206
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        except Exception:
            pass

    content_length = (end - start) + 1
    headers["Content-Length"] = str(content_length)

    async def download_stream_generator():
        start_chunk = start // STREAM_CHUNK_SIZE
        skip_first = start % STREAM_CHUNK_SIZE
        remaining = content_length
        first = True

        try:
            async for chunk in bot.stream_media(media, offset=start_chunk):
                if first:
                    chunk = chunk[skip_first:]
                    first = False
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                yield chunk
                remaining -= len(chunk)
                if remaining <= 0:
                    break
        except Exception:
            pass

    return StreamingResponse(
        download_stream_generator(),
        status_code=status_code,
        headers=headers
    )
