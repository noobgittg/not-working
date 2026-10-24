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
    get_detailed_mediainfo,
    extract_all_audio_tracks,
    extract_all_subtitle_tracks,
    add_audio_to_video,
    add_subtitle_to_video,
    trim_video,
    parse_time_range,
    resolve_thumbnail,
    format_caption,
    schedule_deletion
)

MAX_BOT_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MiB limit

@Client.on_message(filters.private & filters.command(["pro", "filepro", "advance", "tools"]))
async def file_pro_command_entry(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document or target.audio):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video, audio or document file!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply to any media with')} `/pro`"
            f"{format_watermark()}"
        )
    await show_file_pro_menu(target, message)

@Client.on_callback_query(filters.regex(r"^pro_menu_(\d+)"))
async def file_pro_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("media no longer exists!"), show_alert=True)
    await show_file_pro_menu(original_msg, query.message, is_callback=True)

async def show_file_pro_menu(media_msg: Message, target_msg: Message, is_callback: bool = False):
    msg_id = media_msg.id
    media = media_msg.video or media_msg.document or media_msg.audio
    file_name = getattr(media, "file_name", None) or f"media_{msg_id}"
    file_size_bytes = getattr(media, "file_size", 0)
    file_size = humanbytes(file_size_bytes)
    dur = getattr(media, "duration", 0)
    dur_str = time_formatter(seconds=dur) if dur > 0 else "N/A"

    text = (
        f"✦ **{to_smallcaps('file pro media studio')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('file size')}** : `{file_size}`\n"
        f"• ⏱️ **{to_smallcaps('duration')}** : `{dur_str}`\n\n"
        f"💡 **{to_smallcaps('choose a file pro advance feature below:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('mediainfo')}", callback_data=f"pro_mediainfo_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"🎵 {to_smallcaps('extract all audio')}", callback_data=f"pro_extaudio_{msg_id}"),
            InlineKeyboardButton(f"💬 {to_smallcaps('extract all subtitle')}", callback_data=f"pro_extsub_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"➕🎵 {to_smallcaps('add audio')}", callback_data=f"pro_addaudio_ask_{msg_id}"),
            InlineKeyboardButton(f"➕💬 {to_smallcaps('add subtitle')}", callback_data=f"pro_addsub_ask_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"✂️ {to_smallcaps('trim video')}", callback_data=f"pro_trim_ask_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data=f"back_to_media_{msg_id}"),
            InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")
        ]
    ]

    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

@Client.on_callback_query(filters.regex(r"^back_to_media_(\d+)"))
async def back_to_media_handler(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    from plugins.rename import incoming_file_entry
    original = await client.get_messages(query.message.chat.id, msg_id)
    if original and original.media:
        await query.message.delete()
        await incoming_file_entry(client, original)
    else:
        await query.answer(to_smallcaps("media not found!"), show_alert=True)

# ==================== 1. MEDIAINFO ====================

@Client.on_callback_query(filters.regex(r"^pro_mediainfo_(\d+)"))
async def pro_mediainfo_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)

    status = await query.message.edit_text(f"🔍 **{to_smallcaps('generating detailed mediainfo...')}**")

    media = original.video or original.document or original.audio
    raw_name = getattr(media, "file_name", None) or f"media_{msg_id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{query.from_user.id}_info_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    temp_path = os.path.join(download_dir, clean_name)

    try:
        await original.download(
            file_name=temp_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading header", status, time.time())
        )
    except Exception as e:
        clean_temp_files(temp_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    info = await get_detailed_mediainfo(temp_path)
    clean_temp_files(temp_path, download_dir)

    if not info:
        return await status.edit_text(f"❌ **{to_smallcaps('failed to extract media information.')}**")

    txt = f"✦ **{to_smallcaps('media information')}** ✦\n\n"
    txt += f"• 📁 **{to_smallcaps('file name')}** : `{clean_name}`\n"
    txt += f"• 📦 **{to_smallcaps('file size')}** : `{humanbytes(info.get('size', 0))}`\n"
    txt += f"• ⏱️ **{to_smallcaps('duration')}** : `{time_formatter(seconds=info.get('duration', 0))}`\n"
    txt += f"• 🏷️ **{to_smallcaps('container')}** : `{info.get('container', 'Unknown')}`\n"
    if info.get('bitrate'):
        txt += f"• 🚀 **{to_smallcaps('bitrate')}** : `{humanbytes(info['bitrate'])}/s`\n"

    v_streams = info.get("video_streams", [])
    if v_streams:
        txt += f"\n🎬 **{to_smallcaps('video streams')}** (`{len(v_streams)}`):\n"
        for i, v in enumerate(v_streams, 1):
            txt += (
                f"  `#{i}` • **{v['codec']}** ({v['profile']}) | "
                f"`{v['width']}x{v['height']}` ({v['aspect_ratio']}) | "
                f"`{v['pix_fmt']}` | `{v['r_frame_rate']} fps`\n"
            )

    a_streams = info.get("audio_streams", [])
    if a_streams:
        txt += f"\n🎵 **{to_smallcaps('audio streams')}** (`{len(a_streams)}`):\n"
        for i, a in enumerate(a_streams, 1):
            lang_label = a.get('language') or a.get('lang') or a.get('lang_code', 'UND')
            txt += (
                f"  `#{i}` • **{a['codec']}** | {a['channels']}ch ({a['channel_layout']}) | "
                f"`{a['sample_rate']}Hz` | Lang: `{str(lang_label).upper()}` | Title: `{a['title']}`\n"
            )

    s_streams = info.get("subtitle_streams", [])
    if s_streams:
        txt += f"\n💬 **{to_smallcaps('subtitle streams')}** (`{len(s_streams)}`):\n"
        for i, s in enumerate(s_streams, 1):
            lang_label = s.get('language') or s.get('lang') or s.get('lang_code', 'UND')
            txt += f"  `#{i}` • **{s['codec']}** | Lang: `{str(lang_label).upper()}` | Title: `{s['title']}`\n"

    txt += format_watermark()

    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back to menu')}", callback_data=f"pro_menu_{msg_id}")]]

    if len(txt) <= 4000:
        await status.edit_text(txt, reply_markup=InlineKeyboardMarkup(btn))
    else:
        doc_path = os.path.join(Config.DOWNLOAD_DIR, f"Mediainfo_{clean_name}.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(txt.replace("**", "").replace("`", ""))
        await query.message.reply_document(
            document=doc_path,
            caption=f"📊 **{to_smallcaps('full mediainfo report')}** : `{clean_name}`{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        clean_temp_files(doc_path)
        await status.delete()

# ==================== 2. EXTRACT ALL AUDIO ====================

@Client.on_message(filters.private & filters.command(["extractaudio", "extaudio"]))
async def extract_audio_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video to extract audio!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply with')} `/extractaudio`"
            f"{format_watermark()}"
        )
    await run_extract_all_audio(client, target, message)

@Client.on_callback_query(filters.regex(r"^pro_extaudio_(\d+)"))
async def pro_extaudio_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)
    await run_extract_all_audio(client, original, query.message, is_callback=True)

async def run_extract_all_audio(client: Client, media_msg: Message, target_msg: Message, is_callback: bool = False):
    status = await (target_msg.edit_text if is_callback else target_msg.reply_text)(
        f"⏳ **{to_smallcaps('initializing audio extraction...')}**"
    )

    media = media_msg.video or media_msg.document
    raw_name = getattr(media, "file_name", None) or f"video_{media_msg.id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    uid = media_msg.from_user.id if media_msg.from_user else target_msg.chat.id
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{uid}_extaud_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    video_path = os.path.join(download_dir, clean_name)

    start_dl = time.time()
    try:
        await media_msg.download(
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading video", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    await status.edit_text(f"🎵 **{to_smallcaps('extracting all audio tracks...')}**")
    tracks = await extract_all_audio_tracks(video_path, download_dir)

    if not tracks:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('no audio streams found in this video!')}**"
            f"{format_watermark()}"
        )

    await status.edit_text(f"📤 **{to_smallcaps('uploading')}** `{len(tracks)}` **{to_smallcaps('audio track(s)...')}**")

    for t in tracks:
        track_path = t["path"]
        caption = (
            f"🎵 **{to_smallcaps('audio track')}** `#{t['index']}`\n\n"
            f"• 🏷️ **{to_smallcaps('language')}** : `{t['language'].upper()}`\n"
            f"• 🎼 **{to_smallcaps('title')}** : `{t['title']}`\n"
            f"• 🎚️ **{to_smallcaps('codec')}** : `{t['codec']}`\n"
            f"• 📦 **{to_smallcaps('size')}** : `{humanbytes(os.path.getsize(track_path))}`"
            f"{format_watermark()}"
        )
        try:
            await client.send_audio(
                chat_id=target_msg.chat.id,
                audio=track_path,
                caption=caption[:1020] + "..." if len(caption) > 1024 else caption,
                duration=t["duration"],
                title=f"{t['title']} ({t['language'].upper()})",
                performer=Config.WATERMARK
            )
        except Exception as e:
            logger.error(f"Failed to upload audio track: {e}")

    clean_temp_files(video_path, download_dir)
    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back to menu')}", callback_data=f"pro_menu_{media_msg.id}")]]
    await status.edit_text(
        f"✅ **{to_smallcaps('successfully extracted')}** `{len(tracks)}` **{to_smallcaps('audio track(s)!')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ==================== 3. EXTRACT ALL SUBTITLE ====================

@Client.on_message(filters.private & filters.command(["extractsub", "extsub"]))
async def extract_sub_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video to extract subtitles!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply with')} `/extractsub`"
            f"{format_watermark()}"
        )
    await run_extract_all_sub(client, target, message)

@Client.on_callback_query(filters.regex(r"^pro_extsub_(\d+)"))
async def pro_extsub_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)
    await run_extract_all_sub(client, original, query.message, is_callback=True)

async def run_extract_all_sub(client: Client, media_msg: Message, target_msg: Message, is_callback: bool = False):
    status = await (target_msg.edit_text if is_callback else target_msg.reply_text)(
        f"⏳ **{to_smallcaps('initializing subtitle extraction...')}**"
    )

    media = media_msg.video or media_msg.document
    raw_name = getattr(media, "file_name", None) or f"video_{media_msg.id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    uid = media_msg.from_user.id if media_msg.from_user else target_msg.chat.id
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{uid}_extsub_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    video_path = os.path.join(download_dir, clean_name)

    start_dl = time.time()
    try:
        await media_msg.download(
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading video", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    await status.edit_text(f"💬 **{to_smallcaps('extracting all subtitle tracks...')}**")
    tracks = await extract_all_subtitle_tracks(video_path, download_dir)

    if not tracks:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('no subtitle streams found in this video!')}**"
            f"{format_watermark()}"
        )

    await status.edit_text(f"📤 **{to_smallcaps('uploading')}** `{len(tracks)}` **{to_smallcaps('subtitle track(s)...')}**")

    for t in tracks:
        sub_path = t["path"]
        caption = (
            f"💬 **{to_smallcaps('subtitle track')}** `#{t['index']}`\n\n"
            f"• 🏷️ **{to_smallcaps('language')}** : `{t['language'].upper()}`\n"
            f"• 📝 **{to_smallcaps('title')}** : `{t['title']}`\n"
            f"• 🔤 **{to_smallcaps('format')}** : `{t['codec']}`"
            f"{format_watermark()}"
        )
        try:
            await client.send_document(
                chat_id=target_msg.chat.id,
                document=sub_path,
                caption=caption[:1020] + "..." if len(caption) > 1024 else caption,
                file_name=os.path.basename(sub_path)
            )
        except Exception as e:
            logger.error(f"Failed to upload subtitle file: {e}")

    clean_temp_files(video_path, download_dir)
    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back to menu')}", callback_data=f"pro_menu_{media_msg.id}")]]
    await status.edit_text(
        f"✅ **{to_smallcaps('successfully extracted')}** `{len(tracks)}` **{to_smallcaps('subtitle track(s)!')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ==================== 4. ADD AUDIO ====================

@Client.on_message(filters.private & filters.command("addaudio"))
async def add_audio_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video to add audio!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply with')} `/addaudio`"
            f"{format_watermark()}"
        )
    await prompt_add_audio(client, message.chat.id, target.id)

@Client.on_callback_query(filters.regex(r"^pro_addaudio_ask_(\d+)"))
async def pro_addaudio_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    await query.message.delete()
    await prompt_add_audio(client, query.message.chat.id, msg_id)

async def prompt_add_audio(client: Client, chat_id: int, video_msg_id: int):
    await client.send_message(
        chat_id=chat_id,
        text=(
            f"🎵 **{to_smallcaps('add audio to video')}** ✦\n\n"
            f"💬 {to_smallcaps('please reply to this message with the audio file (.mp3, .m4a, .aac, .wav) you want to add.')}\n\n"
            f"💡 {to_smallcaps('send')} `/cancel` {to_smallcaps('to abort.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("send or reply with audio file..."))
    )
    await cache.set(f"waiting_addaudio_{chat_id}", video_msg_id, ttl=300)

@Client.on_callback_query(filters.regex(r"^pro_addaud_mode_(\d+)_(\d+)_(add|replace)"))
async def execute_add_audio(client: Client, query: CallbackQuery):
    video_id = int(query.matches[0].group(1))
    audio_id = int(query.matches[0].group(2))
    mode = query.matches[0].group(3)
    replace = (mode == "replace")
    user_id = query.from_user.id

    status = await query.message.edit_text(f"⏳ **{to_smallcaps('initializing audio muxing...')}**")

    video_msg = await client.get_messages(query.message.chat.id, video_id)
    audio_msg = await client.get_messages(query.message.chat.id, audio_id)

    if not video_msg or not audio_msg:
        return await status.edit_text(f"❌ **{to_smallcaps('media no longer exists!')}**")

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_addaud_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)

    v_media = video_msg.video or video_msg.document
    a_media = audio_msg.audio or audio_msg.voice or audio_msg.document

    v_name = sanitize_filename(getattr(v_media, "file_name", "video.mp4"))
    a_name = sanitize_filename(getattr(a_media, "file_name", "audio.mp3"))

    v_path = os.path.join(download_dir, v_name)
    a_path = os.path.join(download_dir, a_name)
    out_name = f"muxed_{os.path.splitext(v_name)[0]}.mkv"
    out_path = os.path.join(download_dir, out_name)

    try:
        await video_msg.download(
            file_name=v_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading video", status, time.time())
        )
        await audio_msg.download(
            file_name=a_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading audio", status, time.time())
        )
    except Exception as e:
        clean_temp_files(v_path, a_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    await status.edit_text(f"🎛️ **{to_smallcaps('muxing audio track into video...')}**")
    success = await add_audio_to_video(v_path, a_path, out_path, replace_existing=replace)

    if not success or not os.path.exists(out_path):
        clean_temp_files(v_path, a_path, out_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('audio muxing failed!')}**{format_watermark()}")

    out_size = os.path.getsize(out_path)
    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('audio muxed successfully!')}**\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('file size')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('duration')}** : `{time_formatter(seconds=dur)}`\n"
        f"• 🎚️ **{to_smallcaps('mode')}** : `{'REPLACE EXISTING' if replace else 'ADD NEW TRACK'}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('uploading video with new audio...')}**")

    try:
        await client.send_video(
            chat_id=query.message.chat.id,
            video=out_path,
            caption=caption[:1020] + "..." if len(caption) > 1024 else caption,
            duration=dur,
            width=int(attrs.get("width", 1280)) or 1280,
            height=int(attrs.get("height", 720)) or 720,
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 uploading video", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('upload failed')}** : `{e}`")

    clean_temp_files(download_dir)
    try:
        await status.delete()
    except Exception:
        pass

# ==================== 5. ADD SUBTITLE ====================

@Client.on_message(filters.private & filters.command("addsub"))
async def add_sub_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video to add subtitles!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply with')} `/addsub`"
            f"{format_watermark()}"
        )
    await prompt_add_sub(client, message.chat.id, target.id)

@Client.on_callback_query(filters.regex(r"^pro_addsub_ask_(\d+)"))
async def pro_addsub_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    await query.message.delete()
    await prompt_add_sub(client, query.message.chat.id, msg_id)

async def prompt_add_sub(client: Client, chat_id: int, video_msg_id: int):
    await client.send_message(
        chat_id=chat_id,
        text=(
            f"💬 **{to_smallcaps('add subtitle to video')}** ✦\n\n"
            f"💬 {to_smallcaps('please reply to this message with your subtitle file (.srt, .ass, .vtt).')}\n\n"
            f"💡 {to_smallcaps('send')} `/cancel` {to_smallcaps('to abort.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("send or reply with subtitle file..."))
    )
    await cache.set(f"waiting_addsub_{chat_id}", video_msg_id, ttl=300)

async def execute_add_subtitle(client: Client, reply_msg: Message, video_id: int, sub_msg: Message):
    status = await reply_msg.reply_text(f"⏳ **{to_smallcaps('initializing subtitle muxing...')}**")
    user_id = reply_msg.from_user.id

    video_msg = await client.get_messages(reply_msg.chat.id, video_id)
    if not video_msg or not video_msg.media:
        return await status.edit_text(f"❌ **{to_smallcaps('video message no longer exists!')}**")

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_addsub_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)

    v_media = video_msg.video or video_msg.document
    s_media = sub_msg.document

    v_name = sanitize_filename(getattr(v_media, "file_name", "video.mp4"))
    s_name = sanitize_filename(getattr(s_media, "file_name", "sub.srt"))

    v_path = os.path.join(download_dir, v_name)
    s_path = os.path.join(download_dir, s_name)
    out_name = f"subbed_{os.path.splitext(v_name)[0]}.mkv"
    out_path = os.path.join(download_dir, out_name)

    try:
        await video_msg.download(
            file_name=v_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading video", status, time.time())
        )
        await sub_msg.download(
            file_name=s_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading subtitle", status, time.time())
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    await status.edit_text(f"💬 **{to_smallcaps('soft-muxing subtitle into video...')}**")
    success = await add_subtitle_to_video(v_path, s_path, out_path)

    if not success or not os.path.exists(out_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('subtitle muxing failed!')}**")

    out_size = os.path.getsize(out_path)
    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('subtitle muxed successfully!')}**\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('file size')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('duration')}** : `{time_formatter(seconds=dur)}`\n"
        f"• 💬 **{to_smallcaps('subtitle file')}** : `{s_name}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('uploading video with subtitle...')}**")

    try:
        await client.send_video(
            chat_id=reply_msg.chat.id,
            video=out_path,
            caption=caption[:1020] + "..." if len(caption) > 1024 else caption,
            duration=dur,
            width=int(attrs.get("width", 1280)) or 1280,
            height=int(attrs.get("height", 720)) or 720,
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 uploading video", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('upload failed')}** : `{e}`")

    clean_temp_files(download_dir)
    try:
        await status.delete()
    except Exception:
        pass

# ==================== 6. TRIM VIDEO ====================

@Client.on_message(filters.private & filters.command("trim"))
async def trim_video_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video to trim!')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply with')} `/trim`"
            f"{format_watermark()}"
        )
    await prompt_trim(client, message.chat.id, target.id)

@Client.on_callback_query(filters.regex(r"^pro_trim_ask_(\d+)"))
async def pro_trim_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    await query.message.delete()
    await prompt_trim(client, query.message.chat.id, msg_id)

async def prompt_trim(client: Client, chat_id: int, video_msg_id: int):
    await client.send_message(
        chat_id=chat_id,
        text=(
            f"✂️ **{to_smallcaps('trim video segment')}** ✦\n\n"
            f"💬 {to_smallcaps('please reply to this message with start and end time.')}\n\n"
            f"• **{to_smallcaps('format')}** : `HH:MM:SS HH:MM:SS`\n"
            f"• **{to_smallcaps('example')} 1** : `00:01:30 00:05:00`\n"
            f"• **{to_smallcaps('example')} 2** : `01:30 to 05:00`\n"
            f"• **{to_smallcaps('example')} 3** : `90 300`\n\n"
            f"💡 {to_smallcaps('send')} `/cancel` {to_smallcaps('to abort.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("e.g. 00:01:30 00:05:00"))
    )
    await cache.set(f"waiting_trim_{chat_id}", video_msg_id, ttl=300)

async def execute_trim_video(client: Client, reply_msg: Message, video_id: int, time_text: str):
    start_sec, end_sec = parse_time_range(time_text)
    if start_sec is None or end_sec is None or end_sec <= start_sec:
        return await reply_msg.reply_text(
            f"⚠️ **{to_smallcaps('invalid time range!')}**\n\n"
            f"• **{to_smallcaps('format')}** : `HH:MM:SS HH:MM:SS`\n"
            f"• **{to_smallcaps('example')}** : `00:01:30 00:05:00`"
            f"{format_watermark()}"
        )

    status = await reply_msg.reply_text(f"⏳ **{to_smallcaps('initializing video trim...')}**")
    user_id = reply_msg.from_user.id

    video_msg = await client.get_messages(reply_msg.chat.id, video_id)
    if not video_msg or not video_msg.media:
        return await status.edit_text(f"❌ **{to_smallcaps('video message no longer exists!')}**")

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_trim_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)

    v_media = video_msg.video or video_msg.document
    raw_name = sanitize_filename(getattr(v_media, "file_name", "video.mp4"))
    base_name, ext = os.path.splitext(raw_name)

    v_path = os.path.join(download_dir, raw_name)
    out_name = f"trimmed_{base_name}_{int(start_sec)}s_{int(end_sec)}s{ext or '.mp4'}"
    out_path = os.path.join(download_dir, out_name)

    try:
        await video_msg.download(
            file_name=v_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading video", status, time.time())
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    await status.edit_text(f"✂️ **{to_smallcaps('trimming video segment (stream copy)...')}**")
    success = await trim_video(v_path, out_path, start_sec, end_sec)

    if not success or not os.path.exists(out_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('video trim failed!')}**")

    out_size = os.path.getsize(out_path)
    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('video trimmed successfully!')}**\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('file size')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('segment')}** : `{time_formatter(seconds=int(start_sec))}` ➔ `{time_formatter(seconds=int(end_sec))}`\n"
        f"• ⏱️ **{to_smallcaps('total length')}** : `{time_formatter(seconds=dur)}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('uploading trimmed video...')}**")

    try:
        await client.send_video(
            chat_id=reply_msg.chat.id,
            video=out_path,
            caption=caption[:1020] + "..." if len(caption) > 1024 else caption,
            duration=dur,
            width=int(attrs.get("width", 1280)) or 1280,
            height=int(attrs.get("height", 720)) or 720,
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 uploading video", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('upload failed')}** : `{e}`")

    clean_temp_files(download_dir)
    try:
        await status.delete()
    except Exception:
        pass

# ==================== FORCEREPLY MEDIA DISPATCHER ====================

@Client.on_message(filters.private & filters.reply & (filters.audio | filters.voice | filters.document))
async def file_pro_force_reply_media_listener(client: Client, message: Message):
    user_id = message.from_user.id

    aud_video_id = await cache.get(f"waiting_addaudio_{user_id}")
    if aud_video_id:
        await cache.delete(f"waiting_addaudio_{user_id}")
        if not (message.audio or message.voice or (message.document and message.document.mime_type and "audio" in message.document.mime_type)):
            return await message.reply_text(
                f"❌ **{to_smallcaps('no valid audio file received!')}**\n\n"
                f"{to_smallcaps('please send a valid audio file (.mp3, .m4a, .aac, .wav).')}"
                f"{format_watermark()}"
            )
        btn = [
            [
                InlineKeyboardButton(f"➕ {to_smallcaps('add as new track')}", callback_data=f"pro_addaud_mode_{aud_video_id}_{message.id}_add"),
                InlineKeyboardButton(f"🔄 {to_smallcaps('replace audio')}", callback_data=f"pro_addaud_mode_{aud_video_id}_{message.id}_replace")
            ],
            [
                InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")
            ]
        ]
        return await message.reply_text(
            f"✦ **{to_smallcaps('select audio mode')}** ✦\n\n"
            f"• 🎵 **{to_smallcaps('audio')}** : `{getattr(message.audio or message.document, 'file_name', 'audio.mp3')}`\n\n"
            f"💡 **{to_smallcaps('choose how to mux this audio into your video:')}**"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    sub_video_id = await cache.get(f"waiting_addsub_{user_id}")
    if sub_video_id:
        await cache.delete(f"waiting_addsub_{user_id}")
        if not (message.document and (message.document.file_name or "").lower().endswith((".srt", ".ass", ".vtt", ".sub"))):
            return await message.reply_text(
                f"❌ **{to_smallcaps('no valid subtitle file received!')}**\n\n"
                f"{to_smallcaps('please send a valid .srt, .ass, or .vtt subtitle file.')}"
                f"{format_watermark()}"
            )
        return await execute_add_subtitle(client, message, sub_video_id, message)
