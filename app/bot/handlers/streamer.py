import secrets
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.database.repositories.file_repo import file_repo
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter

@Client.on_message(filters.private & filters.command("stream"))
async def stream_command_entry(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ғɪʟᴇ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀ sᴛʀᴇᴀᴍ ʟɪɴᴋ.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇᴅɪᴀ ᴡɪᴛʜ')} `/stream`"
            f"{format_watermark()}"
        )
    await generate_stream_response(client, message.reply_to_message, message)

@Client.on_callback_query(filters.regex(r"^stream_(\d+)"))
async def stream_callback_entry(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await generate_stream_response(client, original, query.message)

async def generate_stream_response(client: Client, media_msg: Message, target_reply: Message):
    status = await target_reply.reply_text(f"⚡ **{to_smallcaps('ɢᴇɴᴇʀᴀᴛɪɴɢ sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍ ʟɪɴᴋ...')}**")

    bin_chan = Config.BIN_CHANNEL if Config.BIN_CHANNEL != 0 else media_msg.chat.id
    try:
        log_msg = await media_msg.forward(bin_chan)
    except Exception:
        log_msg = media_msg

    media = media_msg.document or media_msg.video or media_msg.audio
    file_name = getattr(media, "file_name", None) or "stream_media.mp4"
    file_size = media.file_size
    mime_type = getattr(media, "mime_type", "video/mp4")
    duration = time_formatter(seconds=getattr(media, "duration", 0)) if getattr(media, "duration", 0) > 0 else "N/A"

    file_id = secrets.token_urlsafe(12)
    await file_repo.save_file(
        file_id=file_id,
        chat_id=log_msg.chat.id,
        message_id=log_msg.id,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type
    )

    watch_url = f"{Config.BASE_URL}/watch/{file_id}"
    stream_url = f"{Config.BASE_URL}/stream/{file_id}"
    download_url = f"{Config.BASE_URL}/download/{file_id}"

    text = (
        f"✦ **{to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍ ʟɪɴᴋ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(file_size)}`\n"
        f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{duration}`\n\n"
        f"🔗 **{to_smallcaps('ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ (ᴘʟʏʀ ᴠ𝟹)')}** :\n{watch_url}\n\n"
        f"⬇️ **{to_smallcaps('ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ')}** :\n{download_url}\n\n"
        f"💡 {to_smallcaps('ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ ɪɴ-ʙʀᴏᴡsᴇʀ ᴏʀ ʟᴀᴜɴᴄʜ ᴅɪʀᴇᴄᴛʟʏ ɪɴ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ ᴍᴇᴅɪᴀ ᴘʟᴀʏᴇʀ:')}"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"🎬 {to_smallcaps('ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ')}", url=watch_url),
            InlineKeyboardButton(f"⬇️ {to_smallcaps('ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ')}", url=download_url)
        ],
        [
            InlineKeyboardButton(f"▶️ ᴍx ᴘʟᴀʏᴇʀ", url=f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;type=video/*;end"),
            InlineKeyboardButton(f"▶️ ᴠʟᴄ ᴘʟᴀʏᴇʀ", url=f"intent:{stream_url}#Intent;package=org.videolan.vlc;type=video/*;end")
        ],
        [
            InlineKeyboardButton(f"▶️ ᴘʟᴀʏɪᴛ", url=f"playit://playvp/video?url={stream_url}"),
            InlineKeyboardButton(f"▶️ ᴋᴍᴘʟᴀʏᴇʀ", url=f"kmplayer://{stream_url}")
        ],
        [
            InlineKeyboardButton(f"📢 {to_smallcaps('ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ')}", url=Config.WATERMARK_URL),
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")
        ]
    ]

    await status.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
