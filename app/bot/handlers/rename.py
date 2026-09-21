import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.cache import cache
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter, clean_temp_files, sanitize_filename
from app.utils.progress import progress_for_pyrogram
from app.services.ffmpeg_service import get_media_attributes
from app.services.thumb_service import resolve_thumbnail
from app.services.caption_service import format_caption
from app.services.autodel_service import schedule_deletion

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def incoming_file_entry(client: Client, message: Message):
    media = message.document or message.video or message.audio
    file_name = getattr(media, "file_name", None) or "Unknown_File"
    file_size = humanbytes(media.file_size)
    mime_type = getattr(media, "mime_type", "unknown")
    duration = time_formatter(seconds=getattr(media, "duration", 0)) if getattr(media, "duration", 0) > 0 else "N/A"

    is_video = bool(message.video or (message.document and mime_type and mime_type.startswith("video/")))

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
    row2.append(InlineKeyboardButton(f"🔍 {to_smallcaps('ᴍᴇᴅɪᴀ ɪɴғᴏ')}", callback_data=f"mediainfo_{message.id}"))
    buttons.append(row2)
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

    await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ʀᴇɴᴀᴍᴇ ᴡᴏʀᴋғʟᴏᴡ...')}**")

    original_msg = await client.get_messages(query.message.chat.id, target_id)
    if not original_msg or not original_msg.media:
        return await query.message.edit_text(f"❌ **{to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!')}**")

    # Fetch user prefix/suffix
    u = await user_repo.get_user(user_id)
    prefix = u.get("prefix") or ""
    suffix = u.get("suffix") or ""

    name_parts = os.path.splitext(new_name)
    base_name = name_parts[0]
    ext = name_parts[1]

    final_name = sanitize_filename(f"{prefix}{base_name}{suffix}{ext}")

    download_dir = f"downloads/{user_id}_{int(time.time())}"
    os.makedirs(download_dir, exist_ok=True)
    download_path = os.path.join(download_dir, final_name)

    start_time = time.time()
    try:
        await original_msg.download(
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ғɪʟᴇ", query.message, start_time)
        )
    except Exception as e:
        clean_temp_files(download_path)
        return await query.message.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    if not os.path.exists(download_path):
        return await query.message.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴀғᴛᴇʀ ᴅᴏᴡɴʟᴏᴀᴅ!')}**")

    file_size_bytes = os.path.getsize(download_path)
    file_size_str = humanbytes(file_size_bytes)

    # Resolve thumbnail
    thumb_path = await resolve_thumbnail(client, user_id, download_path)

    # Format caption
    orig_caption = original_msg.caption or ""
    final_caption = await format_caption(
        user_id=user_id,
        file_name=final_name,
        file_size_str=file_size_str,
        ext=ext.replace(".", ""),
        file_caption=orig_caption
    )

    upload_start = time.time()
    await query.message.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ʀᴇɴᴀᴍᴇᴅ ғɪʟᴇ...')}**")

    sent_msg = None
    try:
        if upload_type == "vid":
            attrs = await get_media_attributes(download_path)
            sent_msg = await client.send_video(
                chat_id=query.message.chat.id,
                video=download_path,
                caption=final_caption,
                duration=attrs["duration"],
                width=attrs["width"],
                height=attrs["height"],
                thumb=thumb_path,
                supports_streaming=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", query.message, upload_start)
            )
        else:
            sent_msg = await client.send_document(
                chat_id=query.message.chat.id,
                document=download_path,
                caption=final_caption,
                thumb=thumb_path,
                force_document=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴅᴏᴄᴜᴍᴇɴᴛ", query.message, upload_start)
            )
    except Exception as e:
        clean_temp_files(download_path, thumb_path)
        return await query.message.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    clean_temp_files(download_path, thumb_path)
    await query.message.delete()

    # Schedule deletion if user has configured timer
    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_msg:
        await schedule_deletion(sent_msg.chat.id, sent_msg.id, del_time)
