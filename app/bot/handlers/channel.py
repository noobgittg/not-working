import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from app.database.repositories.chat_repo import chat_repo
from app.utils.font import to_smallcaps
from app.utils.helpers import humanbytes, time_formatter
from app.services.caption_service import format_caption
from app.services.autodel_service import schedule_deletion

@Client.on_message(filters.channel & (filters.document | filters.video))
async def channel_media_listener(client: Client, message: Message):
    media = message.video or message.document
    if not media:
        return

    chat_doc = await chat_repo.get_or_create_chat(message.chat.id, message.chat.title or "Channel", "channel")

    filename = media.file_name or "file.mp4"
    file_size_str = humanbytes(media.file_size)
    duration = getattr(media, "duration", 0)
    duration_str = time_formatter(duration * 1000) if duration else "0s"
    _, ext = os.path.splitext(filename)

    curr_caption = message.caption or ""
    if Config.WATERMARK not in curr_caption:
        new_caption = await format_caption(message.chat.id, filename, file_size_str, duration_str, ext)
        try:
            await message.edit_caption(caption=new_caption)
        except Exception:
            pass

    auto_del = chat_doc.get("auto_delete_time", 0)
    if auto_del > 0:
        await schedule_deletion(message.chat.id, message.id, auto_del)
