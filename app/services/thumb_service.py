import os
import aiohttp
import aiofiles
from typing import Optional
from pyrogram import Client
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.logger import logger
from app.utils.helpers import is_valid_url
from .ffmpeg_service import extract_frame_screenshot

async def download_thumbnail_url(url: str, target_path: str) -> Optional[str]:
    if not url or not is_valid_url(url):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    async with aiofiles.open(target_path, "wb") as f:
                        await f.write(await resp.read())
                    return target_path
    except Exception as e:
        logger.warning(f"Failed to download thumbnail from URL {url}: {e}")
    return None

async def resolve_thumbnail(
    client: Client,
    user_id: int,
    temp_dir: str,
    video_path: Optional[str] = None,
    duration: int = 0
) -> Optional[str]:
    """
    Resolves the best available thumbnail for a media file:
    1. Custom user thumbnail stored in DB
    2. Fallback URL thumbnail (THAM_URL)
    3. Auto-extracted video frame screenshot using FFmpeg
    Guaranteed to return a valid string path or None. Never returns a tuple.
    """
    if os.path.isfile(temp_dir):
        target_dir = os.path.dirname(temp_dir)
    else:
        target_dir = temp_dir
    os.makedirs(target_dir, exist_ok=True)

    user = await user_repo.get_user(user_id)

    # 1. Custom user thumbnail
    if user and user.get("thumb_id"):
        try:
            custom_path = os.path.join(target_dir, "custom_thumb.jpg")
            res = await client.download_media(user["thumb_id"], file_name=custom_path)
            if res and isinstance(res, str) and os.path.exists(res):
                return res
        except Exception as e:
            logger.warning(f"Error fetching user custom thumbnail: {e}")

    # 2. Tham URL thumbnail
    tham_url = (user.get("tham_url") if user else None) or Config.THAM_URL
    if tham_url:
        cached_thumb = os.path.join(target_dir, "tham_url.jpg")
        downloaded = await download_thumbnail_url(tham_url, cached_thumb)
        if downloaded and isinstance(downloaded, str) and os.path.exists(downloaded):
            return downloaded

    # 3. Screenshot extraction from video
    if video_path and os.path.exists(video_path):
        screen_thumb = await extract_frame_screenshot(video_path, target_dir, duration)
        if screen_thumb and isinstance(screen_thumb, str) and os.path.exists(screen_thumb):
            return screen_thumb

    return None
