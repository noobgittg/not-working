import os
import re
from urllib.parse import urlparse
from typing import Optional

def humanbytes(size: Optional[int]) -> str:
    """Formats a byte count into a human-readable size string (e.g. 12.50 MB)."""
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def time_formatter(milliseconds: int = 0, seconds: int = 0) -> str:
    """
    Formats a duration given in either milliseconds or seconds into a human-readable string:
    e.g. '1d 2h 30m 15s' or '45s'.
    Supports positional argument as milliseconds.
    """
    if seconds:
        total_seconds = int(seconds)
    elif milliseconds:
        total_seconds = int(milliseconds / 1000)
    else:
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
    """Validates whether a string is a well-formed http or https URL."""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False

def clean_temp_files(*files):
    """
    Safely cleans up temporary files or directories from disk.
    Handles nested lists or tuples gracefully to prevent PathLike TypeErrors.
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
                        import shutil
                        shutil.rmtree(f, ignore_errors=True)
                    else:
                        os.remove(f)
            except Exception:
                pass

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a file name by removing directory traversal patterns, illegal
    characters, and control characters to prevent filesystem security issues.
    """
    if not name:
        return "file.bin"
    name = os.path.basename(name)
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'[\x00-\x1f\x7f]', "", name)
    name = name.strip(" .")
    return name or "file.bin"
