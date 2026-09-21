import asyncio
import ipaddress
import os
import re
import socket
from urllib.parse import urlparse
from typing import Optional, Tuple, List


def humanbytes(size: Optional[int]) -> str:
    try:
        size = int(size or 0)
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        return "0 B"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024.0 or unit == "PB":
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def time_formatter(milliseconds: int = 0, seconds: int = 0) -> str:
    if seconds:
        total_seconds = int(seconds)
    elif milliseconds:
        total_seconds = int(milliseconds / 1000)
    else:
        total_seconds = 0
    minutes, secs = divmod(max(0, total_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    res = ""
    if days:
        res += f"{days}d "
    if hours:
        res += f"{hours}h "
    if minutes:
        res += f"{minutes}m "
    res += f"{secs}s"
    return res.strip() or "0s"


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse((url or "").strip())
        return result.scheme in {"http", "https"} and bool(result.hostname)
    except Exception:
        return False


def is_safe_public_url(url: str) -> bool:
    """Reject localhost/private/reserved targets to reduce thumbnail SSRF risk."""
    if not is_valid_url(url):
        return False
    try:
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain", "metadata.google.internal", "host.docker.internal"}:
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)
        except ValueError:
            pass
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in infos:
            addr = sockaddr[0]
            try:
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
            except ValueError:
                return False
        return True
    except Exception:
        return False


def is_telegram_button_url(url: str) -> bool:
    """Telegram-safe button URL: only public-looking HTTP(S) links are emitted."""
    if not is_valid_url(url):
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
        return host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    except Exception:
        return False


def clean_temp_files(*files):
    for f in files:
        if f and os.path.exists(f):
            try:
                if os.path.isdir(f):
                    import shutil
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    os.remove(f)
            except Exception:
                pass


def sanitize_filename(name: str) -> str:
    if not name:
        return "file.bin"
    name = os.path.basename(str(name).replace("\\", "/"))
    name = re.sub(r'[\x00-\x1f\x7f]', "", name)
    name = re.sub(r'[/:*?"<>|]+', "", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:255] or "file.bin"


def quote_filename_for_header(name: str) -> str:
    return sanitize_filename(name).replace('"', "'")


def preserve_extension(new_name: str, original_name: str) -> Tuple[str, str]:
    new_name = sanitize_filename(new_name)
    original_name = sanitize_filename(original_name or "file.bin")
    base, ext = os.path.splitext(new_name)
    original_ext = os.path.splitext(original_name)[1]
    if not base:
        base = os.path.splitext(original_name)[0] or "file"
    if not ext:
        ext = original_ext
    return sanitize_filename(base + ext), ext.lstrip(".").lower()


def split_file(path: str, output_dir: str, part_size: int) -> List[str]:
    """Split a large output into uploadable binary parts without loading it into RAM."""
    os.makedirs(output_dir, exist_ok=True)
    size = os.path.getsize(path)
    if size <= part_size:
        return [path]
    base = os.path.basename(path)
    parts: List[str] = []
    with open(path, "rb") as src:
        index = 1
        while True:
            chunk = src.read(part_size)
            if not chunk:
                break
            part_path = os.path.join(output_dir, f"{base}.part{index:03d}")
            with open(part_path, "wb") as dst:
                dst.write(chunk)
            parts.append(part_path)
            index += 1
    return parts


async def split_file_async(
    path: str,
    output_dir: Optional[str] = None,
    part_size: Optional[int] = None,
    *,
    max_bytes: Optional[int] = None,
) -> List[str]:
    target = max_bytes or part_size
    if not target or target <= 0:
        raise ValueError("part_size/max_bytes must be greater than zero")
    out_dir = output_dir or os.path.join(os.path.dirname(path), "parts")
    return await asyncio.to_thread(split_file, path, out_dir, int(target))
