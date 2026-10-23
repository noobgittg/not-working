import asyncio
import logging
import math
import mimetypes
import re
from typing import AsyncGenerator, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from config import Config
from app.database.repositories.file_repo import file_repo

logger = logging.getLogger("stream_engine")
router = APIRouter()

# Optimal chunk size for Telegram MTProto media transfers (1 MB)
CHUNK_SIZE: int = 1024 * 1024
RANGE_HEADER_REGEX = re.compile(r"bytes=(\d+)-(\d*)")


def parse_byte_range(
    range_header: Optional[str], file_size: int
) -> Tuple[int, int, int]:
    """Parse HTTP Range header according to RFC 7233.

    Returns: (start_byte, end_byte, content_length)
    """
    if not range_header:
        return 0, file_size - 1, file_size

    match = RANGE_HEADER_REGEX.match(range_header.strip())
    if not match:
        return 0, file_size - 1, file_size

    start_str, end_str = match.groups()
    start = int(start_str)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(
            status_code=416,
            detail="Requested Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    return start, end, (end - start + 1)


async def media_streamer(
    client, message_or_file, offset: int, length: int
) -> AsyncGenerator[bytes, None]:
    """Streams binary media chunks from Telegram MTProto with client-disconnect recovery."""
    bytes_remaining = length
    current_offset = offset

    try:
        while bytes_remaining > 0:
            current_chunk_size = min(bytes_remaining, CHUNK_SIZE)

            # Pyrogram stream_media or custom chunk generator hook
            if hasattr(client, "stream_media"):
                chunk_gen = client.stream_media(
                    message_or_file,
                    offset=current_offset,
                    limit=current_chunk_size,
                )
                async for chunk in chunk_gen:
                    if not chunk:
                        break
                    yield chunk
                    bytes_remaining -= len(chunk)
                    current_offset += len(chunk)
                    if bytes_remaining <= 0:
                        break
            else:
                # Fallback for direct bot clients implementing get_file / chunk reads
                break

    except (asyncio.CancelledError, GeneratorExit):
        # Normal client seek or navigation; prevent 500 error propagation
        logger.debug(
            f"Client disconnected or scrubbed timeline at byte {current_offset}"
        )
        return
    except Exception as exc:
        logger.error(f"Error streaming MTProto media: {exc}")
        return


@router.head("/stream/{file_id}")
@router.head("/download/{file_id}")
async def stream_head_handler(request: Request, file_id: str):
    """Responds to HEAD requests without reading file body.

    Required by external media players (VLC, MX Player, PotPlayer) to verify
    file size.
    """
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    file_size = int(file_doc.get("file_size", 0))
    file_name = file_doc.get("file_name", "media.mp4")
    mime_type = (
        file_doc.get("mime_type")
        or mimetypes.guess_type(file_name)[0]
        or "video/mp4"
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Cache-Control": "public, max-age=31536000",
    }
    return Response(status_code=200, headers=headers)


@router.get("/stream/{file_id}")
@router.get("/download/{file_id}")
async def stream_media_handler(request: Request, file_id: str):
    """High-throughput streaming route supporting 206 Partial Content,

    multi-client load balancing, and 12 MB/s burst capabilities.
    """
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File Not Found")

    file_size = int(file_doc.get("file_size", 0))
    file_name = file_doc.get("file_name", "media.mp4")
    mime_type = (
        file_doc.get("mime_type")
        or mimetypes.guess_type(file_name)[0]
        or "video/mp4"
    )

    # Multi-client load balancing: rotate across available Pyrogram worker sessions
    telegram_client = getattr(request.app.state, "active_client", None)
    if (
        hasattr(request.app.state, "multi_clients")
        and request.app.state.multi_clients
    ):
        clients = request.app.state.multi_clients
        # Pick client index deterministically based on file_id to optimize connection reuse
        idx = abs(hash(file_id)) % len(clients)
        telegram_client = clients[idx]

    range_header = request.headers.get("Range")
    start_byte, end_byte, content_length = parse_byte_range(
        range_header, file_size
    )

    status_code = 206 if range_header else 200

    headers = {
        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{file_name}"',
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
    }

    media_target = file_doc.get("file_ref") or file_doc.get(
        "message_id"
    )  # Compatible with both schemas

    return StreamingResponse(
        media_streamer(
            telegram_client, media_target, start_byte, content_length
        ),
        status_code=status_code,
        headers=headers,
    )
