import time
import asyncio
import logging
import sys
import os
import re
import math
import shutil
import uuid
from collections import OrderedDict
from urllib.parse import urlparse
from typing import Any, Optional, Dict, List, Tuple
from config import Config
try:
    from pyrogram.errors import FloodWait, MessageNotModified
except ImportError:
    FloodWait = type("FloodWait", (Exception,), {})
    MessageNotModified = type("MessageNotModified", (Exception,), {})

# ==================== 1. SMALLCAPS STYLISH FONT & EMOJIS ====================

SMALLCAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺',
    '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'
}

ALPHA_SMALLCAPS_MAP = {k: v for k, v in SMALLCAPS_MAP.items() if k.isalpha()}

def to_smallcaps(text: str, convert_digits: bool = False) -> str:
    """Converts text into clean smallcap stylish font while preserving URLs, @mentions, and /commands."""
    if not text:
        return ""
    cmap = SMALLCAPS_MAP if convert_digits else ALPHA_SMALLCAPS_MAP
    tokens = re.split(r'(https?://\S+|@\w+|/[a-zA-Z0-9_]+|\{[a-zA-Z0-9_]+\})', str(text))
    out = []
    for idx, tok in enumerate(tokens):
        if idx % 2 == 1:
            out.append(tok)
        else:
            out.append("".join(cmap.get(c, c) for c in tok))
    return "".join(out)

def sc(text: str) -> str:
    """Short alias for to_smallcaps."""
    return to_smallcaps(text)

def style_text(header: str, items: dict = None) -> str:
    out = f"✦ **{to_smallcaps(header)}** ✦\n\n"
    if items:
        for k, v in items.items():
            out += f"• **{to_smallcaps(k)}** : `{v}`\n"
        out += "\n"
    out += f"⚡ **{to_smallcaps('powered by')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
    return out

def format_watermark() -> str:
    return f"\n\n📢 **{to_smallcaps('join')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"


# ==================== 2. LOGGER ====================

MEMORY_LOGS: List[str] = []

class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            MEMORY_LOGS.append(msg)
            if len(MEMORY_LOGS) > 150:
                MEMORY_LOGS.pop(0)
        except Exception:
            pass

def setup_logger(name: str = "MMW_PRO") -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)

        mem_handler = MemoryLogHandler()
        mem_handler.setFormatter(formatter)
        log.addHandler(mem_handler)
    return log

logger = setup_logger()

_TELEGRAM_WRITE_BLOCK_UNTIL = 0.0


def _flood_wait_seconds(error: Exception) -> int:
    try:
        return max(1, int(getattr(error, "value", 1)))
    except (TypeError, ValueError):
        return 1


async def safe_edit_text(message: Any, text: str, **kwargs: Any) -> Any:
    """Best-effort status edit; never lets FloodWait abort a media job."""
    global _TELEGRAM_WRITE_BLOCK_UNTIL
    if message is None:
        return None
    now = time.time()
    if now < _TELEGRAM_WRITE_BLOCK_UNTIL:
        return message
    try:
        return await message.edit_text(text=text, **kwargs)
    except FloodWait as error:
        wait_for = _flood_wait_seconds(error)
        _TELEGRAM_WRITE_BLOCK_UNTIL = max(_TELEGRAM_WRITE_BLOCK_UNTIL, now + wait_for)
        logger.warning(f"Telegram write cooldown active for {wait_for}s; skipping optional status edits")
        return message
    except MessageNotModified:
        return message
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.debug(f"Optional Telegram status edit skipped: {error}")
        return message


async def safe_reply_text(target: Any, text: str, **kwargs: Any) -> Any:
    """Best-effort status creation; a media job may continue without it."""
    global _TELEGRAM_WRITE_BLOCK_UNTIL
    if target is None:
        return None
    now = time.time()
    if now < _TELEGRAM_WRITE_BLOCK_UNTIL:
        return None
    try:
        return await target.reply_text(text, **kwargs)
    except FloodWait as error:
        wait_for = _flood_wait_seconds(error)
        _TELEGRAM_WRITE_BLOCK_UNTIL = max(_TELEGRAM_WRITE_BLOCK_UNTIL, now + wait_for)
        logger.warning(f"Telegram write cooldown active for {wait_for}s; continuing without a status message")
        return None
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.debug(f"Optional Telegram status creation skipped: {error}")
        return None


async def safe_send_message(client: Any, **kwargs: Any) -> Any:
    """Best-effort text send that never turns a FloodWait into a crash."""
    global _TELEGRAM_WRITE_BLOCK_UNTIL
    now = time.time()
    if now < _TELEGRAM_WRITE_BLOCK_UNTIL:
        return None
    try:
        return await client.send_message(**kwargs)
    except FloodWait as error:
        wait_for = _flood_wait_seconds(error)
        _TELEGRAM_WRITE_BLOCK_UNTIL = max(_TELEGRAM_WRITE_BLOCK_UNTIL, now + wait_for)
        logger.warning(f"Telegram write cooldown active for {wait_for}s; skipping optional message send")
        return None
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.debug(f"Optional Telegram message send skipped: {error}")
        return None


async def safe_forward_message(message: Any, chat_id: Any) -> Any:
    """Forward for indexing without delaying the main media workflow on FloodWait."""
    global _TELEGRAM_WRITE_BLOCK_UNTIL
    now = time.time()
    if now < _TELEGRAM_WRITE_BLOCK_UNTIL:
        return message
    try:
        return await message.forward(chat_id)
    except FloodWait as error:
        wait_for = _flood_wait_seconds(error)
        _TELEGRAM_WRITE_BLOCK_UNTIL = max(_TELEGRAM_WRITE_BLOCK_UNTIL, now + wait_for)
        logger.warning(f"Telegram forward cooldown active for {wait_for}s; indexing original message instead")
        return message
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.debug(f"Optional Telegram forward skipped: {error}")
        return message


async def safe_delete_messages(client: Any, chat_id: Any, message_ids: Any) -> bool:
    """Delete batches without turning rate limits into a tight retry loop."""
    global _TELEGRAM_WRITE_BLOCK_UNTIL
    now = time.time()
    if now < _TELEGRAM_WRITE_BLOCK_UNTIL:
        return False
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_ids)
        return True
    except FloodWait as error:
        wait_for = _flood_wait_seconds(error)
        _TELEGRAM_WRITE_BLOCK_UNTIL = max(_TELEGRAM_WRITE_BLOCK_UNTIL, now + wait_for)
        logger.warning(f"Telegram delete cooldown active for {wait_for}s; deferring auto-delete batch")
        return False
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.debug(f"Optional Telegram delete skipped: {error}")
        return False


# ==================== 3. ULTRA-FAST O(1) LRU TTL CACHE ====================

class FastMemoryCache:
    """
    High-performance bounded O(1) LRU + TTL in-memory caching engine.
    Eliminates duplicate DB roundtrips for user settings, chat configs, stream tokens, and file lookups.
    """
    def __init__(self, default_ttl: Optional[int] = None, max_entries: Optional[int] = None):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._expires: Dict[str, float] = {}
        self._default_ttl = default_ttl if default_ttl is not None else getattr(Config, "CACHE_TTL", 900)
        self._max_entries = max_entries if max_entries is not None else getattr(Config, "CACHE_MAX_ENTRIES", 5000)
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            curr_now = float(time.time())
            if curr_now > self._expires.get(key, 0):
                self._cache.pop(key, None)
                self._expires.pop(key, None)
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            curr_now = float(time.time())
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._max_entries:
                expired_keys = [k for k, exp in list(self._expires.items()) if curr_now > exp]
                for k in expired_keys:
                    self._cache.pop(k, None)
                    self._expires.pop(k, None)
                if len(self._cache) >= self._max_entries:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self._expires.pop(oldest_key, None)

            self._cache[key] = value
            effective_ttl = ttl if ttl is not None else self._default_ttl
            self._expires[key] = curr_now + float(effective_ttl)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            existed = key in self._cache
            self._cache.pop(key, None)
            self._expires.pop(key, None)
            return existed

    async def clear(self):
        async with self._lock:
            self._cache.clear()
            self._expires.clear()

    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100) if total_requests > 0 else 100.0
            return {
                "cached_keys": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio_percent": round(hit_ratio, 2)
            }

cache = FastMemoryCache()


# ==================== 4. HELPERS & AUTH ====================

DEVIL_MODE_ACTIVE: bool = False

def is_devil_mode_active() -> bool:
    return DEVIL_MODE_ACTIVE

def set_devil_mode(state: bool) -> bool:
    global DEVIL_MODE_ACTIVE
    DEVIL_MODE_ACTIVE = bool(state)
    return DEVIL_MODE_ACTIVE

def get_current_timestamp() -> float:
    return float(time.time())

async def is_admin(*args, **kwargs) -> bool:
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
    user_id = message.from_user.id if message.from_user else 0
    if not await is_admin(client, user_id):
        await message.reply_text(
            f"🚫 **{to_smallcaps('access denied!')}**\n\n"
            f"🔒 {to_smallcaps('this command is restricted to bot admins only.')}"
            f"{format_watermark()}"
        )
        return False
    return True

def humanbytes(size: Optional[int]) -> str:
    if not size or size <= 0:
        return "0 B"
    num_size = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_size < 1024.0:
            break
        num_size /= 1024.0
    return f"{num_size:.2f} {unit}"

def time_formatter(milliseconds: int = 0, seconds: Optional[int] = None) -> str:
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
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False

def sanitize_filename(name: str) -> str:
    if not name:
        return "file.mp4"
    name = os.path.basename(name)
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f\x7f]', "_", str(name))
    cleaned = cleaned.strip(". ")
    return cleaned or "file.mp4"

def clean_temp_files(*files):
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


# ==================== 5. PYROGRAM PROGRESS ====================

_PROGRESS_THROTTLE: Dict[int, float] = {}

async def progress_for_pyrogram(
    current: int,
    total: int,
    ud_type: str,
    message: Any,
    start_time: Any = None
):
    now_ts = get_current_timestamp()
    start_ts = now_ts
    if start_time is not None:
        if callable(start_time):
            try:
                val = start_time()
                if isinstance(val, (int, float)):
                    start_ts = float(val)
            except Exception:
                pass
        elif isinstance(start_time, (int, float)):
            start_ts = float(start_time)

    msg_key = getattr(message, "id", 0)
    last_edit = _PROGRESS_THROTTLE.get(msg_key, 0.0)
    if current >= total:
        # The caller immediately transitions to probing/compression/upload.
        # Do not race that transition with a final download edit at 100%.
        _PROGRESS_THROTTLE.pop(msg_key, None)
        return
    if (now_ts - last_edit) < 3.5:
        return
    _PROGRESS_THROTTLE[msg_key] = now_ts

    diff = max(0.001, now_ts - start_ts)
    percentage = (current * 100 / total) if total > 0 else 0
    speed = (current / diff) if diff > 0 else 0
    time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0

    filled_blocks = min(10, max(0, math.floor(percentage / 10)))
    progress = "[{0}{1}] `{2}%`\n".format(
        "".join(["▰" for _ in range(filled_blocks)]),
        "".join(["▱" for _ in range(10 - filled_blocks)]),
        round(percentage, 1)
    )

    tmp = (
        f"⚡ **{to_smallcaps(ud_type)}**...\n\n"
        f"{progress}"
        f"🚀 **{to_smallcaps('speed')}** : `{humanbytes(speed)}/s`\n"
        f"📦 **{to_smallcaps('done')}** : `{humanbytes(current)} / {humanbytes(total)}`\n"
        f"⏳ **{to_smallcaps('eta')}** : `{time_formatter(milliseconds=time_to_completion)}`"
        f"{format_watermark()}"
    )
    try:
        await safe_edit_text(message, tmp)
    except Exception:
        pass


# ==================== 6. TASK MANAGER ====================

class MediaTask:
    def __init__(
        self,
        task_id: str,
        user_id: int,
        task_type: str,
        work_dir: str,
        asyncio_task: Optional[asyncio.Task] = None,
        process: Optional[asyncio.subprocess.Process] = None,
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.work_dir = work_dir
        self.asyncio_task = asyncio_task
        self.process = process
        self.created_at = time.time()
        self.is_cancelled = False


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, MediaTask] = {}
        self._lock = asyncio.Lock()

    def generate_task_id(self, user_id: int) -> str:
        return f"{user_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    def create_workspace(self, user_id: int, task_id: str) -> str:
        work_dir = os.path.abspath(os.path.join(Config.DOWNLOAD_DIR, str(user_id), task_id))
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    async def register_task(
        self,
        task_id: str,
        user_id: int,
        task_type: str,
        work_dir: str,
        asyncio_task: Optional[asyncio.Task] = None,
    ) -> MediaTask:
        async with self._lock:
            media_task = MediaTask(
                task_id=task_id,
                user_id=user_id,
                task_type=task_type,
                work_dir=work_dir,
                asyncio_task=asyncio_task,
            )
            self._tasks[task_id] = media_task
            return media_task

    def set_subprocess(self, task_id: str, process: asyncio.subprocess.Process) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].process = process

    def get_task(self, task_id: str) -> Optional[MediaTask]:
        return self._tasks.get(task_id)

    def get_user_tasks(self, user_id: int) -> list:
        return [task for task in self._tasks.values() if task.user_id == user_id]

    def is_user_busy(self, user_id: int) -> bool:
        return False

    async def cancel_user_tasks(self, user_id: int) -> int:
        user_tasks = self.get_user_tasks(user_id)
        count = 0
        for t in user_tasks:
            if await self.cancel_task(t.task_id):
                count += 1
        return count

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.is_cancelled = True
            if task.process and task.process.returncode is None:
                try:
                    task.process.kill()
                except Exception:
                    pass
            if task.asyncio_task and not task.asyncio_task.done():
                task.asyncio_task.cancel()
            return True

    async def cleanup_task(self, task_id: str) -> None:
        async with self._lock:
            task = self._tasks.pop(task_id, None)
        if task and task.work_dir and os.path.exists(task.work_dir):
            try:
                shutil.rmtree(task.work_dir, ignore_errors=True)
            except Exception:
                pass

task_manager = TaskManager()
