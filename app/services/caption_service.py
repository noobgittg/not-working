from datetime import datetime, timezone

from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import format_watermark

DEFAULT_CAPTION = (
    "📁 **{filename}**\n\n"
    "• 📦 **sɪᴢᴇ** : `{filesize}`\n"
    "• ⏱️ **ᴅᴜʀᴀᴛɪᴏɴ** : `{duration}`\n"
    "• 🏷️ **ᴛʏᴘᴇ** : `{ext}`"
)


def render_caption_template(
    template: str,
    *,
    file_name: str,
    file_size_str: str,
    duration_str: str = "0s",
    ext: str = "",
    file_caption: str = "",
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
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
            date=now_str,
        )
    except Exception:
        caption = template
    if Config.WATERMARK not in caption:
        caption += format_watermark()
    return caption


async def format_caption(
    user_id: int,
    file_name: str,
    file_size_str: str,
    duration_str: str = "0s",
    ext: str = "",
    file_caption: str = "",
) -> str:
    user = await user_repo.get_user(user_id)
    user_custom = user.get("custom_caption") if user else None
    user_caps_list = user.get("captions_list", []) if user else []
    template = user_custom or (user_caps_list[0] if user_caps_list else None) or file_caption or DEFAULT_CAPTION
    return render_caption_template(
        template,
        file_name=file_name,
        file_size_str=file_size_str,
        duration_str=duration_str,
        ext=ext,
        file_caption=file_caption,
    )
