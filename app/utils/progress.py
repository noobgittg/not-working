import math
import time as time_module

from .font import to_smallcaps, format_watermark
from .helpers import humanbytes, time_formatter


async def progress_for_pyrogram(
    current: int,
    total: int,
    ud_type: str,
    message,
    start_time: float,
):
    """Pyrogram/Pyrofork progress callback with clock-collision and flood protection."""
    now = time_module.monotonic()
    start = float(start_time) if isinstance(start_time, (int, float)) else now
    diff = max(0.001, now - start)

    last_update = getattr(message, "_mmw_progress_time", 0.0)
    if current != total and now - last_update < 2.5:
        return
    try:
        message._mmw_progress_time = now
    except Exception:
        pass

    percentage = (current * 100 / total) if total > 0 else 0.0
    speed = current / diff
    eta_ms = int(((total - current) / speed) * 1000) if speed > 0 else 0
    elapsed_ms = int(diff * 1000)

    filled = min(10, max(0, math.floor(percentage / 10)))
    progress_bar = "▰" * filled + "▱" * (10 - filled)
    emoji = "📥" if "down" in ud_type.lower() else "📤"

    text = (
        f"{emoji} **{to_smallcaps(ud_type)}**...\n\n"
        f"[{progress_bar}] `{percentage:.1f}%`\n\n"
        f"• 📦 **{to_smallcaps('ᴘʀᴏᴄᴇssᴇᴅ')}** : `{humanbytes(current)}` / `{humanbytes(total)}`\n"
        f"• 🚀 **{to_smallcaps('sᴘᴇᴇᴅ')}** : `{humanbytes(speed)}/s`\n"
        f"• ⏳ **{to_smallcaps('ᴇᴛᴀ')}** : `{time_formatter(milliseconds=eta_ms)}`\n"
        f"• ⏱️ **{to_smallcaps('ᴇʟᴀᴘsᴇᴅ')}** : `{time_formatter(milliseconds=elapsed_ms)}`"
        f"{format_watermark()}"
    )
    try:
        await message.edit_text(text=text)
    except Exception:
        pass
