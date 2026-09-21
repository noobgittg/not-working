import time
import math
from .font import to_smallcaps, format_watermark
from .helpers import humanbytes, time_formatter
from config import Config

async def progress_for_pyrogram(
    current: int,
    total: int,
    ud_type: str,
    message,
    start_time: float
):
    now = time.time()
    diff = now - start_time
    if round(diff % 3.00) == 0 or current == total:
        percentage = (current * 100 / total) if total > 0 else 0
        speed = current / diff if diff > 0 else 0
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        elapsed_time = round(diff) * 1000

        filled_blocks = math.floor(percentage / 10)
        empty_blocks = 10 - filled_blocks
        progress_bar = "".join(["▰" for _ in range(filled_blocks)]) + "".join(["▱" for _ in range(empty_blocks)])

        emoji = "📥" if "down" in ud_type.lower() else "📤"

        tmp = (
            f"⚡ **{to_smallcaps(ud_type)}**...\n\n"
            f"[{progress_bar}] `{round(percentage, 2)}%`\n\n"
            f"• 📦 **{to_smallcaps('ᴘʀᴏᴄᴇssᴇᴅ')}** : `{humanbytes(current)}` / `{humanbytes(total)}`\n"
            f"• 🚀 **{to_smallcaps('sᴘᴇᴇᴅ')}** : `{humanbytes(speed)}/s`\n"
            f"• ⏳ **{to_smallcaps('ᴇᴛᴀ')}** : `{time_formatter(milliseconds=time_to_completion)}`\n"
            f"• ⏱️ **{to_smallcaps('ᴇʟᴀᴘsᴇᴅ')}** : `{time_formatter(milliseconds=elapsed_time)}`"
            f"{format_watermark()}"
        )
        try:
            await message.edit_text(text=tmp)
        except Exception:
            pass
