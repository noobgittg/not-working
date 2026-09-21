import asyncio
import os
from typing import Optional

import aiofiles
import aiohttp
from pyrogram import Client

from app.database.repositories.user_repo import user_repo
from app.services.ffmpeg_service import extract_frame_screenshot
from app.utils.helpers import is_safe_public_url
from app.utils.logger import logger
from config import Config

MAX_THUMBNAIL_BYTES = 8 * 1024 * 1024


async def download_thumbnail_url(url: str, target_path: str) -> Optional[str]:
    """Download only small, public image URLs; avoids common SSRF and memory issues."""
    if not is_safe_public_url(url):
        return None
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    try:
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        headers = {"User-Agent": "MMW-ProBot/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=False) as resp:
                if resp.status not in {200, 301, 302, 307, 308}:
                    return None
                if resp.status != 200:
                    location = resp.headers.get("Location")
                    if not location or not is_safe_public_url(location):
                        return None
                    async with session.get(location, allow_redirects=False) as redirected:
                        if redirected.status != 200:
                            return None
                        return await _save_response_image(redirected, target_path)
                return await _save_response_image(resp, target_path)
    except Exception as exc:
        logger.warning("Thumbnail URL download failed: %s", exc)
    return None


async def _save_response_image(resp: aiohttp.ClientResponse, target_path: str) -> Optional[str]:
    ctype = (resp.headers.get("Content-Type") or "").lower().split(";", 1)[0]
    if not ctype.startswith("image/"):
        return None
    declared = resp.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > MAX_THUMBNAIL_BYTES:
        return None
    total = 0
    async with aiofiles.open(target_path, "wb") as file_obj:
        async for chunk in resp.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if total > MAX_THUMBNAIL_BYTES:
                return None
            await file_obj.write(chunk)
    return target_path if os.path.isfile(target_path) and total else None


async def resolve_thumbnail(
    client: Client,
    user_id: int,
    workdir: str,
    video_path: Optional[str] = None,
    duration: int = 0,
) -> Optional[str]:
    """Resolve custom thumb -> configured URL -> generated video frame."""
    os.makedirs(workdir, exist_ok=True)
    user = await user_repo.get_user(user_id)

    if user and user.get("thumb_id"):
        try:
            custom_path = os.path.join(workdir, "custom_thumb.jpg")
            result = await client.download_media(user["thumb_id"], file_name=custom_path)
            if result and os.path.isfile(result):
                return result
        except Exception as exc:
            logger.warning("Error fetching custom thumbnail: %s", exc)

    tham_url = (user.get("tham_url") if user else None) or Config.THAM_URL
    if tham_url:
        cached_thumb = os.path.join(workdir, "tham_url.jpg")
        downloaded = await download_thumbnail_url(tham_url, cached_thumb)
        if downloaded:
            return downloaded

    if video_path and os.path.isfile(video_path):
        attrs_duration = duration
        if not attrs_duration:
            try:
                from app.services.ffmpeg_service import get_media_attributes
                attrs = await get_media_attributes(video_path)
                attrs_duration = attrs.get("duration", 0)
            except Exception:
                attrs_duration = 0
        return await extract_frame_screenshot(video_path, workdir, attrs_duration)
    return None
