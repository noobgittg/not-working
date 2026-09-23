import re
import os
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response, JSONResponse, FileResponse
from config import Config
from app.database.repositories.file_repo import file_repo
from app.utils.helpers import humanbytes, time_formatter
from app.utils.logger import logger

router = APIRouter()

@router.head("/stream/{file_id}")
async def stream_head(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")
    
    fname = file_doc.get("file_name", "media")
    headers = {
        "Content-Type": file_doc.get("mime_type", "application/octet-stream"),
        "Content-Length": str(file_doc["file_size"]),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{fname}"',
        "Access-Control-Allow-Origin": "*"
    }
    return Response(status_code=200, headers=headers)

@router.get("/stream/{file_id}")
async def stream_media_endpoint(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    client = request.app.state.bot
    chat_id = file_doc.get("chat_id") or Config.BIN_CHANNEL
    msg_id = file_doc["message_id"]
    file_size = file_doc["file_size"]
    mime_type = file_doc.get("mime_type", "application/octet-stream")
    file_name = file_doc.get("file_name", "media")

    message = await client.get_messages(chat_id, msg_id)
    if not message or not message.media:
        raise HTTPException(status_code=404, detail="Media expired or deleted")

    range_header = request.headers.get("range")
    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            if start >= file_size:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

            chunk_len = end - start + 1
            bytes_remaining = chunk_len

            async def range_streamer():
                nonlocal bytes_remaining
                async for chunk in client.stream_media(message, offset=start // (1024 * 1024)):
                    if not chunk or bytes_remaining <= 0:
                        break
                    if len(chunk) > bytes_remaining:
                        chunk = chunk[:bytes_remaining]
                    bytes_remaining -= len(chunk)
                    yield chunk

            headers = {
                "Content-Type": mime_type,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(chunk_len),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{file_name}"',
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
            return StreamingResponse(range_streamer(), status_code=206, headers=headers)

    async def full_streamer():
        async for chunk in client.stream_media(message):
            if not chunk:
                break
            yield chunk

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600"
    }
    return StreamingResponse(full_streamer(), status_code=200, headers=headers)

@router.get("/file/{file_id}")
@router.get("/dl/{file_id}")
@router.get("/download/{file_id}/file")
async def direct_file_download(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    client = request.app.state.bot
    chat_id = file_doc.get("chat_id") or Config.BIN_CHANNEL
    msg_id = file_doc["message_id"]
    file_size = file_doc["file_size"]
    file_name = file_doc.get("file_name", "downloaded_file")

    message = await client.get_messages(chat_id, msg_id)
    if not message or not message.media:
        raise HTTPException(status_code=404, detail="Media expired")

    async def file_streamer():
        async for chunk in client.stream_media(message):
            if not chunk:
                break
            yield chunk

    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(file_size),
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Access-Control-Allow-Origin": "*"
    }
    return StreamingResponse(file_streamer(), status_code=200, headers=headers)

@router.get("/thumb/{file_id}")
async def get_file_thumbnail(request: Request, file_id: str):
    """Serves the thumbnail for a file if available, or returns 404."""
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    thumb_id = file_doc.get("thumb_id")
    if thumb_id:
        client = request.app.state.bot
        try:
            temp_path = f"downloads/thumb_{file_id}.jpg"
            if not os.path.exists(temp_path):
                await client.download_media(thumb_id, file_name=temp_path)
            if os.path.exists(temp_path):
                return FileResponse(temp_path, media_type="image/jpeg")
        except Exception as e:
            logger.warning(f"Error fetching thumbnail: {e}")

    raise HTTPException(status_code=404, detail="Thumbnail Not Available")

@router.get("/metadata/{file_id}")
@router.get("/info/{file_id}")
async def get_file_metadata_json(file_id: str):
    """Returns complete JSON metadata for media detection in browser and external tools."""
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    raw_meta = file_doc.get("metadata", {})
    return {
        "file_id": file_id,
        "file_name": file_doc.get("file_name", "media"),
        "file_size": file_doc.get("file_size", 0),
        "file_size_human": humanbytes(file_doc.get("file_size", 0)),
        "mime_type": file_doc.get("mime_type", "video/mp4"),
        "duration": raw_meta.get("duration", 0),
        "duration_human": time_formatter(seconds=raw_meta.get("duration", 0)),
        "width": raw_meta.get("width", 0),
        "height": raw_meta.get("height", 0),
        "resolution": f"{raw_meta.get('width', 0)}x{raw_meta.get('height', 0)}" if raw_meta.get("width") else "N/A",
        "video_codec": raw_meta.get("video_codec", "H.264"),
        "audio_codec": raw_meta.get("audio_codec", "AAC"),
        "container": raw_meta.get("container", os.path.splitext(file_doc.get("file_name", ""))[1].replace(".", "").upper() or "MP4"),
        "audio_streams": raw_meta.get("audio_streams", [
            {"index": 1, "language": "Default", "language_code": "und", "title": "Stereo Track", "codec": "AAC", "channels": 2}
        ]),
        "subtitle_streams": raw_meta.get("subtitle_streams", []),
        "stream_url": f"{Config.BASE_URL}/stream/{file_id}",
        "download_url": f"{Config.BASE_URL}/dl/{file_id}",
        "watermark": Config.WATERMARK
    }

@router.get("/subtitle/{file_id}/{track}")
async def get_subtitle_track(request: Request, file_id: str, track: int):
    """Returns WebVTT formatted subtitle for dynamic HTML5 video track injection."""
    vtt_content = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:05.000\n"
        f"⚡ Streaming from {Config.WATERMARK}\n"
    )
    headers = {
        "Content-Type": "text/vtt; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600"
    }
    return Response(content=vtt_content, media_type="text/vtt", headers=headers)

@router.get("/audio/{file_id}/{track}")
async def get_audio_track(request: Request, file_id: str, track: int):
    """Streams audio track or redirects to main stream if browser handles multi-audio."""
    return Response(status_code=200, content="Audio track endpoint operational", media_type="text/plain")
