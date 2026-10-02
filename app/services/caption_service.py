import os
import datetime
from typing import Optional, Dict, Any, Union
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import format_watermark
from app.utils.helpers import humanbytes, time_formatter

DEFAULT_CAPTION = (
    "📁 **{filename}**\n\n"
    "• 📦 **sɪᴢᴇ** : `{filesize}`\n"
    "• ⏱️ **ᴅᴜʀᴀᴛɪᴏɴ** : `{duration}`\n"
    "• 🌐 **ʟᴀɴɢᴜᴀɢᴇ** : `{language}`\n"
    "• 🎧 **ᴀᴜᴅɪᴏ** : `{audio_track}`\n"
    "• 🏷️ **ᴛʏᴘᴇ** : `{ext}`\n"
    "• 🆔 **ғɪʟᴇ ɪᴅ** : `{file_id}`"
)

async def format_caption(
    user_or_id: Union[int, Dict[str, Any], Any],
    file_name: str,
    file_size_str: Any = "0 B",
    duration_str: Any = "0s",
    ext: str = "",
    file_caption: str = "",
    language: str = "Undetermined",
    audio_track: str = "Default Audio",
    file_id: str = "",
    resolution: str = "N/A",
    video_codec: str = "N/A",
    audio_codec: str = "N/A",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Dynamically formats caption based on file metadata:
    File name, File size, Duration, Language, Audio track, Caption, File ID, etc.
    Guarantees strict safety truncation to under 1024 characters to prevent Telegram MediaCaptionTooLong errors.
    """
    user: Optional[Dict[str, Any]] = None
    if isinstance(user_or_id, dict):
        user = user_or_id
    elif isinstance(user_or_id, int):
        user = await user_repo.get_user(user_or_id)
    elif user_or_id is not None:
        uid = getattr(user_or_id, "id", None) or getattr(user_or_id, "user_id", None)
        if uid:
            user = await user_repo.get_user(int(uid))

    if isinstance(file_size_str, (int, float)):
        file_size_str = humanbytes(int(file_size_str))

    if isinstance(duration_str, (int, float)):
        duration_str = time_formatter(seconds=int(duration_str))

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

    # Extract deeper metadata if provided
    if metadata:
        if not language or language == "Undetermined":
            langs = [a.get("language") or a.get("lang") for a in metadata.get("audio_streams", []) if (a.get("language") or a.get("lang"))]
            if langs:
                language = ", ".join(sorted(set([str(l).title() for l in langs])))
        if not audio_track or audio_track == "Default Audio":
            auds = [f"{a.get('codec', '')} {a.get('channels', 2)}ch".strip() for a in metadata.get("audio_streams", [])]
            if auds:
                audio_track = ", ".join(auds)
        if not resolution or resolution == "N/A":
            v_streams = metadata.get("video_streams", [])
            if v_streams:
                resolution = f"{v_streams[0].get('width', 0)}x{v_streams[0].get('height', 0)}"
        if not video_codec or video_codec == "N/A":
            v_streams = metadata.get("video_streams", [])
            if v_streams:
                video_codec = v_streams[0].get("codec", "N/A")
        if not audio_codec or audio_codec == "N/A":
            a_streams = metadata.get("audio_streams", [])
            if a_streams:
                audio_codec = a_streams[0].get("codec", "N/A")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    time_str = now_utc.strftime("%H:%M:%S UTC")

    # Safe formatting dict mapping all user requested metadata tokens
    fmt_dict = {
        "filename": file_name,
        "file_name": file_name,
        "filesize": file_size_str,
        "file_size": file_size_str,
        "duration": duration_str,
        "language": language or "Undetermined",
        "languages": language or "Undetermined",
        "audio_track": audio_track or "Stereo 2.0",
        "autotrack": audio_track or "Stereo 2.0",
        "audio_tracks": audio_track or "Stereo 2.0",
        "caption": file_caption or "",
        "file_caption": file_caption or "",
        "original_caption": file_caption or "",
        "file_id": file_id or "N/A",
        "fileid": file_id or "N/A",
        "resolution": resolution or "N/A",
        "video_codec": video_codec or "N/A",
        "audio_codec": audio_codec or "N/A",
        "ext": ext,
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL,
        "date": now_str,
        "time": time_str,
        "current_time": time_str,
        "time_str": time_str
    }

    try:
        class SafeDict(dict):
            def __missing__(self, key):
                return f"{{{key}}}"
        caption = template.format_map(SafeDict(**fmt_dict))
    except Exception:
        caption = template

    if Config.WATERMARK not in caption:
        caption += format_watermark()

    # Telegram Bot API enforces a hard 1024-character limit on message captions
    if len(caption) > 1024:
        wm = format_watermark()
        avail = 1024 - len(wm) - 4
        caption = caption[:max(0, avail)] + "...\n" + wm

    return caption

async def extract_and_format_caption(
    user_id: int,
    file_path: str,
    original_caption: str = "",
    file_id: str = ""
) -> str:
    """
    Extracts complete technical metadata directly from the file via ffprobe
    and renders the formatted caption based on actual stream metadata.
    """
    from .ffmpeg_service import get_detailed_mediainfo

    file_name = os.path.basename(file_path)
    file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    file_size_str = humanbytes(file_size_bytes)
    ext = os.path.splitext(file_name)[1].replace(".", "").lower()

    metadata = await get_detailed_mediainfo(file_path)
    dur_sec = metadata.get("duration", 0)
    duration_str = time_formatter(seconds=dur_sec) if dur_sec > 0 else "0s"

    return await format_caption(
        user_or_id=user_id,
        file_name=file_name,
        file_size_str=file_size_str,
        duration_str=duration_str,
        ext=ext,
        file_caption=original_caption,
        file_id=file_id,
        metadata=metadata
    )
