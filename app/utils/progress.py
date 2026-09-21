import math
import time
from typing import Dict, Tuple

from .font import to_smallcaps, format_watermark
from .helpers import humanbytes, time_formatter

_LAST_EDIT: Dict[Tuple[int, int], float] = {}
_MIN_EDIT_INTERVAL = 4.0


async def progress_for_pyrogram(current: int, total: int, ud_type: str, message, start_time: float):
    now = time.monotonic()
    key = (getattr(getattr(message, "chat", None), "id", 0), getattr(message, "id", 0))
    last = _LAST_EDIT.get(key, 0.0)
    if current != total and now - last < _MIN_EDIT_INTERVAL:
        return
    if current != total and current <= 0:
        return

    _LAST_EDIT[key] = now
    elapsed = max(0.001, time.time() - start_time)
    percentage = (current * 100 / total) if total > 0 else 0.0
    speed = current / elapsed
    remaining_ms = int(((total - current) / speed) * 1000) if speed > 0 and total > current else 0
    filled = max(0, min(10, math.floor(percentage / 10)))
    bar = "▰" * filled + "▱" * (10 - filled)
    emoji = "📥" if "down" in ud_type.lower() else "📤"
    text = (
        f"⚡ **{to_smallcaps(f'{emoji} {ud_type}')}**\n\n"
        f"[{bar}] `{percentage:.1f}%`\n\n"
        f"• 📦 **{to_smallcaps('ᴘʀᴏᴄᴇssᴇᴅ')}** : `{humanbytes(current)}` / `{humanbytes(total)}`\n"
        f"• 🚀 **{to_smallcaps('sᴘᴇᴇᴅ')}** : `{humanbytes(speed)}/s`\n"
        f"• ⏳ **{to_smallcaps('ᴇᴛᴀ')}** : `{time_formatter(milliseconds=remaining_ms)}`\n"
        f"• ⏱️ **{to_smallcaps('ᴇʟᴀᴘsᴇᴅ')}** : `{time_formatter(seconds=int(elapsed))}`"
        f"{format_watermark()}"
    )
    try:
        await message.edit_text(text)
    except Exception:
        pass

    if current >= total:
        _LAST_EDIT.pop(key, None)
