import re
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from config import Config
from app.database.repositories.file_repo import file_repo

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
                "Access-Control-Allow-Origin": "*"
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
        "Access-Control-Allow-Origin": "*"
    }
    return StreamingResponse(full_streamer(), status_code=200, headers=headers)

@router.get("/file/{file_id}")
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
