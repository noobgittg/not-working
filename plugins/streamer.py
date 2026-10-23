import secrets
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from config import Config
from app.database.repositories.file_repo import file_repo
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter
from app.utils.logger import logger

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
    raw_name = getattr(media, "file_name", None) or "stream_media.mp4"
    file_name = raw_name.replace("`", "'")
    file_size = media.file_size
    mime_type = getattr(media, "mime_type", "video/mp4")
    duration_val = getattr(media, "duration", 0)
    duration = time_formatter(seconds=duration_val) if duration_val > 0 else "N/A"

    thumb_id = getattr(media.thumbs[0], "file_id", None) if getattr(media, "thumbs", None) else None
    metadata = {
        "duration": duration_val,
        "width": getattr(media, "width", 0),
        "height": getattr(media, "height", 0)
    }

    user_id = media_msg.from_user.id if media_msg.from_user else (target_reply.from_user.id if target_reply.from_user else 0)

    file_id = secrets.token_urlsafe(12)
    await file_repo.save_file(
        file_id=file_id,
        chat_id=log_msg.chat.id,
        message_id=log_msg.id,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        user_id=user_id,
        metadata=metadata,
        thumb_id=thumb_id
    )

    watch_url = f"{Config.BASE_URL}/watch/{file_id}"
    download_url = f"{Config.BASE_URL}/download/{file_id}"

    text = (
        f"✦ **{to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍ ʟɪɴᴋ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(file_size)}`\n"
        f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{duration}`\n"
        f"• 🆔 **{to_smallcaps('ғɪʟᴇ ɪᴅ')}** : `{file_id}`\n\n"
        f"🔗 **{to_smallcaps('ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ (𝟷𝟻 ᴘʟᴀʏᴇʀ ᴇɴɢɪɴᴇs)')}** :\n{watch_url}\n\n"
        f"⬇️ **{to_smallcaps('ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ')}** :\n{download_url}\n\n"
        f"💡 **{to_smallcaps('ғᴇᴀᴛᴜʀᴇs')}** :\n"
        f"• 📥 {to_smallcaps('ᴄʟɪᴄᴋ')} `[ɢᴇᴛ ғɪʟᴇ]` {to_smallcaps('ᴛᴏ ʀᴇᴛʀɪᴇᴠᴇ ᴛʜᴇ ғɪʟᴇ ᴅɪʀᴇᴄᴛʟʏ ɪɴ ᴛᴇʟᴇɢʀᴀᴍ.')}\n"
        f"• 🗑️ {to_smallcaps('ᴄʟɪᴄᴋ')} `[ʀᴇᴠᴏᴋᴇ]` {to_smallcaps('ᴛᴏ ᴅᴇʟᴇᴛᴇ/ᴅɪsᴀʙʟᴇ ᴛʜɪs sᴛʀᴇᴀᴍ ʟɪɴᴋ ᴀɴʏᴛɪᴍᴇ.')}"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"🎬 {to_smallcaps('ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ')}", url=watch_url),
            InlineKeyboardButton(f"⬇️ {to_smallcaps('ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ')}", url=download_url)
        ],
        [
            InlineKeyboardButton(f"📥 {to_smallcaps('ɢᴇᴛ ғɪʟᴇ')}", callback_data=f"getfile_{file_id}"),
            InlineKeyboardButton(f"🗑️ {to_smallcaps('ʀᴇᴠᴏᴋᴇ ʟɪɴᴋ')}", callback_data=f"revoke_{file_id}")
        ],
        [
            InlineKeyboardButton(f"📢 {to_smallcaps('ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ')}", url=Config.WATERMARK_URL),
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")
        ]
    ]

    await status.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# ==================== GET FILE FEATURE ====================

@Client.on_message(filters.private & filters.command(["getfile", "file"]))
async def get_file_command_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/getfile <file_id>`\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/getfile abc123xyz`\n\n"
            f"💡 {to_smallcaps('ʀᴇᴛʀɪᴇᴠᴇs ᴀɴᴅ sᴇɴᴅs ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ғɪʟᴇ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ʏᴏᴜ.')}"
            f"{format_watermark()}"
        )
    file_id = message.command[1].strip()
    await send_streamed_file_to_user(client, message.chat.id, file_id, message)

@Client.on_callback_query(filters.regex(r"^getfile_([a-zA-Z0-9_-]+)"))
async def get_file_callback_entry(client: Client, query: CallbackQuery):
    file_id = query.matches[0].group(1)
    await query.answer(to_smallcaps("sᴇɴᴅɪɴɢ ғɪʟᴇ ᴛᴏ ʏᴏᴜ..."))
    await send_streamed_file_to_user(client, query.message.chat.id, file_id, query.message)

async def send_streamed_file_to_user(client: Client, chat_id: int, file_id: str, reply_target: Message):
    file_doc = await file_repo.get_file(file_id)
    if not file_doc:
        return await reply_target.reply_text(
            f"❌ **{to_smallcaps('ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ sᴛʀᴇᴀᴍ ʟɪɴᴋ ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ!')}**\n\n"
            f"💡 {to_smallcaps('ᴛʜɪs sᴛʀᴇᴀᴍ ʟɪɴᴋ ᴍᴀʏ ʜᴀᴠᴇ ᴇxᴘɪʀᴇᴅ ᴏʀ ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ ʙʏ ᴛʜᴇ ᴜᴘʟᴏᴀᴅᴇʀ.')}"
            f"{format_watermark()}"
        )

    try:
        msg = await client.get_messages(file_doc["chat_id"], file_doc["message_id"])
        if msg and msg.media:
            await msg.copy(chat_id=chat_id)
        else:
            await reply_target.reply_text(f"❌ **{to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs ɪɴ sᴛᴏʀᴀɢᴇ ᴄʜᴀɴɴᴇʟ!')}**")
    except Exception as e:
        logger.error(f"Error copying media file for file_id {file_id}: {e}", exc_info=True)
        await reply_target.reply_text(f"❌ **{to_smallcaps('ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ')}**: `{e}`")

# ==================== REVOKE / DELETE STREAM LINK FEATURE ====================

@Client.on_message(filters.private & filters.command(["revoke", "delfile", "revokestream"]))
async def revoke_command_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/revoke <file_id>`\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/revoke abc123xyz`\n\n"
            f"💡 {to_smallcaps('ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ᴅɪsᴀʙʟᴇs ᴛʜᴇ sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋ ғᴏʀ ᴛʜɪs ғɪʟᴇ.')}"
            f"{format_watermark()}"
        )
    file_id = message.command[1].strip()
    file_doc = await file_repo.get_file(file_id, include_revoked=True)
    if not file_doc:
        return await message.reply_text(f"❌ **{to_smallcaps('ғɪʟᴇ ɪᴅ ɴᴏᴛ ғᴏᴜɴᴅ!')}**")

    # Authorize: owner of file or admin
    user_id = message.from_user.id
    if file_doc.get("user_id") and file_doc["user_id"] != user_id and user_id not in Config.ADMINS:
        return await message.reply_text(f"🚫 **{to_smallcaps('ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ʀᴇᴠᴏᴋᴇ ᴛʜɪs sᴛʀᴇᴀᴍ ʟɪɴᴋ!')}**")

    await file_repo.revoke_file(file_id)
    await message.reply_text(
        f"✦ **{to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ ʀᴇᴠᴏᴋᴇᴅ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_doc.get('file_name', 'Media')}`\n"
        f"• 🆔 **{to_smallcaps('ғɪʟᴇ ɪᴅ')}** : `{file_id}`\n\n"
        f"✅ **{to_smallcaps('ᴛʜɪs sᴛʀᴇᴀᴍ ʟɪɴᴋ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴠᴏᴋᴇᴅ & ᴅɪsᴀʙʟᴇᴅ.')}**\n"
        f"• {to_smallcaps('ᴀʟʟ ᴡᴇʙ ᴘʟᴀʏᴇʀs ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋs ᴡɪʟʟ ɴᴏᴡ ʀᴇᴛᴜʀɴ 𝟺𝟶𝟺.')}"
        f"{format_watermark()}"
    )

@Client.on_callback_query(filters.regex(r"^revoke_([a-zA-Z0-9_-]+)"))
async def revoke_callback_entry(client: Client, query: CallbackQuery):
    file_id = query.matches[0].group(1)
    file_doc = await file_repo.get_file(file_id, include_revoked=True)
    if not file_doc:
        return await query.answer(to_smallcaps("ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    user_id = query.from_user.id
    if file_doc.get("user_id") and file_doc["user_id"] != user_id and user_id not in Config.ADMINS:
        return await query.answer(to_smallcaps("ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ʀᴇᴠᴏᴋᴇ ᴛʜɪs ʟɪɴᴋ!"), show_alert=True)

    await file_repo.revoke_file(file_id)
    await query.answer(to_smallcaps("sᴛʀᴇᴀᴍ ʟɪɴᴋ ʀᴇᴠᴏᴋᴇᴅ!"), show_alert=True)

    await query.message.edit_text(
        f"✦ **{to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ ʀᴇᴠᴏᴋᴇᴅ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_doc.get('file_name', 'Media')}`\n"
        f"• 🆔 **{to_smallcaps('ғɪʟᴇ ɪᴅ')}** : `{file_id}`\n\n"
        f"🚫 **{to_smallcaps('ᴛʜɪs sᴛʀᴇᴀᴍ ʟɪɴᴋ ʜᴀs ʙᴇᴇɴ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʀᴇᴠᴏᴋᴇᴅ & ᴅɪsᴀʙʟᴇᴅ.')}**\n"
        f"• {to_smallcaps('ᴀʟʟ ᴡᴇʙ ᴘʟᴀʏᴇʀs ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋs ᴡɪʟʟ ɴᴏᴡ ʀᴇᴛᴜʀɴ 𝟺𝟶𝟺 ɴᴏᴛ ғᴏᴜɴᴅ.')}\n"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")]])
    )
