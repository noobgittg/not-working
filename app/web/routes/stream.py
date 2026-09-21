import re
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.database.repositories.file_repo import file_repo
from app.utils.helpers import quote_filename_for_header
from config import Config

router = APIRouter()
STREAM_CHUNK_SIZE = 1024 * 1024
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _parse_range(value: str, size: int) -> Optional[Tuple[int, int]]:
    if not value or not value.startswith("bytes=") or "," in value or size <= 0:
        return None
    match = _RANGE_RE.match(value.strip())
    if not match:
        return None
    start_raw, end_raw = match.groups()
    try:
        if not start_raw:
            suffix = int(end_raw)
            if suffix <= 0:
                return None
            start = max(0, size - min(suffix, size))
            return start, size - 1
        start = int(start_raw)
        if start >= size:
            return None
        end = int(end_raw) if end_raw else size - 1
        if end < start:
            return None
        return start, min(end, size - 1)
    except ValueError:
        return None


def _headers(mime: str, filename: str, length: int, disposition: str = "inline"):
    return {
        "Content-Type": mime or "application/octet-stream",
        "Content-Length": str(length),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'{disposition}; filename="{quote_filename_for_header(filename)}"',
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
    }


async def _get_message(request: Request, file_doc: dict):
    client = request.app.state.bot
    chat_id = file_doc.get("chat_id") or Config.BIN_CHANNEL
    message_id = file_doc.get("message_id")
    if not message_id:
        raise HTTPException(status_code=404, detail="Media reference missing")
    try:
        message = await client.get_messages(chat_id, int(message_id))
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Media expired or unavailable") from exc
    if not message or not message.media:
        raise HTTPException(status_code=404, detail="Media expired or deleted")
    return client, message


@router.head("/stream/{file_id}")
async def stream_head(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")
    return Response(status_code=200, headers=_headers(file_doc.get("mime_type"), file_doc.get("file_name", "media"), int(file_doc.get("file_size", 0))))


@router.get("/stream/{file_id}")
async def stream_media_endpoint(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")
    size = int(file_doc.get("file_size", 0) or 0)
    mime = file_doc.get("mime_type") or "application/octet-stream"
    filename = file_doc.get("file_name") or "media"
    client, message = await _get_message(request, file_doc)

    range_value = request.headers.get("range")
    if range_value:
        parsed = _parse_range(range_value, size)
        if parsed is None:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"})
        start, end = parsed
        remaining = end - start + 1
        offset = start // STREAM_CHUNK_SIZE
        skip = start % STREAM_CHUNK_SIZE

        async def range_streamer():
            nonlocal remaining, skip
            async for chunk in client.stream_media(message, offset=offset):
                if not chunk or remaining <= 0:
                    break
                if skip:
                    if len(chunk) <= skip:
                        skip -= len(chunk)
                        continue
                    chunk = chunk[skip:]
                    skip = 0
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                remaining -= len(chunk)
                if chunk:
                    yield chunk
                if remaining <= 0:
                    break

        headers = _headers(mime, filename, end - start + 1)
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return StreamingResponse(range_streamer(), status_code=206, headers=headers)

    async def full_streamer():
        async for chunk in client.stream_media(message):
            if chunk:
                yield chunk

    return StreamingResponse(full_streamer(), status_code=200, headers=_headers(mime, filename, size))


@router.get("/file/{file_id}")
async def direct_file_download(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")
    client, message = await _get_message(request, file_doc)
    size = int(file_doc.get("file_size", 0) or 0)
    filename = file_doc.get("file_name") or "downloaded_file"

    async def file_streamer():
        async for chunk in client.stream_media(message):
            if chunk:
                yield chunk

    return StreamingResponse(
        file_streamer(), status_code=200,
        headers=_headers("application/octet-stream", filename, size, "attachment"),
    )
