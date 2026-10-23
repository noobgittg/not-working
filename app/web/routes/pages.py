import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.database.repositories.file_repo import FileRepository

router = APIRouter()

# Setup Jinja2 templates directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.get("/")
async def index(request: Request):
    """Home / Index page route."""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/watch/{file_id}")
async def watch_page(request: Request, file_id: str):
    """
    Renders the cinematic video player watch page for a given file ID / hash.
    Validates file existence in MongoDB and supplies stream & download URLs.
    """
    try:
        file_doc = await FileRepository.get_file_by_id(file_id)
        if not file_doc:
            raise HTTPException(status_code=404, detail="Stream link expired or file not found.")

        file_name = file_doc.get("file_name") or file_doc.get("name") or "Media Stream"
        file_size = file_doc.get("file_size") or file_doc.get("size", 0)

        base_url = str(request.base_url).rstrip("/")
        stream_url = f"{base_url}/stream/{file_id}"
        download_url = f"{base_url}/download/{file_id}"

        return templates.TemplateResponse("watch.html", {
            "request": request,
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "stream_url": stream_url,
            "download_url": download_url
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error while generating watch page.")

@router.get("/dl/{file_id}")
async def download_page(request: Request, file_id: str):
    """Renders the dedicated download redirect page."""
    try:
        file_doc = await FileRepository.get_file_by_id(file_id)
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found or link expired.")

        file_name = file_doc.get("file_name", "download")
        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/download/{file_id}"

        return templates.TemplateResponse("dl.html", {
            "request": request,
            "file_name": file_name,
            "download_url": download_url
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error.")
