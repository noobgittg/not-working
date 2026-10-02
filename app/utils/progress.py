import time
import math
from typing import Any, Optional
from config import Config
from app.utils.font import to_smallcaps
from app.utils.helpers import humanbytes, time_formatter

async def progress_for_pyrogram(
    current: int,
    total: int,
    ud_type: str,
    message: Any,
    start_time: Any = None
):
    """
    Real-time progress callback for Pyrogram upload / download with throttle and safe speed calculation.
    Defensively handles any start_time type (float, int, callable, or missing) without attribute errors.
    """
    now_ts = float(time.time())

    # Safely resolve start_time
    if callable(start_time):
        try:
            start_ts = float(start_time())
        except Exception:
            start_ts = now_ts
    elif isinstance(start_time, (int, float)):
        start_ts = float(start_time)
    else:
        start_ts = now_ts

    diff = max(0.001, now_ts - start_ts)
    if round(diff % 4.00) == 0 or current == total:
        percentage = (current * 100 / total) if total > 0 else 0
        speed = (current / diff) if diff > 0 else 0
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0

        filled_blocks = min(10, max(0, math.floor(percentage / 10)))
        progress = "[{0}{1}] `{2}%`\n".format(
            "".join(["▰" for _ in range(filled_blocks)]),
            "".join(["▱" for _ in range(10 - filled_blocks)]),
            round(percentage, 2)
        )

        tmp = (
            f"⚡ **{to_smallcaps(ud_type)}**...\n\n"
            f"{progress}"
            f"🚀 **{to_smallcaps('SPEED')}** : `{humanbytes(speed)}/s`\n"
            f"📦 **{to_smallcaps('DONE')}** : `{humanbytes(current)} / {humanbytes(total)}`\n"
            f"⏳ **{to_smallcaps('ETA')}** : `{time_formatter(milliseconds=time_to_completion)}`\n\n"
            f"⚡ **{to_smallcaps('POWERED BY')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
        )
        try:
            await message.edit_text(text=tmp)
        except Exception:
            pass
