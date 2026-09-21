import os
import time
import uuid

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.repositories.user_repo import user_repo
from app.services.autodel_service import schedule_deletion
from app.services.caption_service import format_caption
from app.services.ffmpeg_service import compress_media, get_media_attributes
from app.services.thumb_service import resolve_thumbnail
from app.utils.font import format_watermark, to_smallcaps
from app.utils.helpers import clean_temp_files, humanbytes, sanitize_filename, split_file_async, time_formatter
from app.utils.progress import progress_for_pyrogram
from app.utils.task_manager import operation_slot
from config import Config


@Client.on_message(filters.private & filters.command("compress"))
async def compress_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    media = (target.video or target.audio or target.document) if target else None
    if not target or not media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ, ᴀᴜᴅɪᴏ ᴏʀ ғғᴍᴘᴇɢ-ʀᴇᴀᴅᴀʙʟᴇ ᴅᴏᴄᴜᴍᴇɴᴛ.')}**\n"
            f"`/compress`{format_watermark()}"
        )
    await show_compression_menu(target, message)


@Client.on_callback_query(filters.regex(r"^compress_menu_(\d+)$"))
async def compress_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    media = original.video or original.audio or original.document
    if getattr(media, "file_size", 0) > Config.MAX_TELEGRAM_UPLOAD_BYTES:
        # Downloading large files is supported when Telegram permits it, but the final upload is split if necessary.
        await query.answer(to_smallcaps("ʟᴀʀɢᴇ ғɪʟᴇ: ᴏᴜᴛᴘᴜᴛ ᴡɪʟʟ ʙᴇ sᴘʟɪᴛ ɪғ ɴᴇᴄᴇssᴀʀʏ."), show_alert=False)
    await show_compression_menu(original, query.message, is_callback=True)


async def show_compression_menu(media_msg: Message, target_msg: Message, is_callback: bool = False):
    media = media_msg.video or media_msg.audio or media_msg.document
    file_name = getattr(media, "file_name", None) or ("audio.m4a" if media_msg.audio else "media.bin")
    file_size = humanbytes(getattr(media, "file_size", 0) or 0)
    buttons = [
        [
            InlineKeyboardButton("⚡ 720ᴘ / CRF 28", callback_data=f"do_comp_{media_msg.id}_720_28_superfast"),
            InlineKeyboardButton("🚀 480ᴘ / CRF 30", callback_data=f"do_comp_{media_msg.id}_480_30_ultrafast"),
        ],
        [
            InlineKeyboardButton("📦 360ᴘ / CRF 32", callback_data=f"do_comp_{media_msg.id}_360_32_ultrafast"),
            InlineKeyboardButton("🎚️ 1080ᴘ / CRF 24", callback_data=f"do_comp_{media_msg.id}_1080_24_veryfast"),
        ],
        [
            InlineKeyboardButton("⚖️ CRF 24", callback_data=f"do_comp_{media_msg.id}_0_24_fast"),
            InlineKeyboardButton("💎 CRF 20", callback_data=f"do_comp_{media_msg.id}_0_20_fast"),
        ],
        [InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")],
    ]
    text = (
        f"✦ **{to_smallcaps('ғғᴍᴘᴇɢ ᴍᴇᴅɪᴀ ᴄᴏᴍᴘʀᴇssᴏʀ')}** ✦\n\n"
        f"• 📁 `{file_name}`\n• 📦 `{file_size}`\n\n"
        f"{to_smallcaps('ᴠɪᴅᴇᴏ ᴀɴᴅ ᴀᴜᴅɪᴏ ᴍᴇᴅɪᴀ ᴀʀᴇ ʜᴀɴᴅʟᴇᴅ ᴠɪᴀ ғғᴍᴘᴇɢ. ɴᴏɴ-ᴍᴇᴅɪᴀ ғɪʟᴇs ᴀʀᴇ ʀᴇᴊᴇᴄᴛᴇᴅ ᴄʟᴇᴀʀʟʏ.')}"
        f"{format_watermark()}"
    )
    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^do_comp_(\d+)_(\d+)_(\d+)_([a-z]+)$"))
async def execute_compression(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    scale_h = int(query.matches[0].group(2))
    crf = int(query.matches[0].group(3))
    preset = query.matches[0].group(4)
    user_id = query.from_user.id
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    try:
        async with operation_slot(user_id):
            status = await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴡᴏʀᴋғʟᴏᴡ')}...**{format_watermark()}")
            media = original.video or original.audio or original.document
            raw_name = getattr(media, "file_name", None) or (f"audio_{msg_id}.m4a" if original.audio else f"media_{msg_id}.bin")
            clean_name = sanitize_filename(raw_name)
            workdir = os.path.join(Config.DOWNLOAD_DIR, f"compress_{user_id}_{uuid.uuid4().hex}")
            os.makedirs(workdir, exist_ok=True)
            input_path = os.path.join(workdir, clean_name)
            source_ext = os.path.splitext(clean_name)[1].lower()
            output_ext = ".mp4"
            try:
                await original.download(
                    file_name=input_path,
                    progress=progress_for_pyrogram,
                    progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ", status, time.time()),
                )
                if not os.path.isfile(input_path):
                    return await status.edit_text(f"❌ {to_smallcaps('ғɪʟᴇ ᴡᴀs ɴᴏᴛ ᴅᴏᴡɴʟᴏᴀᴅᴇᴅ.')}")
                attrs = await get_media_attributes(input_path)
                if not attrs.get("has_video") and not attrs.get("has_audio"):
                    return await status.edit_text(
                        f"❌ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ')}**\n\n"
                        f"{to_smallcaps('ᴛʜɪs ғɪʟᴇ ʜᴀs ɴᴏ ᴀᴜᴅɪᴏ ᴏʀ ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍ ᴛʜᴀᴛ ғғᴍᴘᴇɢ ᴄᴀɴ ᴅᴇᴄᴏᴅᴇ.')}"
                    )
                is_video = bool(attrs.get("has_video"))
                if is_video:
                    output_name = f"compressed_{os.path.splitext(clean_name)[0]}.mp4"
                else:
                    output_ext = ".m4a"
                    output_name = f"compressed_{os.path.splitext(clean_name)[0]}.m4a"
                output_path = os.path.join(workdir, sanitize_filename(output_name))
                await status.edit_text(f"🗜️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪɴɢ ᴍᴇᴅɪᴀ')}...**{format_watermark()}")
                comp_start = time.time()
                success = await compress_media(
                    input_path, output_path, crf=crf, preset=preset, scale_height=scale_h,
                    progress_message=status, total_duration=attrs.get("duration", 0),
                )
                comp_duration = time.time() - comp_start
                if not success or not os.path.isfile(output_path):
                    return await status.edit_text(f"❌ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ')}**\n{to_smallcaps('ᴛʀʏ ᴀ ᴅɪғғᴇʀᴇɴᴛ ғɪʟᴇ ᴏʀ ʟᴏᴡᴇʀ ʀᴇsᴏʟᴜᴛɪᴏɴ.')}" )

                comp_size = os.path.getsize(output_path)
                orig_size = os.path.getsize(input_path)
                savings = round((orig_size - comp_size) / orig_size * 100, 2) if orig_size else 0
                attrs_out = await get_media_attributes(output_path)
                base_caption = await format_caption(
                    user_id=user_id,
                    file_name=os.path.basename(output_path),
                    file_size_str=humanbytes(comp_size),
                    duration_str=time_formatter(seconds=attrs_out.get("duration", 0)),
                    ext=output_ext.lstrip("."),
                    file_caption=original.caption or "",
                )
                final_caption = base_caption + (
                    f"\n\n📊 **{to_smallcaps('ᴄᴏᴍᴘʀᴇssɪᴏɴ sᴛᴀᴛɪsᴛɪᴄs')}**\n"
                    f"• 📦 `{humanbytes(orig_size)}` → `{humanbytes(comp_size)}`\n"
                    f"• 📉 `{savings}%`\n"
                    f"• ⏱️ `{time_formatter(seconds=round(comp_duration))}`"
                )
                await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴏᴍᴘʀᴇssᴇᴅ ᴍᴇᴅɪᴀ')}...**{format_watermark()}")

                # The observed Pyrofork/Telegram Bot API ceiling is 2000 MiB. Split oversized output into safe parts.
                if comp_size > Config.SAFE_TELEGRAM_PART_BYTES:
                    parts = await split_file_async(output_path, max_bytes=Config.SAFE_TELEGRAM_PART_BYTES)
                    if not parts:
                        return await status.edit_text(f"❌ {to_smallcaps('ᴄᴏᴜʟᴅ ɴᴏᴛ sᴘʟɪᴛ ᴛʜᴇ ᴏᴜᴛᴘᴜᴛ ғɪʟᴇ.')}")
                    sent_messages = []
                    total_parts = len(parts)
                    for index, part in enumerate(parts, 1):
                        caption = f"{final_caption}\n\n📦 **Part {index}/{total_parts}**"
                        sent = await client.send_document(
                            query.message.chat.id, part, caption=caption, force_document=True,
                            progress=progress_for_pyrogram,
                            progress_args=(f"📤 Part {index}/{total_parts}", status, time.time()),
                        )
                        sent_messages.append(sent)
                    for part in parts:
                        clean_temp_files(part)
                else:
                    thumb_path = await resolve_thumbnail(client, user_id, workdir, output_path) if attrs_out.get("has_video") else None
                    try:
                        if attrs_out.get("has_video"):
                            sent = await client.send_video(
                                query.message.chat.id, output_path, caption=final_caption,
                                duration=attrs_out.get("duration", 0), width=attrs_out.get("width") or 1,
                                height=attrs_out.get("height") or 1, thumb=thumb_path, supports_streaming=True,
                                progress=progress_for_pyrogram,
                                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, time.time()),
                            )
                        else:
                            sent = await client.send_audio(
                                query.message.chat.id, output_path, caption=final_caption,
                                duration=attrs_out.get("duration", 0),
                                progress=progress_for_pyrogram,
                                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴀᴜᴅɪᴏ", status, time.time()),
                            )
                    finally:
                        clean_temp_files(thumb_path)
                    sent_messages = [sent]
            finally:
                clean_temp_files(workdir)
    except RuntimeError as exc:
        return await query.answer(str(exc), show_alert=True)
    except Exception as exc:
        clean_temp_files(locals().get("workdir"))
        return await query.message.edit_text(f"❌ **{to_smallcaps('ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ')}**\n`{str(exc)[:700]}`")

    await query.message.delete()
    u = await user_repo.get_user(user_id)
    del_time = u.get("auto_delete_time", 0) if u else 0
    for sent in sent_messages:
        if del_time > 0:
            await schedule_deletion(sent.chat.id, sent.id, del_time)
