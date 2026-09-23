import os
import time
import secrets
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter, clean_temp_files, sanitize_filename
from app.utils.progress import progress_for_pyrogram
from app.services.ffmpeg_service import get_media_attributes, compress_media, check_media_streams, compress_audio
from app.services.thumb_service import resolve_thumbnail
from app.services.caption_service import extract_and_format_caption, format_caption
from app.services.autodel_service import schedule_deletion

MAX_BOT_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MiB

@Client.on_message(filters.private & filters.command("compress"))
async def compress_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document or target.audio):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ᴀᴜᴅɪᴏ ғɪʟᴇ ᴛᴏ ᴄᴏᴍᴘʀᴇss.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇᴅɪᴀ ᴡɪᴛʜ')} `/compress`"
            f"{format_watermark()}"
        )
    await show_compression_menu(target, message)

@Client.on_callback_query(filters.regex(r"^compress_menu_(\d+)"))
async def compress_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await show_compression_menu(original_msg, query.message, is_callback=True)

async def show_compression_menu(media_msg: Message, target_msg: Message, is_callback: bool = False):
    msg_id = media_msg.id
    media = media_msg.video or media_msg.document or media_msg.audio
    file_name = getattr(media, "file_name", "video.mp4")
    file_size_bytes = getattr(media, "file_size", 0)
    file_size = humanbytes(file_size_bytes)

    btn = [
        [
            InlineKeyboardButton("⚡ 720ᴘ ʜᴅ (sᴜᴘᴇʀ ғᴀsᴛ)", callback_data=f"do_comp_{msg_id}_720_28_superfast"),
            InlineKeyboardButton("🚀 480ᴘ sᴅ (ᴜʟᴛʀᴀ ғᴀsᴛ)", callback_data=f"do_comp_{msg_id}_480_30_ultrafast")
        ],
        [
            InlineKeyboardButton("📦 360ᴘ (ᴍᴀx sᴀᴠɪɴɢ)", callback_data=f"do_comp_{msg_id}_360_32_ultrafast"),
            InlineKeyboardButton("🎚️ 1080ᴘ (ғᴜʟʟ ʜᴅ)", callback_data=f"do_comp_{msg_id}_1080_24_veryfast")
        ],
        [
            InlineKeyboardButton("⚖️ ᴄʀғ 24 (ʙᴀʟᴀɴᴄᴇᴅ)", callback_data=f"do_comp_{msg_id}_0_24_fast"),
            InlineKeyboardButton("💎 ᴄʀғ 20 (ʜɪɢʜ ǫᴜᴀʟɪᴛʏ)", callback_data=f"do_comp_{msg_id}_0_20_fast")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
        ]
    ]

    size_note = ""
    if file_size_bytes > MAX_BOT_FILE_SIZE:
        size_note = f"\n⚠️ **{to_smallcaps('ɴᴏᴛᴇ')}** : {to_smallcaps('ᴏʀɪɢɪɴᴀʟ ɪs > 𝟸ɢʙ. ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴡɪʟʟ ʙʀɪɴɢ ɪᴛ ᴜɴᴅᴇʀ 𝟸ɢʙ sᴏ ɪᴛ ᴄᴀɴ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ.')}\n"

    text = (
        f"✦ **{to_smallcaps('ғғᴍᴘᴇɢ ᴠɪᴅᴇᴏ ᴄᴏᴍᴘʀᴇssᴏʀ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ᴄᴜʀʀᴇɴᴛ sɪᴢᴇ')}** : `{file_size}`"
        f"{size_note}\n"
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴅᴇsɪʀᴇᴅ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴘʀᴇsᴇᴛ:')}**\n"
        f"• 720ᴘ ʜᴅ : {to_smallcaps('ʙᴇsᴛ ʙᴀʟᴀɴᴄᴇ ᴏғ ǫᴜᴀʟɪᴛʏ ᴀɴᴅ sɪᴢᴇ')}\n"
        f"• 480ᴘ sᴅ : {to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ ғᴀsᴛ & ʟᴏᴡ sɪᴢᴇ')}\n"
        f"• 360ᴘ : {to_smallcaps('ᴍᴀxɪᴍᴜᴍ sɪᴢᴇ ʀᴇᴅᴜᴄᴛɪᴏɴ')}\n"
        f"• 1080ᴘ : {to_smallcaps('ғᴜʟʟ ʜᴅ ǫᴜᴀʟɪᴛʏ ᴘʀᴇsᴇʀᴠᴀᴛɪᴏɴ')}"
        f"{format_watermark()}"
    )
    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^do_comp_(\d+)_(\d+)_(\d+)_([a-z]+)"))
async def execute_compression(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    scale_h = int(query.matches[0].group(2))
    crf = int(query.matches[0].group(3))
    preset = query.matches[0].group(4)
    user_id = query.from_user.id

    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    status = await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴡᴏʀᴋғʟᴏᴡ...')}**")

    media = original_msg.video or original_msg.document or original_msg.audio
    raw_name = getattr(media, "file_name", None) or f"video_{msg_id}.mp4"
    clean_name = sanitize_filename(raw_name)

    # Unique isolated directory for unlimited simultaneous operations per user
    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_comp_{msg_id}_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    input_path = os.path.join(download_dir, clean_name)
    output_path = os.path.join(download_dir, f"compressed_{clean_name}")

    start_dl = time.time()
    try:
        await original_msg.download(
            file_name=input_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    if not os.path.exists(input_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴀғᴛᴇʀ ᴅᴏᴡɴʟᴏᴀᴅ!')}**")

    # Inspect media streams
    stream_info = await check_media_streams(input_path)
    has_video = stream_info["has_video"]
    has_audio = stream_info["has_audio"]

    if not has_video and not has_audio:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ')}**\n\n"
            f"⚠️ {to_smallcaps('ᴛʜɪs ғɪʟᴇ ʜᴀs ɴᴏ ᴀᴜᴅɪᴏ ᴏʀ ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍ ᴛʜᴀᴛ ғғᴍᴘᴇɢ ᴄᴀɴ ᴅᴇᴄᴏᴅᴇ.')}\n\n"
            f"💡 {to_smallcaps('ᴛᴏ ʀᴇɴᴀᴍᴇ ᴛʜɪs ғɪʟᴇ (ᴘᴅғ, ᴢɪᴘ, ᴀᴘᴋ), ᴜsᴇ')} `/rename` {to_smallcaps('ɪɴsᴛᴇᴀᴅ.')}"
            f"{format_watermark()}"
        )

    orig_size = os.path.getsize(input_path)
    total_duration = getattr(media, "duration", 0)

    comp_start = time.time()
    if has_video:
        await status.edit_text(f"🗜️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ɪɴ ᴘʀᴏɢʀᴇss (ᴜɴɪᴠᴇʀsᴀʟ ʜ.𝟸𝟼𝟺)...')}**")
        success = await compress_media(
            input_path,
            output_path,
            crf=crf,
            preset=preset,
            scale_height=scale_h,
            progress_message=status,
            total_duration=total_duration
        )
    else:
        # Audio only file
        await status.edit_text(f"🗜️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴀᴜᴅɪᴏ ᴄᴏᴍᴘʀᴇssɪᴏɴ ɪɴ ᴘʀᴏɢʀᴇss...')}**")
        if not output_path.endswith((".m4a", ".mp3", ".aac")):
            output_path += ".m4a"
        success = await compress_audio(input_path, output_path)

    comp_duration = time.time() - comp_start

    if not success or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ')}**\n\n"
            f"⚠️ {to_smallcaps('ᴇɴᴄᴏᴅɪɴɢ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴅᴜʀɪɴɢ ᴍᴇᴅɪᴀ ᴄᴏᴍᴘʀᴇssɪᴏɴ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɴᴏᴛʜᴇʀ ᴘʀᴇsᴇᴛ (ᴇ.ɢ. 𝟺𝟾𝟶ᴘ ᴏʀ 𝟹𝟼𝟶ᴘ).')}\n\n"
            f"💡 {to_smallcaps('ʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴜsᴇ')} `/stream` {to_smallcaps('ᴛᴏ ᴡᴀᴛᴄʜ ᴏʀ sʜᴀʀᴇ ᴛʜᴇ ғɪʟᴇ ᴅɪʀᴇᴄᴛʟʏ.')}"
            f"{format_watermark()}"
        )

    comp_size = os.path.getsize(output_path)
    if comp_size > MAX_BOT_FILE_SIZE:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: ᴄᴏᴍᴘʀᴇssᴇᴅ ғɪʟᴇ sᴛɪʟʟ > 𝟸ɢʙ!')}**\n\n"
            f"• 📦 **{to_smallcaps('sɪᴢᴇ')}** : `{humanbytes(comp_size)}`\n\n"
            f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ʀᴇsᴛʀɪᴄᴛs ᴜᴘʟᴏᴀᴅs ᴛᴏ 𝟸ɢʙ. ᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ᴀ ʟᴏᴡᴇʀ ǫᴜᴀʟɪᴛʏ ᴘʀᴇsᴇᴛ (ᴇ.ɢ. 𝟺𝟾𝟶ᴘ ᴏʀ 𝟹𝟼𝟶ᴘ) ᴛᴏ ʀᴇᴅᴜᴄᴇ ɪᴛ ғᴜʀᴛʜᴇʀ.')}"
            f"{format_watermark()}"
        )

    savings = round(((orig_size - comp_size) / orig_size) * 100, 2) if orig_size > 0 else 0

    attrs = await get_media_attributes(output_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(
        client=client,
        user_id=user_id,
        temp_dir=download_dir,
        video_path=output_path,
        duration=dur
    )
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    # Deep metadata-driven caption
    orig_caption = original_msg.caption or ""
    base_caption = await extract_and_format_caption(
        user_id=user_id,
        file_path=output_path,
        original_caption=orig_caption,
        file_id=str(msg_id)
    )

    stats_summary = (
        f"\n\n📊 **{to_smallcaps('ᴄᴏᴍᴘʀᴇssɪᴏɴ sᴛᴀᴛɪsᴛɪᴄs')}** :\n"
        f"• 📦 **{to_smallcaps('ᴏʀɪɢɪɴᴀʟ sɪᴢᴇ')}** : `{humanbytes(orig_size)}`\n"
        f"• 📦 **{to_smallcaps('ᴄᴏᴍᴘʀᴇssᴇᴅ sɪᴢᴇ')}** : `{humanbytes(comp_size)}`\n"
        f"• 📉 **{to_smallcaps('sᴘᴀᴄᴇ sᴀᴠᴇᴅ')}** : `{savings}%`\n"
        f"• ⏱️ **{to_smallcaps('ᴇɴᴄᴏᴅɪɴɢ ᴛɪᴍᴇ')}** : `{time_formatter(seconds=round(comp_duration))}`"
    )
    final_caption = base_caption + stats_summary

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴏᴍᴘʀᴇssᴇᴅ ᴍᴇᴅɪᴀ...')}**")

    sent_video = None
    try:
        if has_video:
            w = int(attrs["width"])
            h = int(attrs["height"])
            sent_video = await client.send_video(
                chat_id=query.message.chat.id,
                video=output_path,
                caption=final_caption,
                duration=dur,
                width=w,
                height=h,
                thumb=thumb_path,
                supports_streaming=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, upload_start)
            )
        else:
            sent_video = await client.send_audio(
                chat_id=query.message.chat.id,
                audio=output_path,
                caption=final_caption,
                duration=dur,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴀᴜᴅɪᴏ", status, upload_start)
            )
    except Exception as e:
        clean_temp_files(input_path, output_path, thumb_path, download_dir)
        err_str = str(e)
        if "2000" in err_str or "bigger than" in err_str.lower():
            return await status.edit_text(
                f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: ғɪʟᴇ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ (𝟸𝟶𝟶𝟶 ᴍɪʙ) ʟɪᴍɪᴛ!')}**\n\n"
                f"{to_smallcaps('ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ᴅᴏᴇs ɴᴏᴛ ᴀʟʟᴏᴡ ʙᴏᴛs ᴛᴏ ᴜᴘʟᴏᴀᴅ ғɪʟᴇs ʟᴀʀɢᴇʀ ᴛʜᴀɴ 𝟸ɢʙ.')}"
                f"{format_watermark()}"
            )
        return await status.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{err_str}`")

    clean_temp_files(input_path, output_path, thumb_path, download_dir)
    try:
        await status.delete()
    except Exception:
        pass

    u = await user_repo.get_user(user_id)
    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_video:
        await schedule_deletion(sent_video.chat.id, sent_video.id, del_time)
