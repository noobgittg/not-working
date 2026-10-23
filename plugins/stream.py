import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, Response

from config import Config
from file_repo import file_repo
from logger import logger

router = APIRouter()
CHUNK_SIZE = 1024 * 1024


def _file_size(file_doc: dict) -> int:
    try:
        return max(0, int(file_doc.get("file_size") or 0))
    except (TypeError, ValueError):
        return 0


def _parse_byte_range(range_header: str | None, file_size: int):
    if range_header is None:
        return None
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not match or file_size <= 0 or not (match.group(1) or match.group(2)):
        raise ValueError("Invalid byte range")
    first, last = match.groups()
    try:
        if not first:
            suffix_size = int(last)
            if suffix_size <= 0:
                raise ValueError
            return max(0, file_size - suffix_size), file_size - 1
        start = int(first)
        end = int(last) if last else file_size - 1
        if start >= file_size or end < start:
            raise ValueError
        return start, min(end, file_size - 1)
    except ValueError as exc:
        raise ValueError("Invalid byte range") from exc


async def _iter_media(client, message, start: int = 0, length: int | None = None):
    remaining = length
    trim_start = start % CHUNK_SIZE
    try:
        stream = client.stream_media(message, offset=start // CHUNK_SIZE) if start else client.stream_media(message)
        async for chunk in stream:
            if not chunk:
                break
            if trim_start:
                if len(chunk) <= trim_start:
                    trim_start -= len(chunk)
                    continue
                chunk = chunk[trim_start:]
                trim_start = 0
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk = chunk[:remaining]
                remaining -= len(chunk)
            if chunk:
                yield chunk
            if remaining is not None and remaining <= 0:
                break
    except Exception as exc:
        logger.warning("Telegram media streaming failed (%s).", type(exc).__name__)
        raise


@router.head("/stream/{file_id}")
async def stream_head(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    file_size = _file_size(file_doc)
    file_name = re.sub(r"[\r\n\x00-\x1f\x7f/\\]", "_", str(file_doc.get("file_name") or "media"))[:255]
    headers = {
        "Content-Type": file_doc.get("mime_type") or "application/octet-stream",
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(file_name, safe='')}",
    }
    return Response(status_code=200, headers=headers)


@router.get("/stream/{file_id}")
async def stream_media_endpoint(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        client = request.app.state.bot
        chat_id = file_doc.get("chat_id") or Config.BIN_CHANNEL
        message_id = int(file_doc["message_id"])
        file_size = _file_size(file_doc)
    except (AttributeError, KeyError, TypeError, ValueError):
        logger.warning("Stored stream metadata is incomplete")
        raise HTTPException(status_code=404, detail="File metadata is unavailable")

    try:
        message = await client.get_messages(chat_id, message_id)
    except Exception as exc:
        logger.warning("Telegram media lookup failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Unable to retrieve media from Telegram")

    if not message or not message.media:
        raise HTTPException(status_code=404, detail="Media is unavailable or was deleted")

    mime_type = file_doc.get("mime_type") or "application/octet-stream"
    file_name = re.sub(
        r"[\r\n\x00-\x1f\x7f/\\]", "_", str(file_doc.get("file_name") or "media")
    )[:255]
    disposition = f"inline; filename*=UTF-8''{quote(file_name, safe='')}"
    range_header = request.headers.get("range")
    try:
        byte_range = _parse_byte_range(range_header, file_size)
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    if byte_range is not None:
        start, end = byte_range
        content_length = end - start + 1
        return StreamingResponse(
            _iter_media(client, message, start=start, length=content_length),
            status_code=206,
            headers={
                "Content-Type": mime_type,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Content-Disposition": disposition,
            },
        )

    async def full_streamer():
        async for chunk in _iter_media(client, message):
            yield chunk

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": disposition,
    }
    return StreamingResponse(full_streamer(), status_code=200, headers=headers)


@router.head("/file/{file_id}")
@router.head("/download/file/{file_id}")
async def direct_file_head(file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    file_size = _file_size(file_doc)
    file_name = re.sub(
        r"[\r\n\x00-\x1f\x7f/\\]", "_", str(file_doc.get("file_name") or "downloaded_file")
    )[:255]
    return Response(
        status_code=200,
        headers={
            "Content-Type": file_doc.get("mime_type") or "application/octet-stream",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name, safe='')}",
        },
    )


@router.get("/file/{file_id}")
@router.get("/download/file/{file_id}")
async def direct_file_download(request: Request, file_id: str):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        client = request.app.state.bot
        chat_id = file_doc.get("chat_id") or Config.BIN_CHANNEL
        message_id = int(file_doc["message_id"])
        file_size = _file_size(file_doc)
    except (AttributeError, KeyError, TypeError, ValueError):
        logger.warning("Stored download metadata is incomplete")
        raise HTTPException(status_code=404, detail="File metadata is unavailable")

    try:
        message = await client.get_messages(chat_id, message_id)
    except Exception as exc:
        logger.warning("Telegram download lookup failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Unable to retrieve file from Telegram")

    if not message or not message.media:
        raise HTTPException(status_code=404, detail="Media is unavailable or was deleted")

    file_name = re.sub(
        r"[\r\n\x00-\x1f\x7f/\\]", "_", str(file_doc.get("file_name") or "downloaded_file")
    )[:255]
    mime_type = file_doc.get("mime_type") or "application/octet-stream"
    range_header = request.headers.get("range")
    try:
        byte_range = _parse_byte_range(range_header, file_size)
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    if byte_range is not None:
        start, end = byte_range
        content_length = end - start + 1
        return StreamingResponse(
            _iter_media(client, message, start=start, length=content_length),
            status_code=206,
            headers={
                "Content-Type": mime_type,
                "Content-Length": str(content_length),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name, safe='')}",
                "Accept-Ranges": "bytes",
            },
        )

    async def file_streamer():
        async for chunk in _iter_media(client, message):
            yield chunk

    return StreamingResponse(
        file_streamer(),
        status_code=200,
        headers={
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name, safe='')}",
            "Accept-Ranges": "bytes",
        },
    )
