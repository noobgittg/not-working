import datetime
from typing import Optional
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark

DEFAULT_CAPTION = (
    "📁 **{filename}**\n\n"
    "• 📦 **sɪᴢᴇ** : `{filesize}`\n"
    "• ⏱️ **ᴅᴜʀᴀᴛɪᴏɴ** : `{duration}`\n"
    "• 🏷️ **ᴛʏᴘᴇ** : `{ext}`"
)

async def format_caption(
    user_id: int,
    file_name: str,
    file_size_str: str,
    duration_str: str = "0s",
    ext: str = "",
    file_caption: str = ""
) -> str:
    """
    Dynamically format caption based on:
    cap = user_custom_caption or file_caption or cap[] or DEFAULT_CAPTION
    """
    user = await user_repo.get_user(user_id)
    user_custom = user.get("custom_caption") if user else None
    user_caps_list = user.get("captions_list", []) if user else []

    # Dynamic fallback:
    # 1. User set custom caption template
    # 2. First template from user's dynamic caption list cap[]
    # 3. Original file caption from media
    # 4. Global default template
    template = user_custom
    if not template and user_caps_list:
        template = user_caps_list[0]
    if not template and file_caption:
        template = file_caption
    if not template:
        template = DEFAULT_CAPTION

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    try:
        caption = template.format(
            filename=file_name,
            filesize=file_size_str,
            duration=duration_str,
            ext=ext,
            original_caption=file_caption,
            caption=file_caption,
            file_caption=file_caption,
            watermark=Config.WATERMARK,
            watermark_url=Config.WATERMARK_URL,
            date=now_str
        )
    except Exception:
        caption = template

    if Config.WATERMARK not in caption:
        caption += format_watermark()

    return caption
