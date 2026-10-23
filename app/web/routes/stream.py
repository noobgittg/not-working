import os
import mimetypes
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, Response
from app.database.repositories.file_repo import FileRepository

router = APIRouter()

@router.get("/stream/{file_id}")
async def stream_media(request: Request, file_id: str, range: str = Header(None)):
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="Media file not found or expired.")

    file_path = file_doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File source missing on server.")

    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "video/mp4"

    # Handle Range Requests
    start = 0
    end = file_size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
    }

    if range:
        try:
            range_type, range_val = range.strip().split("=")
            if range_type == "bytes":
                range_parts = range_val.split("-")
                if range_parts[0]:
                    start = int(range_parts[0])
                if range_parts[1]:
                    end = int(range_parts[1])
                
                if start >= file_size or end >= file_size or start > end:
                    return Response(
                        status_code=416,
                        headers={"Content-Range": f"bytes */{file_size}"}
                    )
                
                status_code = 206
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        except Exception:
            pass

    content_length = (end - start) + 1
    headers["Content-Length"] = str(content_length)

    def iter_file():
        chunk_size = 512 * 1024  # 512 KB optimized chunk size for high throughput
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_to_read = min(chunk_size, remaining)
                data = f.read(chunk_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iter_file(),
        status_code=status_code,
        headers=headers
    )

@router.get("/download/{file_id}")
async def download_media(request: Request, file_id: str):
    """Handles direct file downloads with proper attachment headers."""
    file_doc = await FileRepository.get_file_by_id(file_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found.")

    file_path = file_doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on server.")

    file_name = file_doc.get("file_name", os.path.basename(file_path))
    file_size = os.path.getsize(file_path)
    
    def iter_file():
        chunk_size = 1024 * 1024
        with open(file_path, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                yield data

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Length": str(file_size)
        }
    )
