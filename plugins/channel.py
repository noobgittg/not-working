import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from plugins.core_db import chat_repo
from plugins.core_utils import to_smallcaps, format_watermark, humanbytes, time_formatter
from plugins.core_services import format_caption, schedule_deletion

@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def channel_media_listener(client: Client, message: Message):
    media = message.video or message.document or message.audio
    if not media:
        return

    chat_doc = await chat_repo.get_or_create_chat(message.chat.id, message.chat.title or "Channel", "channel")
    if not chat_doc.get("auto_caption", True):
        return

    filename = getattr(media, "file_name", None) or "file.mp4"
    file_size_str = humanbytes(getattr(media, "file_size", 0))
    duration = getattr(media, "duration", 0)
    duration_str = time_formatter(seconds=duration) if duration else "0s"
    _, ext = os.path.splitext(filename)
    ext = ext.replace(".", "")

    curr_caption = message.caption or ""
    if Config.WATERMARK not in curr_caption:
        new_caption = await format_caption(
            user_or_id=message.chat.id,
            file_name=filename,
            file_size_str=file_size_str,
            duration_str=duration_str,
            ext=ext,
            file_caption=curr_caption,
            file_id=str(message.id)
        )
        try:
            await message.edit_caption(caption=new_caption)
        except Exception:
            pass

    auto_del = chat_doc.get("auto_delete_time", 0)
    if auto_del > 0:
        await schedule_deletion(message.chat.id, message.id, auto_del)
