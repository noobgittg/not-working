import os

from pyrogram import Client, filters
from pyrogram.types import Message

from app.database.repositories.chat_repo import chat_repo
from app.services.autodel_service import schedule_deletion
from app.services.caption_service import render_caption_template
from app.utils.font import to_smallcaps
from app.utils.helpers import humanbytes, time_formatter
from config import Config


@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def channel_media_listener(client: Client, message: Message):
    media = message.video or message.document or message.audio
    if not media:
        return
    chat_doc = await chat_repo.get_or_create_chat(message.chat.id, message.chat.title or "Channel", "channel")
    filename = getattr(media, "file_name", None) or "media.bin"
    file_size_str = humanbytes(getattr(media, "file_size", 0))
    duration = getattr(media, "duration", 0) or 0
    duration_str = time_formatter(seconds=duration)
    _, ext = os.path.splitext(filename)
    current_caption = message.caption or ""

    if Config.WATERMARK not in current_caption:
        template = chat_doc.get("auto_caption")
        if template:
            new_caption = render_caption_template(
                template,
                file_name=filename,
                file_size_str=file_size_str,
                duration_str=duration_str,
                ext=ext.lstrip("."),
                file_caption=current_caption,
            )
        else:
            new_caption = current_caption + ("\n\n" if current_caption else "") + Config.WATERMARK
        try:
            await message.edit_caption(caption=new_caption)
        except Exception:
            pass

    auto_del = int(chat_doc.get("auto_delete_time", 0) or 0)
    if auto_del > 0:
        await schedule_deletion(message.chat.id, message.id, auto_del)
