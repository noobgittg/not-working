import os
import re
import time
import shutil
from urllib.parse import urlparse
from typing import Optional, Any, Tuple
from config import Config
from app.utils.font import to_smallcaps

DEVIL_MODE_ACTIVE: bool = False

def is_devil_mode_active() -> bool:
    """Returns True if developer / devil mode is currently enabled."""
    global DEVIL_MODE_ACTIVE
    return DEVIL_MODE_ACTIVE

def set_devil_mode(state: bool) -> bool:
    """Sets developer / devil mode state."""
    global DEVIL_MODE_ACTIVE
    DEVIL_MODE_ACTIVE = bool(state)
    return DEVIL_MODE_ACTIVE

def get_current_timestamp() -> float:
    """Safely returns current unix timestamp in seconds."""
    return float(time.time())

async def is_admin(*args, **kwargs) -> bool:
    """
    Reusable admin-check function verifying if user_id is in ADMINS.
    Supports both is_admin(user_id: int) and is_admin(client, user_id: int).
    Returns True if user is an administrator or owner, False otherwise.
    """
    user_id = kwargs.get("user_id")
    if user_id is None and args:
        user_id = args[-1]
    if not user_id:
        return False
    try:
        return int(user_id) in Config.ADMINS
    except (ValueError, TypeError):
        return False

async def check_admin(client: Any, message: Any) -> bool:
    """
    Reusable admin gatekeeper for command handlers.
    Returns True if user is admin; otherwise sends safe rejection message and returns False.
    """
    user_id = message.from_user.id if message.from_user else 0
    if not await is_admin(client, user_id):
        await message.reply_text(
            f"🚫 **{to_smallcaps('ACCESS DENIED!')}**\n\n"
            f"{to_smallcaps('This command is restricted to Bot Administrators only.')}\n\n"
            f"⚡ **{to_smallcaps('POWERED BY')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
        )
        return False
    return True

def humanbytes(size: Optional[int]) -> str:
    """Formats byte counts into human-readable strings (B, KB, MB, GB, TB)."""
    if not size or size <= 0:
        return "0 B"
    num_size = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_size < 1024.0:
            break
        num_size /= 1024.0
    return f"{num_size:.2f} {unit}"

def time_formatter(milliseconds: int = 0, seconds: Optional[int] = None) -> str:
    """
    Formats duration given in either milliseconds or seconds into a human-readable string.
    Supports both positional and keyword calls safely.
    Examples: '1d 2h 30m 15s', '45s', '0s'.
    """
    if seconds is not None:
        total_seconds = int(seconds)
    elif milliseconds:
        total_seconds = int(milliseconds / 1000)
    else:
        total_seconds = 0

    if total_seconds < 0:
        total_seconds = 0

    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    res = ""
    if days > 0:
        res += f"{days}d "
    if hours > 0:
        res += f"{hours}h "
    if minutes > 0:
        res += f"{minutes}m "
    res += f"{secs}s"
    return res.strip() or "0s"

def is_valid_url(url: str) -> bool:
    """Checks if a string is a valid HTTP or HTTPS URL."""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False

def sanitize_filename(name: str) -> str:
    """Sanitizes filename removing illegal characters and path traversal patterns."""
    if not name:
        return "file.mp4"
    name = os.path.basename(name)
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f\x7f]', "_", str(name))
    cleaned = cleaned.strip(". ")
    return cleaned or "file.mp4"

def clean_temp_files(*files):
    """
    Safely cleans up temporary files or directories from disk.
    Handles nested lists, tuples, or non-existent files gracefully.
    """
    for f in files:
        if isinstance(f, (list, tuple, set)):
            for sub_f in f:
                clean_temp_files(sub_f)
            continue
        if f and isinstance(f, (str, bytes, os.PathLike)):
            try:
                if os.path.exists(f):
                    if os.path.isdir(f):
                        shutil.rmtree(f, ignore_errors=True)
                    else:
                        os.remove(f)
            except Exception:
                pass
