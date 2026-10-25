import os
import time
import secrets
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from config import Config
from plugins.core_db import user_repo
from plugins.core_utils import (
    cache,
    to_smallcaps,
    format_watermark,
    humanbytes,
    time_formatter,
    clean_temp_files,
    sanitize_filename,
    progress_for_pyrogram,
    logger
)
from plugins.core_services import (
    get_media_attributes,
    compress_media,
    compress_audio,
    compress_to_target_size,
    check_media_streams,
    resolve_thumbnail,
    extract_and_format_caption,
    schedule_deletion,
    download_media_with_auth_recovery
)

@Client.on_message(filters.private & filters.command(["autocompress", "auto_compress"]))
async def toggle_autocompress_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    u = await user_repo.get_or_create(user_id, message.from_user.first_name, message.from_user.username)
    new_state = not bool(u.get("auto_compress", False))
    await user_repo.update_user(user_id, {"auto_compress": new_state})
    state_txt = "🟢 ᴇɴᴀʙʟᴇᴅ" if new_state else "⚪ ᴅɪsᴀʙʟᴇᴅ"
    await message.reply_text(
        f"✦ **{to_smallcaps('auto-compressor mode')}** ✦\n\n"
        f"• 🗜️ **{to_smallcaps('status')}** : `{state_txt}`\n"
        f"• ⚙️ **{to_smallcaps('default preset')}** : `720p HD (Superfast CRF 28)`\n\n"
        f"💡 {to_smallcaps('when enabled, every video you send is automatically compressed with H.264 + custom thumbnail & caption!')}"
        f"{format_watermark()}"
    )

async def run_auto_compress_workflow(client: Client, media_msg: Message, user_id: int):
    status = await media_msg.reply_text(f"🗜️ **{to_smallcaps('auto-compressing video (720p hd superfast)...')}**", quote=True)
    await perform_compression_job(
        client=client,
        original_msg=media_msg,
        status=status,
        user_id=user_id,
        scale_h=720,
        crf=28,
        preset="superfast",
        is_target_mode=False,
        target_mb=None
    )

@Client.on_message(filters.private & filters.command("compress"))
async def compress_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document or target.audio):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video or audio file to compress.')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply to any media with')} `/compress` {to_smallcaps('or')} `/compress 100MB`"
            f"{format_watermark()}"
        )

    target_mb = None
    if len(message.command) > 1:
        arg = message.command[1].upper().replace("MB", "").replace("M", "").strip()
        try:
            target_mb = float(arg)
            if target_mb <= 0:
                target_mb = None
        except ValueError:
            target_mb = None

    if target_mb:
        await cache.set(f"comp_target_{message.from_user.id}_{target.id}", target_mb, ttl=600)

    await show_compression_menu(target, message, custom_target_mb=target_mb)

@Client.on_callback_query(filters.regex(r"^compress_menu_(\d+)"))
async def compress_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)
    await show_compression_menu(original_msg, query.message, is_callback=True)

async def show_compression_menu(media_msg: Message, target_msg: Message, is_callback: bool = False, custom_target_mb: float = None):
    msg_id = media_msg.id
    media = media_msg.video or media_msg.document or media_msg.audio
    raw_file_name = getattr(media, "file_name", None) or "video.mp4"
    file_name = raw_file_name.replace("`", "'")
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
        ]
    ]

    t_mb = custom_target_mb or await cache.get(f"comp_target_{target_msg.chat.id}_{msg_id}")
    if t_mb:
        btn.append([
            InlineKeyboardButton(f"🎯 ᴛᴀʀɢᴇᴛ sɪᴢᴇ: {int(t_mb)} ᴍʙ", callback_data=f"do_comptarget_{msg_id}_{int(t_mb)}")
        ])

    btn.append([
        InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")
    ])

    text = (
        f"✦ **{to_smallcaps('ffmpeg video compressor')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('current size')}** : `{file_size}`\n\n"
        f"💡 **{to_smallcaps('select your desired compression preset:')}**"
        f"{format_watermark()}"
    )
    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^do_comp(target)?_(\d+)_(\d+)(?:_(\d+)_([a-z]+))?"))
async def execute_compression(client: Client, query: CallbackQuery):
    is_target_mode = bool(query.matches[0].group(1))
    msg_id = int(query.matches[0].group(2))
    user_id = query.from_user.id

    if is_target_mode:
        target_mb = float(query.matches[0].group(3))
        scale_h = 720
        crf = 28
        preset = "veryfast"
    else:
        scale_h = int(query.matches[0].group(3))
        crf = int(query.matches[0].group(4))
        preset = query.matches[0].group(5)
        target_mb = None

    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("original media not found!"), show_alert=True)

    status = await query.message.edit_text(f"⏳ **{to_smallcaps('initializing compression workflow...')}**")
    await perform_compression_job(
        client=client,
        original_msg=original_msg,
        status=status,
        user_id=user_id,
        scale_h=scale_h,
        crf=crf,
        preset=preset,
        is_target_mode=is_target_mode,
        target_mb=target_mb
    )

async def perform_compression_job(
    client: Client,
    original_msg: Message,
    status: Message,
    user_id: int,
    scale_h: int,
    crf: int,
    preset: str,
    is_target_mode: bool = False,
    target_mb: float = None
):
    msg_id = original_msg.id
    media = original_msg.video or original_msg.document or original_msg.audio
    raw_name = getattr(media, "file_name", None) or f"video_{msg_id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_comp_{msg_id}_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    input_path = os.path.join(download_dir, clean_name)
    output_path = os.path.join(download_dir, f"compressed_{clean_name}")

    start_dl = time.time()
    try:
        await download_media_with_auth_recovery(
            client=client,
            message=original_msg,
            file_name=input_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading media", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    if not os.path.exists(input_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('file not found after download!')}**")

    stream_info = await check_media_streams(input_path)
    has_video = stream_info.get("has_video", False)
    has_audio = stream_info.get("has_audio", False)

    if not has_video and not has_audio:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ffmpeg compression failed')}**\n\n"
            f"⚠️ {to_smallcaps('this file has no audio or video stream that ffmpeg can decode.')}"
            f"{format_watermark()}"
        )

    orig_size = os.path.getsize(input_path)
    if has_video:
        # H.264/AAC is not valid in every source container, especially WebM
        # and some AVI/MKV files. Emit a broadly streamable MP4 instead.
        stem = sanitize_filename(os.path.splitext(clean_name)[0]) or f"video_{msg_id}"
        output_path = os.path.join(download_dir, f"compressed_{stem}.mp4")
    pre_attrs = await get_media_attributes(input_path)
    total_duration = getattr(media, "duration", 0) or int(pre_attrs.get("duration", 0))

    comp_start = time.time()
    if has_video:
        if is_target_mode and target_mb:
            await status.edit_text(f"🎯 **{to_smallcaps('ffmpeg target-size compression')} ({int(target_mb)} ᴍʙ)...**")
            success = await compress_to_target_size(
                input_path=input_path,
                output_path=output_path,
                target_size_mb=target_mb,
                duration_sec=total_duration,
                scale_height=scale_h
            )
        else:
            await status.edit_text(f"🗜️ **{to_smallcaps('ffmpeg compression in progress (h.264)...')}**")
            success = await compress_media(
                input_path=input_path,
                output_path=output_path,
                crf=crf,
                preset=preset,
                scale_height=scale_h,
                progress_message=status,
                total_duration=total_duration
            )
    else:
        await status.edit_text(f"🗜️ **{to_smallcaps('ffmpeg audio compression in progress...')}**")
        base_no_ext = os.path.splitext(output_path)[0]
        output_path = f"{base_no_ext}.m4a"
        success = await compress_audio(input_path, output_path)

    comp_duration = time.time() - comp_start

    if not success or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        clean_temp_files(input_path, output_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ffmpeg compression failed! please try another preset.')}**"
            f"{format_watermark()}"
        )

    comp_size = os.path.getsize(output_path)
    savings = round(((orig_size - comp_size) / orig_size) * 100, 2) if orig_size > 0 else 0

    attrs = await get_media_attributes(output_path)
    dur = int(attrs.get("duration", 0)) or total_duration
    thumb_path = await resolve_thumbnail(
        client=client,
        user_id=user_id,
        temp_dir=download_dir,
        video_path=output_path,
        duration=dur
    )
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    orig_caption = original_msg.caption or ""
    base_caption = await extract_and_format_caption(
        user_id=user_id,
        file_path=output_path,
        original_caption=orig_caption,
        file_id=str(msg_id)
    )

    stats_summary = (
        f"\n\n📊 **{to_smallcaps('compression stats')}** :\n"
        f"• 📦 **{to_smallcaps('original')}** : `{humanbytes(orig_size)}` ➔ `{humanbytes(comp_size)}`\n"
        f"• 📉 **{to_smallcaps('saved')}** : `{savings}%` | ⏱️ `{time_formatter(seconds=round(comp_duration))}`"
    )
    final_caption = base_caption + stats_summary
    if len(final_caption) > 1024:
        final_caption = final_caption[:1020] + "..."

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('uploading compressed media...')}**")

    sent_video = None
    try:
        if has_video:
            w = int(attrs.get("width", 1280)) or 1280
            h = int(attrs.get("height", 720)) or 720
            try:
                sent_video = await client.send_video(
                    chat_id=status.chat.id,
                    video=output_path,
                    caption=final_caption,
                    duration=dur,
                    width=w,
                    height=h,
                    thumb=thumb_path,
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=("📤 uploading video", status, upload_start)
                )
            except Exception:
                sent_video = await client.send_document(
                    chat_id=status.chat.id,
                    document=output_path,
                    caption=final_caption,
                    thumb=thumb_path,
                    force_document=True,
                    progress=progress_for_pyrogram,
                    progress_args=("📤 uploading document", status, upload_start)
                )
        else:
            sent_video = await client.send_audio(
                chat_id=status.chat.id,
                audio=output_path,
                caption=final_caption,
                duration=dur,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 uploading audio", status, upload_start)
            )
    except Exception as e:
        clean_temp_files(input_path, output_path, thumb_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('upload failed')}** : `{e}`")

    clean_temp_files(input_path, output_path, thumb_path, download_dir)
    try:
        await status.delete()
    except Exception:
        pass

    u = await user_repo.get_user(user_id)
    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_video:
        await schedule_deletion(sent_video.chat.id, sent_video.id, del_time)
