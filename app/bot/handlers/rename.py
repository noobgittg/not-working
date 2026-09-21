import os
import time
import uuid

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.repositories.user_repo import user_repo
from app.services.autodel_service import schedule_deletion
from app.services.caption_service import format_caption
from app.services.ffmpeg_service import get_media_attributes
from app.services.thumb_service import resolve_thumbnail
from app.utils.cache import cache
from app.utils.font import format_watermark, to_smallcaps
from app.utils.helpers import clean_temp_files, humanbytes, preserve_extension, sanitize_filename, time_formatter
from app.utils.progress import progress_for_pyrogram
from app.utils.task_manager import operation_slot
from config import Config


def _media_info(message: Message):
    media = message.document or message.video or message.audio
    if not media:
        return None, False
    mime = getattr(media, "mime_type", "") or ""
    is_video = bool(message.video or mime.startswith("video/"))
    return media, is_video


def _too_large_text():
    return (
        f"❌ **{to_smallcaps('ғɪʟᴇ ᴏᴠᴇʀ 2 GB ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇɴᴀᴍᴇᴅ')}**\n\n"
        f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ ɪs 2000 MiB (ᴀᴘᴘʀᴏx. 2 GB). ᴛʜɪs ʟɪᴍɪᴛ ɪs ᴄʜᴇᴄᴋᴇᴅ ʙᴇғᴏʀᴇ ᴛʜᴇ ʀᴇɴᴀᴍᴇ ᴜᴘʟᴏᴀᴅ.') }"
    ) + format_watermark()


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def incoming_file_entry(client: Client, message: Message):
    media, is_video = _media_info(message)
    if not media:
        return
    file_name = getattr(media, "file_name", None) or "Unknown_File"
    file_size = humanbytes(getattr(media, "file_size", 0))
    mime_type = getattr(media, "mime_type", "unknown") or "unknown"
    duration_value = getattr(media, "duration", 0) or 0
    duration = time_formatter(seconds=duration_value) if duration_value > 0 else "N/A"

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
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ᴀɴ ᴀᴄᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ:')}**{format_watermark()}"
    )
    row2 = []
    if is_video:
        row2.append(InlineKeyboardButton(f"🗜️ {to_smallcaps('ᴄᴏᴍᴘʀᴇss ᴍᴇᴅɪᴀ')}", callback_data=f"compress_menu_{message.id}"))
    row2.append(InlineKeyboardButton(f"🔍 {to_smallcaps('ᴍᴇᴅɪᴀ ɪɴғᴏ')}", callback_data=f"mediainfo_{message.id}"))
    buttons = [
        [
            InlineKeyboardButton(f"✏️ {to_smallcaps('ʀᴇɴᴀᴍᴇ ғɪʟᴇ')}", callback_data=f"rename_{message.id}"),
            InlineKeyboardButton(f"⚡ {to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ')}", callback_data=f"stream_{message.id}"),
        ],
        row2,
        [InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")],
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)


@Client.on_message(filters.private & filters.command(["setprefix", "prefix"]))
async def set_prefix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/setprefix <prefix_text>`{format_watermark()}")
    prefix = message.text.split(None, 1)[1].strip()
    await user_repo.update_user(message.from_user.id, {"prefix": prefix})
    await message.reply_text(f"✅ **{to_smallcaps('ғɪʟᴇ ᴘʀᴇғɪx sᴀᴠᴇᴅ!')}**\n• 🏷️ `{prefix}`{format_watermark()}")


@Client.on_message(filters.private & filters.command(["setsuffix", "suffix"]))
async def set_suffix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/setsuffix <suffix_text>`{format_watermark()}")
    suffix = message.text.split(None, 1)[1].strip()
    await user_repo.update_user(message.from_user.id, {"suffix": suffix})
    await message.reply_text(f"✅ **{to_smallcaps('ғɪʟᴇ sᴜғғɪx sᴀᴠᴇᴅ!')}**\n• 🏷️ `{suffix}`{format_watermark()}")


@Client.on_message(filters.private & filters.command(["delprefix", "delsuffix"]))
async def del_prefix_suffix(client: Client, message: Message):
    key = "prefix" if "prefix" in message.command[0].lower() else "suffix"
    await user_repo.update_user(message.from_user.id, {key: None})
    await message.reply_text(f"🗑️ **{to_smallcaps(key + ' removed successfully')}**{format_watermark()}")


@Client.on_message(filters.private & filters.command("rename"))
async def rename_cmd_handler(client: Client, message: Message):
    target = message.reply_to_message
    media, is_video = _media_info(target) if target else (None, False)
    if not target or not media:
        return await message.reply_text(f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ғɪʟᴇ, ᴠɪᴅᴇᴏ ᴏʀ ᴀᴜᴅɪᴏ.')}**{format_watermark()}")
    if getattr(media, "file_size", 0) and media.file_size > Config.MAX_TELEGRAM_UPLOAD_BYTES:
        return await message.reply_text(_too_large_text())
    if len(message.command) < 2:
        return await message.reply_text(f"📝 **{to_smallcaps('ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ')}**\nExample: `/rename sample.mp4`{format_watermark()}")
    new_name = sanitize_filename(message.text.split(None, 1)[1])
    old_name = getattr(media, "file_name", None) or "file.bin"
    new_name = preserve_extension(new_name, old_name)
    await cache.set(f"rename_name_{message.from_user.id}_{target.id}", new_name, ttl=600)
    await show_rename_options(message, target.id, new_name, is_video)


@Client.on_callback_query(filters.regex(r"^rename_(\d+)$"))
async def rename_callback_ask(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    media, _ = _media_info(original)
    if media and getattr(media, "file_size", 0) > Config.MAX_TELEGRAM_UPLOAD_BYTES:
        return await query.message.edit_text(_too_large_text())
    old_name = getattr(media, "file_name", None) or "file.bin"
    await query.message.delete()
    prompt = await client.send_message(
        chat_id=query.message.chat.id,
        text=(f"✏️ **{to_smallcaps('ᴇɴᴛᴇʀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ')}**\n\n"
              f"• 📁 `{old_name}`\n\n"
              f"{to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪᴛʜ ʏᴏᴜʀ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ.')}{format_watermark()}"),
        reply_markup=ForceReply(placeholder=to_smallcaps("ᴇɴᴛᴇʀ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ...")),
    )
    await cache.set(f"waiting_rename_{query.from_user.id}", msg_id, ttl=300)
    await cache.set(f"rename_prompt_{query.from_user.id}", prompt.id, ttl=300)


@Client.on_message(filters.private & filters.reply)
async def reply_force_rename_collector(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not isinstance(reply.reply_markup, ForceReply):
        return
    msg_id = await cache.get(f"waiting_rename_{message.from_user.id}")
    if not msg_id or not (message.text or "").strip():
        return
    await cache.delete(f"waiting_rename_{message.from_user.id}")
    original = await client.get_messages(message.chat.id, int(msg_id))
    if not original or not original.media:
        return await message.reply_text(f"❌ {to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs.')}{format_watermark()}")
    media, is_video = _media_info(original)
    if getattr(media, "file_size", 0) > Config.MAX_TELEGRAM_UPLOAD_BYTES:
        return await message.reply_text(_too_large_text())
    old_name = getattr(media, "file_name", None) or "file.bin"
    new_name = preserve_extension(sanitize_filename(message.text.strip()), old_name)
    await cache.set(f"rename_name_{message.from_user.id}_{msg_id}", new_name, ttl=600)
    await show_rename_options(message, int(msg_id), new_name, is_video)


async def show_rename_options(message: Message, target_id: int, new_name: str, is_video: bool = False):
    buttons = [[InlineKeyboardButton(f"📁 {to_smallcaps('ᴜᴘʟᴏᴀᴅ ᴀs ᴅᴏᴄᴜᴍᴇɴᴛ')}", callback_data=f"renameto_doc_{target_id}")]]
    if is_video:
        buttons[0].append(InlineKeyboardButton(f"🎬 {to_smallcaps('ᴜᴘʟᴏᴀᴅ ᴀs ᴠɪᴅᴇᴏ')}", callback_data=f"renameto_vid_{target_id}"))
    buttons.append([InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")])
    await message.reply_text(
        f"✦ **{to_smallcaps('sᴇʟᴇᴄᴛ ᴜᴘʟᴏᴀᴅ ᴛʏᴘᴇ')}** ✦\n\n• 🏷️ `{new_name}`\n\n"
        f"💡 {to_smallcaps('ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ɪs ᴏɴʟʏ ᴏғғᴇʀᴇᴅ ғᴏʀ ᴀᴄᴛᴜᴀʟ ᴠɪᴅᴇᴏs.')}{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@Client.on_callback_query(filters.regex(r"^renameto_(doc|vid)_(\d+)$"))
async def execute_rename_operation(client: Client, query: CallbackQuery):
    upload_type = query.matches[0].group(1)
    target_id = int(query.matches[0].group(2))
    user_id = query.from_user.id
    new_name = await cache.get(f"rename_name_{user_id}_{target_id}")
    if not new_name:
        return await query.answer(to_smallcaps("sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ!"), show_alert=True)

    original = await client.get_messages(query.message.chat.id, target_id)
    if not original or not original.media:
        return await query.message.edit_text(f"❌ {to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs.')}" + format_watermark())
    media, is_video = _media_info(original)
    source_size = getattr(media, "file_size", 0) or 0
    if source_size > Config.MAX_TELEGRAM_UPLOAD_BYTES:
        return await query.message.edit_text(_too_large_text())
    if upload_type == "vid" and not is_video:
        return await query.answer(to_smallcaps("ᴏɴʟʏ ᴠɪᴅᴇᴏ ғɪʟᴇs ᴄᴀɴ ʙᴇ sᴇɴᴛ ᴀs ᴠɪᴅᴇᴏ."), show_alert=True)

    try:
        async with operation_slot(user_id):
            await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ʀᴇɴᴀᴍᴇ ᴡᴏʀᴋғʟᴏᴡ')}**...{format_watermark()}")
            u = await user_repo.get_or_create(user_id, query.from_user.first_name or "User", query.from_user.username)
            prefix = u.get("prefix") or ""
            suffix = u.get("suffix") or ""
            new_name = preserve_extension(sanitize_filename(new_name), getattr(media, "file_name", None) or "file.bin")
            base, ext = os.path.splitext(new_name)
            final_name = sanitize_filename(f"{prefix}{base}{suffix}{ext}")
            if not ext:
                ext = os.path.splitext(final_name)[1]
            workdir = os.path.join(Config.DOWNLOAD_DIR, f"rename_{user_id}_{uuid.uuid4().hex}")
            os.makedirs(workdir, exist_ok=True)
            download_path = os.path.join(workdir, final_name)
            thumb_path = None
            try:
                await original.download(
                    file_name=download_path,
                    progress=progress_for_pyrogram,
                    progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ғɪʟᴇ", query.message, time.time()),
                )
                if not os.path.isfile(download_path):
                    return await query.message.edit_text(f"❌ {to_smallcaps('ғɪʟᴇ ᴡᴀs ɴᴏᴛ ᴅᴏᴡɴʟᴏᴀᴅᴇᴅ ᴄᴏʀʀᴇᴄᴛʟʏ.')}")
                actual_size = os.path.getsize(download_path)
                if actual_size > Config.MAX_TELEGRAM_UPLOAD_BYTES:
                    return await query.message.edit_text(_too_large_text())
                thumb_path = await resolve_thumbnail(client, user_id, workdir, download_path)
                final_caption = await format_caption(
                    user_id=user_id,
                    file_name=final_name,
                    file_size_str=humanbytes(actual_size),
                    ext=ext.lstrip("."),
                    file_caption=original.caption or "",
                )
                await query.message.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ʀᴇɴᴀᴍᴇᴅ ғɪʟᴇ')}**...{format_watermark()}")
                upload_start = time.time()
                if upload_type == "vid":
                    attrs = await get_media_attributes(download_path)
                    if not attrs.get("has_video"):
                        return await query.message.edit_text(f"❌ {to_smallcaps('ғɪʟᴇ ᴅᴏᴇs ɴᴏᴛ ᴄᴏɴᴛᴀɪɴ ᴀ ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍ.')}")
                    sent = await client.send_video(
                        query.message.chat.id, download_path, caption=final_caption,
                        duration=attrs.get("duration", 0), width=attrs.get("width") or 1,
                        height=attrs.get("height") or 1, thumb=thumb_path, supports_streaming=True,
                        progress=progress_for_pyrogram, progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", query.message, upload_start),
                    )
                else:
                    sent = await client.send_document(
                        query.message.chat.id, download_path, caption=final_caption, thumb=thumb_path,
                        force_document=True, progress=progress_for_pyrogram,
                        progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴅᴏᴄᴜᴍᴇɴᴛ", query.message, upload_start),
                    )
            finally:
                clean_temp_files(workdir)
    except RuntimeError as exc:
        return await query.answer(str(exc), show_alert=True)
    except Exception as exc:
        clean_temp_files(locals().get("workdir"))
        return await query.message.edit_text(f"❌ **{to_smallcaps('ʀᴇɴᴀᴍᴇ ᴏᴘᴇʀᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ')}**\n`{str(exc)[:700]}`")

    await cache.delete(f"rename_name_{user_id}_{target_id}")
    await query.message.delete()
    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent:
        await schedule_deletion(sent.chat.id, sent.id, del_time)
