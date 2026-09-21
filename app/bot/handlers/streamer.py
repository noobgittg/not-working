import secrets

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.repositories.file_repo import file_repo
from app.utils.font import format_watermark, to_smallcaps
from app.utils.helpers import humanbytes, is_telegram_button_url, time_formatter
from config import Config


def _button(label: str, url: str):
    return InlineKeyboardButton(label, url=url) if is_telegram_button_url(url) else None


@Client.on_message(filters.private & filters.command("stream"))
async def stream_command_entry(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ғɪʟᴇ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀ sᴛʀᴇᴀᴍ ʟɪɴᴋ.')}**\n"
            f"`/stream`{format_watermark()}"
        )
    await generate_stream_response(client, message.reply_to_message, message)


@Client.on_callback_query(filters.regex(r"^stream_(\d+)$"))
async def stream_callback_entry(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await query.answer()
    await generate_stream_response(client, original, query.message)


async def generate_stream_response(client: Client, media_msg: Message, target_reply: Message):
    status = await target_reply.reply_text(f"⚡ **{to_smallcaps('ɢᴇɴᴇʀᴀᴛɪɴɢ sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍ ʟɪɴᴋ...')}**")
    bin_chan = Config.BIN_CHANNEL if Config.BIN_CHANNEL else media_msg.chat.id
    try:
        log_msg = await media_msg.forward(bin_chan)
    except Exception:
        log_msg = media_msg

    media = media_msg.document or media_msg.video or media_msg.audio
    if not media:
        return await status.edit_text(f"❌ {to_smallcaps('sᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ.')}")
    file_name = getattr(media, "file_name", None) or "stream_media.bin"
    file_size = int(getattr(media, "file_size", 0) or 0)
    mime_type = getattr(media, "mime_type", None) or "application/octet-stream"
    duration = time_formatter(seconds=getattr(media, "duration", 0) or 0) if getattr(media, "duration", 0) else "N/A"
    file_id = secrets.token_urlsafe(12)
    await file_repo.save_file(
        file_id=file_id, chat_id=log_msg.chat.id, message_id=log_msg.id,
        file_name=file_name, file_size=file_size, mime_type=mime_type,
    )

    base = Config.BASE_URL.rstrip("/")
    watch_url = f"{base}/watch/{file_id}"
    stream_url = f"{base}/stream/{file_id}"
    download_url = f"{base}/file/{file_id}"
    valid_watch = is_telegram_button_url(watch_url)
    valid_stream = is_telegram_button_url(stream_url)
    valid_download = is_telegram_button_url(download_url)

    link_text = []
    if valid_watch:
        link_text.append(f"🔗 **{to_smallcaps('ᴡᴀᴛᴄʜ')}** : `{watch_url}`")
    if valid_stream:
        link_text.append(f"▶️ **{to_smallcaps('sᴛʀᴇᴀᴍ')}** : `{stream_url}`")
    if valid_download:
        link_text.append(f"⬇️ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ')}** : `{download_url}`")
    if not link_text:
        link_text.append(
            f"⚠️ {to_smallcaps('ʙᴀsᴇ_ᴜʀʟ ɪs ɴᴏᴛ ᴀ ᴛᴇʟᴇɢʀᴀᴍ-ᴠᴀʟɪᴅ ᴘᴜʙʟɪᴄ ʜᴛᴛᴘ(s) ᴜʀʟ. sᴇᴛ ʙᴀsᴇ_ᴜʀʟ ᴛᴏ ᴀ ᴘᴜʙʟɪᴄ ʜᴛᴛᴘs ᴅᴏᴍᴀɪɴ.') }"
        )

    buttons = []
    first = [b for b in (_button(f"🎬 {to_smallcaps('ᴡᴀᴛᴄʜ')}", watch_url), _button(f"⬇️ {to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ')}", download_url)) if b]
    if first:
        buttons.append(first)
    second = [b for b in (_button(f"▶️ {to_smallcaps('ᴏᴘᴇɴ sᴛʀᴇᴀᴍ ᴜʀʟ')}", stream_url),) if b]
    if second:
        buttons.append(second)
    if is_telegram_button_url(Config.WATERMARK_URL):
        buttons.append([InlineKeyboardButton(f"📢 {to_smallcaps('ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ')}", url=Config.WATERMARK_URL)])
    buttons.append([InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")])

    text = (
        f"✦ **{to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍ ʟɪɴᴋ')}** ✦\n\n"
        f"• 📁 `{file_name}`\n• 📦 `{humanbytes(file_size)}`\n• 🏷️ `{mime_type}`\n• ⏱️ `{duration}`\n\n"
        + "\n".join(link_text) + "\n\n"
        f"💡 {to_smallcaps('ᴜsᴇ ᴛʜᴇ sᴛʀᴇᴀᴍ ᴜʀʟ ᴡɪᴛʜ ᴠʟᴄ, ᴍx ᴘʟᴀʏᴇʀ ᴏʀ ᴀɴʏ ᴘʟᴀʏᴇʀ ᴛʜᴀᴛ sᴜᴘᴘᴏʀᴛs ʜᴛᴛᴘ ʀᴀɴɢᴇ ʀᴇǫᴜᴇsᴛs.') }{format_watermark()}"
    )
    await status.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
