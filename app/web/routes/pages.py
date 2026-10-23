"""
Pages Route Module
Handles rendering of watch pages, download pages, and index/home pages.
Supports asynchronous web frameworks (Quart / FastAPI pattern) and Flask fallback.
"""

import os

try:
    from quart import Blueprint, render_template, abort, request
    using_quart = True
except ImportError:
    using_quart = False

if not using_quart:
    from flask import Blueprint, render_template, abort, request, current_app

from app.database.repositories.file_repo import FileRepository

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
async def index():
    """Home / Index page route."""
    if using_quart:
        return await render_template("index.html")
    return render_template("index.html")

@pages_bp.route("/watch/<file_id>")
async def watch_page(file_id):
    """
    Renders the cinematic video player watch page for a given file ID / hash.
    Validates file existence in MongoDB and supplies stream & download URLs.
    """
    try:
        # Fetch file metadata from repository
        file_doc = await FileRepository.get_file_by_id(file_id)
        if not file_doc:
            abort(404, description="Stream link expired or file not found.")

        file_name = file_doc.get("file_name") or file_doc.get("name") or "Media Stream"
        file_size = file_doc.get("file_size") or file_doc.get("size", 0)

        # Construct stream and download URLs dynamically from request host
        base_url = request.host_url.rstrip("/")
        stream_url = f"{base_url}/stream/{file_id}"
        download_url = f"{base_url}/download/{file_id}"

        template_data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "stream_url": stream_url,
            "download_url": download_url
        }

        if using_quart:
            return await render_template("watch.html", **template_data)
        return render_template("watch.html", **template_data)

    except Exception as e:
        if using_quart:
            print(f"Error loading watch page for {file_id}: {e}")
        else:
            current_app.logger.error(f"Error loading watch page for {file_id}: {e}")
        abort(500, description="Internal Server Error while generating watch page.")


@pages_bp.route("/dl/<file_id>")
async def download_page(file_id):
    """Renders the dedicated download redirect page."""
    try:
        file_doc = await FileRepository.get_file_by_id(file_id)
        if not file_doc:
            abort(404, description="File not found or link expired.")

        file_name = file_doc.get("file_name", "download")
        base_url = request.host_url.rstrip("/")
        download_url = f"{base_url}/download/{file_id}"

        template_data = {
            "file_name": file_name,
            "download_url": download_url
        }

        if using_quart:
            return await render_template("dl.html", **template_data)
        return render_template("dl.html", **template_data)
        
    except Exception as e:
        if not using_quart:
            current_app.logger.error(f"Error loading download page for {file_id}: {e}")
        abort(500, description="Internal Server Error.")
