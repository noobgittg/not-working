import os
import time
import secrets
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ForceReply
)
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.cache import cache
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter, clean_temp_files, sanitize_filename
from app.utils.progress import progress_for_pyrogram
from app.services.ffmpeg_service import get_media_attributes
from app.services.thumb_service import resolve_thumbnail
from app.services.caption_service import extract_and_format_caption
from app.services.autodel_service import schedule_deletion

MAX_BOT_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MiB (2GB Telegram Bot API Limit)

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def incoming_file_entry(client: Client, message: Message):
    media = message.document or message.video or message.audio
    file_name = getattr(media, "file_name", None) or "Unknown_File"
    file_size_bytes = getattr(media, "file_size", 0)
    file_size = humanbytes(file_size_bytes)
    mime_type = getattr(media, "mime_type", "unknown")
    duration = time_formatter(seconds=getattr(media, "duration", 0)) if getattr(media, "duration", 0) > 0 else "N/A"

    is_video = bool(message.video or (message.document and mime_type and mime_type.startswith("video/")))

    if file_size_bytes > MAX_BOT_FILE_SIZE:
        text = (
            f"✦ **{to_smallcaps('sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ɪɴsᴘᴇᴄᴛᴏʀ')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
            f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{file_size}`\n"
            f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{duration}`\n\n"
            f"⚠️ **{to_smallcaps('ɴᴏᴛᴇ')}** : {to_smallcaps('ᴛʜɪs ғɪʟᴇ ᴇxᴄᴇᴇᴅs ᴛᴇʟᴇɢʀᴀᴍ 𝟸ɢʙ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ.')}\n"
            f"💡 {to_smallcaps('ʏᴏᴜ ᴄᴀɴ ɢᴇɴᴇʀᴀᴛᴇ ᴀɴ ɪɴsᴛᴀɴᴛ sᴜᴘᴇʀ-sᴏɴɪᴄ sᴛʀᴇᴀᴍ & ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ ʙᴇʟᴏᴡ:')}"
            f"{format_watermark()}"
        )
        buttons = [
            [InlineKeyboardButton(f"⚡ {to_smallcaps('ɢᴇɴᴇʀᴀᴛᴇ sᴛʀᴇᴀᴍ ʟɪɴᴋ')}", callback_data=f"stream_{message.id}")],
            [InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")]
        ]
        return await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

    u = await user_repo.get_user(message.from_user.id)
    has_thumb = "✅" if u and u.get("thumb_id") else "🌐 ᴛʜᴀᴍ_ᴜʀʟ"
    has_caption = "✅" if u and (u.get("custom_caption") or u.get("captions_list")) else "📄 ᴏʀɪɢɪɴᴀʟ"

    text = (
        f"✦ **{to_smallcaps('sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ɪɴsᴘᴇᴄᴛᴏʀ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{file_size}`\n"
        f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{duration}`\n"
        f"• 🖼️ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ')}** : `{has_thumb}`\n"
        f"• 📝 **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴ')}** : `{has_caption}`\n\n"
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ᴀɴ ᴀᴄᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"✏️ {to_smallcaps('ʀᴇɴᴀᴍᴇ ғɪʟᴇ')}", callback_data=f"rename_{message.id}"),
            InlineKeyboardButton(f"⚡ {to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ')}", callback_data=f"stream_{message.id}")
        ]
    ]
    row2 = []
    if is_video:
        row2.append(InlineKeyboardButton(f"🗜️ {to_smallcaps('ᴄᴏᴍᴘʀᴇss ᴠɪᴅᴇᴏ')}", callback_data=f"compress_menu_{message.id}"))
    row2.append(InlineKeyboardButton(f"📊 {to_smallcaps('ᴍᴇᴅɪᴀɪɴғᴏ')}", callback_data=f"pro_mediainfo_{message.id}"))
    buttons.append(row2)
    buttons.append([
        InlineKeyboardButton(f"🎛️ {to_smallcaps('ғɪʟᴇ ᴘʀᴏ ᴀᴅᴠᴀɴᴄᴇ ғᴇᴀᴛᴜʀᴇs')}", callback_data=f"pro_menu_{message.id}")
    ])
    buttons.append([
        InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
    ])

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

@Client.on_message(filters.private & filters.command(["setprefix", "prefix"]))
async def set_prefix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/setprefix <prefix_text>`\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/setprefix [MMW] `\n\n"
            f"💡 {to_smallcaps('ᴛʜɪs ᴘʀᴇғɪx ᴡɪʟʟ ʙᴇ ᴘʀᴇᴘᴇɴᴅᴇᴅ ᴛᴏ ᴇᴠᴇʀʏ ʀᴇɴᴀᴍᴇᴅ ғɪʟᴇ.')}"
            f"{format_watermark()}"
        )
    prefix = message.text.split(None, 1)[1]
    await user_repo.update_user(message.from_user.id, {"prefix": prefix})
    await message.reply_text(
        f"✅ **{to_smallcaps('ғɪʟᴇ ᴘʀᴇғɪx sᴀᴠᴇᴅ!')}**\n\n"
        f"• 🏷️ **{to_smallcaps('ɴᴇᴡ ᴘʀᴇғɪx')}** : `{prefix}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["setsuffix", "suffix"]))
async def set_suffix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/setsuffix <suffix_text>`\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/setsuffix  @mallumovieworldmain2`\n\n"
            f"💡 {to_smallcaps('ᴛʜɪs sᴜғғɪx ᴡɪʟʟ ʙᴇ ɪɴsᴇʀᴛᴇᴅ ʙᴇғᴏʀᴇ ᴛʜᴇ ғɪʟᴇ ᴇxᴛᴇɴsɪᴏɴ.')}"
            f"{format_watermark()}"
        )
    suffix = message.text.split(None, 1)[1]
    await user_repo.update_user(message.from_user.id, {"suffix": suffix})
    await message.reply_text(
        f"✅ **{to_smallcaps('ғɪʟᴇ sᴜғғɪx sᴀᴠᴇᴅ!')}**\n\n"
        f"• 🏷️ **{to_smallcaps('ɴᴇᴡ sᴜғғɪx')}** : `{suffix}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["delprefix", "delsuffix"]))
async def del_prefix_suffix(client: Client, message: Message):
    cmd = message.command[0].lower()
    if "prefix" in cmd:
        await user_repo.update_user(message.from_user.id, {"prefix": None})
        await message.reply_text(f"🗑️ **{to_smallcaps('ғɪʟᴇ ᴘʀᴇғɪx ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**{format_watermark()}")
    else:
        await user_repo.update_user(message.from_user.id, {"suffix": None})
        await message.reply_text(f"🗑️ **{to_smallcaps('ғɪʟᴇ sᴜғғɪx ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("rename"))
async def rename_cmd_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ғɪʟᴇ ᴏʀ ᴠɪᴅᴇᴏ ᴛᴏ ʀᴇɴᴀᴍᴇ.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/rename <new_name.ext>`"
            f"{format_watermark()}"
        )

    media = target.document or target.video or target.audio
    if getattr(media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ғɪʟᴇ ᴛᴏᴏ ʟᴀʀɢᴇ (> 𝟸ɢʙ)!')}**\n\n"
            f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ʀᴇsᴛʀɪᴄᴛs ʙᴏᴛ ᴜᴘʟᴏᴀᴅs ᴛᴏ 𝟸ɢʙ. ғɪʟᴇs ʟᴀʀɢᴇʀ ᴛʜᴀɴ 𝟸ɢʙ ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇɴᴀᴍᴇᴅ.')}\n\n"
            f"💡 {to_smallcaps('ᴜsᴇ')} `/stream` {to_smallcaps('ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀ sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋ ɪɴsᴛᴇᴀᴅ!')}"
            f"{format_watermark()}"
        )

    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ!')}**\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/rename sample_video.mp4`"
            f"{format_watermark()}"
        )

    new_name = message.text.split(None, 1)[1]
    new_name = sanitize_filename(new_name)
    await cache.set(f"rename_name_{message.from_user.id}_{target.id}", new_name, ttl=600)
    await show_rename_options(message, target.id, new_name)

@Client.on_callback_query(filters.regex(r"^rename_(\d+)"))
async def rename_callback_ask(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    media = original.document or original.video or original.audio
    if getattr(media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await query.message.edit_text(
            f"⚠️ **{to_smallcaps('ғɪʟᴇ ᴛᴏᴏ ʟᴀʀɢᴇ (> 𝟸ɢʙ)!')}**\n\n"
            f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ᴅᴏᴇs ɴᴏᴛ sᴜᴘᴘᴏʀᴛ ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇs ɢʀᴇᴀᴛᴇʀ ᴛʜᴀɴ 𝟸ɢʙ. ᴄᴀɴɴᴏᴛ ʀᴇɴᴀᴍᴇ.')}\n\n"
            f"💡 {to_smallcaps('ᴜsᴇ ᴛʜᴇ sᴛʀᴇᴀᴍ ʟɪɴᴋ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴡᴀᴛᴄʜ ᴏʀ ᴅᴏᴡɴʟᴏᴀᴅ ɪɴsᴛᴀɴᴛʟʏ!')}"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⚡ {to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ')}", callback_data=f"stream_{msg_id}")]])
        )

    old_name = getattr(media, "file_name", None) or "file.bin"

    await query.message.delete()
    await client.send_message(
        chat_id=query.message.chat.id,
        text=(
            f"✏️ **{to_smallcaps('ᴇɴᴛᴇʀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ')}**\n\n"
            f"• 📁 **{to_smallcaps('ᴄᴜʀʀᴇɴᴛ')}** : `{old_name}`\n\n"
            f"💬 {to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪᴛʜ ʏᴏᴜʀ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ (ɪɴᴄʟᴜᴅɪɴɢ ᴇxᴛᴇɴsɪᴏɴ).')}\n"
            f"💡 {to_smallcaps('sᴇɴᴅ')} `/cancel` {to_smallcaps('ᴛᴏ ᴀʙᴏʀᴛ.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("ᴇɴᴛᴇʀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ..."))
    )
    await cache.set(f"waiting_rename_{query.from_user.id}", msg_id, ttl=300)

@Client.on_message(filters.private & filters.reply)
async def reply_force_rename_collector(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_markup:
        return
    if not isinstance(message.reply_to_message.reply_markup, ForceReply):
        return

    msg_id = await cache.get(f"waiting_rename_{message.from_user.id}")
    if not msg_id:
        return

    await cache.delete(f"waiting_rename_{message.from_user.id}")
    new_name = sanitize_filename(message.text.strip())
    await cache.set(f"rename_name_{message.from_user.id}_{msg_id}", new_name, ttl=600)
    await show_rename_options(message, msg_id, new_name)

async def show_rename_options(message: Message, target_id: int, new_name: str):
    btn = [
        [
            InlineKeyboardButton(f"📁 {to_smallcaps('ᴜᴘʟᴏᴀᴅ ᴀs ᴅᴏᴄᴜᴍᴇɴᴛ')}", callback_data=f"renameto_doc_{target_id}"),
            InlineKeyboardButton(f"🎬 {to_smallcaps('ᴜᴘʟᴏᴀᴅ ᴀs ᴠɪᴅᴇᴏ')}", callback_data=f"renameto_vid_{target_id}")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
        ]
    ]
    await message.reply_text(
        f"✦ **{to_smallcaps('sᴇʟᴇᴄᴛ ᴜᴘʟᴏᴀᴅ ᴛʏᴘᴇ')}** ✦\n\n"
        f"• 🏷️ **{to_smallcaps('ᴛᴀʀɢᴇᴛ ɴᴀᴍᴇ')}** : `{new_name}`\n\n"
        f"💡 {to_smallcaps('ᴄʜᴏᴏsᴇ ᴡʜᴇᴛʜᴇʀ ᴛᴏ sᴇɴᴅ ᴛʜᴇ ғɪʟᴇ ᴀs ᴀ sᴛʀᴇᴀᴍᴀʙʟᴇ ᴠɪᴅᴇᴏ ᴏʀ ᴀ ʀᴀᴡ ᴅᴏᴄᴜᴍᴇɴᴛ.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^renameto_(doc|vid)_(\d+)"))
async def execute_rename_operation(client: Client, query: CallbackQuery):
    upload_type = query.matches[0].group(1)
    target_id = int(query.matches[0].group(2))
    user_id = query.from_user.id

    new_name = await cache.get(f"rename_name_{user_id}_{target_id}")
    if not new_name:
        return await query.answer(to_smallcaps("sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ! ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ."), show_alert=True)

    status_msg = await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ʀᴇɴᴀᴍᴇ ᴡᴏʀᴋғʟᴏᴡ...')}**")

    original_msg = await client.get_messages(query.message.chat.id, target_id)
    if not original_msg or not original_msg.media:
        return await status_msg.edit_text(f"❌ **{to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!')}**")

    media = original_msg.document or original_msg.video or original_msg.audio
    if getattr(media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await status_msg.edit_text(
            f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: ғɪʟᴇs ʟᴀʀɢᴇʀ ᴛʜᴀɴ 𝟸ɢʙ ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇɴᴀᴍᴇᴅ!')}**\n\n"
            f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ʜᴀs ᴀ sᴛʀɪᴄᴛ 𝟸𝟶𝟶𝟶 ᴍɪʙ (𝟸ɢʙ) ʟɪᴍɪᴛ ғᴏʀ ʙᴏᴛ ᴜᴘʟᴏᴀᴅs.')}"
            f"{format_watermark()}"
        )

    # Fetch user prefix/suffix
    u = await user_repo.get_user(user_id)
    prefix = u.get("prefix") or ""
    suffix = u.get("suffix") or ""

    name_parts = os.path.splitext(new_name)
    base_name = name_parts[0]
    ext = name_parts[1]

    final_name = sanitize_filename(f"{prefix}{base_name}{suffix}{ext}")

    # Isolated directory with random token for unlimited concurrent operations
    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_{target_id}_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    download_path = os.path.join(download_dir, final_name)

    start_time = time.time()
    try:
        await original_msg.download(
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ғɪʟᴇ", status_msg, start_time)
        )
    except Exception as e:
        clean_temp_files(download_path, download_dir)
        return await status_msg.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    if not os.path.exists(download_path):
        clean_temp_files(download_dir)
        return await status_msg.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴀғᴛᴇʀ ᴅᴏᴡɴʟᴏᴀᴅ!')}**")

    file_size_bytes = os.path.getsize(download_path)
    if file_size_bytes > MAX_BOT_FILE_SIZE:
        clean_temp_files(download_path, download_dir)
        return await status_msg.edit_text(
            f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: ғɪʟᴇ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ (𝟸𝟶𝟶𝟶 ᴍɪʙ) ʟɪᴍɪᴛ!')}**\n\n"
            f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ᴅᴏᴇs ɴᴏᴛ ᴀʟʟᴏᴡ ʙᴏᴛs ᴛᴏ ᴜᴘʟᴏᴀᴅ ғɪʟᴇs ʟᴀʀɢᴇʀ ᴛʜᴀɴ 𝟸ɢʙ.')}"
            f"{format_watermark()}"
        )

    attrs = await get_media_attributes(download_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(
        client=client,
        user_id=user_id,
        temp_dir=download_dir,
        video_path=download_path,
        duration=dur
    )
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    # Deep metadata-driven caption
    orig_caption = original_msg.caption or ""
    final_caption = await extract_and_format_caption(
        user_id=user_id,
        file_path=download_path,
        original_caption=orig_caption,
        file_id=str(target_id)
    )

    upload_start = time.time()
    await status_msg.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ʀᴇɴᴀᴍᴇᴅ ғɪʟᴇ...')}**")

    sent_msg = None
    try:
        if upload_type == "vid":
            w = int(attrs["width"])
            h = int(attrs["height"])
            sent_msg = await client.send_video(
                chat_id=query.message.chat.id,
                video=download_path,
                caption=final_caption,
                duration=dur,
                width=w,
                height=h,
                thumb=thumb_path,
                supports_streaming=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status_msg, upload_start)
            )
        else:
            sent_msg = await client.send_document(
                chat_id=query.message.chat.id,
                document=download_path,
                caption=final_caption,
                thumb=thumb_path,
                force_document=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴅᴏᴄᴜᴍᴇɴᴛ", status_msg, upload_start)
            )
    except Exception as e:
        clean_temp_files(download_path, thumb_path, download_dir)
        err_text = str(e)
        if "2000" in err_text or "bigger than" in err_text.lower():
            return await status_msg.edit_text(
                f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: ғɪʟᴇ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ (𝟸𝟶𝟶𝟶 ᴍɪʙ) ʟɪᴍɪᴛ!')}**\n\n"
                f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ᴅᴏᴇs ɴᴏᴛ ᴀʟʟᴏᴡ ʙᴏᴛs ᴛᴏ ᴜᴘʟᴏᴀᴅ ғɪʟᴇs ʟᴀʀɢᴇʀ ᴛʜᴀɴ 𝟸ɢʙ.')}"
                f"{format_watermark()}"
            )
        return await status_msg.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{err_text}`")

    clean_temp_files(download_path, thumb_path, download_dir)
    try:
        await status_msg.delete()
    except Exception:
        pass

    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_msg:
        await schedule_deletion(sent_msg.chat.id, sent_msg.id, del_time)
