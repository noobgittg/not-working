import math
from typing import Any
from config import Config
from app.utils.font import to_smallcaps
from app.utils.helpers import humanbytes, time_formatter, get_current_timestamp

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
    Completely eliminates 'builtin_function_or_method' object has no attribute 'time' by never calling .time on callables.
    """
    now_ts = get_current_timestamp()

    # Safely resolve start_time — never assume it has a .time attribute
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
        elif hasattr(start_time, "__float__"):
            try:
                start_ts = float(start_time)
            except Exception:
                pass

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
