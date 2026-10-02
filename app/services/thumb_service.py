import os
import aiohttp
import aiofiles
from typing import Optional, Any
from pyrogram import Client
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.logger import logger
from app.utils.helpers import is_valid_url
from .ffmpeg_service import extract_frame_screenshot

GLOBAL_THUMB_CACHE = os.path.join(Config.DOWNLOAD_DIR, "global_tham_cache.jpg")

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
    temp_dir_or_thumb_id: Any = None,
    video_path: Optional[str] = None,
    duration: int = 0
) -> Optional[str]:
    """
    Resolves thumbnail prioritizing:
    1. User custom thumbnail (from Telegram)
    2. User custom tham_url or Config.THAM_URL
    3. Video frame screenshot extraction via FFmpeg
    """
    # Resolve directory for storing temp thumbnail
    if isinstance(temp_dir_or_thumb_id, str) and os.path.isdir(temp_dir_or_thumb_id):
        temp_dir = temp_dir_or_thumb_id
    elif video_path and os.path.exists(video_path):
        temp_dir = os.path.dirname(video_path)
    else:
        temp_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
    os.makedirs(temp_dir, exist_ok=True)

    user = await user_repo.get_user(user_id)
    thumb_id = None
    if user and user.get("thumb_id"):
        thumb_id = user["thumb_id"]
    elif isinstance(temp_dir_or_thumb_id, str) and not os.path.isdir(temp_dir_or_thumb_id):
        thumb_id = temp_dir_or_thumb_id

    if thumb_id:
        try:
            custom_path = os.path.join(temp_dir, "custom_thumb.jpg")
            return await client.download_media(thumb_id, file_name=custom_path)
        except Exception as e:
            logger.warning(f"Error fetching user custom thumbnail: {e}")

    user_tham = user.get("tham_url") if user else None
    if user_tham:
        user_thumb_path = os.path.join(temp_dir, "user_tham.jpg")
        downloaded = await download_thumbnail_url(user_tham, user_thumb_path)
        if downloaded and os.path.exists(downloaded):
            return downloaded

    if Config.THAM_URL:
        if os.path.exists(GLOBAL_THUMB_CACHE) and os.path.getsize(GLOBAL_THUMB_CACHE) > 0:
            return GLOBAL_THUMB_CACHE
        downloaded = await download_thumbnail_url(Config.THAM_URL, GLOBAL_THUMB_CACHE)
        if downloaded and os.path.exists(downloaded):
            return downloaded

    if video_path and os.path.exists(video_path):
        return await extract_frame_screenshot(video_path, temp_dir, duration)

    return None
