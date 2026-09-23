import os
import time
import secrets
from typing import Optional
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
from app.services.ffmpeg_service import (
    get_media_attributes,
    get_detailed_mediainfo,
    extract_all_audio_tracks,
    extract_all_subtitle_tracks,
    add_audio_to_video,
    add_subtitle_to_video,
    trim_video,
    parse_time_range
)
from app.services.thumb_service import resolve_thumbnail
from app.services.caption_service import format_caption
from app.services.autodel_service import schedule_deletion

MAX_BOT_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MiB limit

# ==================== MENU & COMMAND ENTRYPOINTS ====================

@Client.on_message(filters.private & filters.command(["pro", "filepro", "advance", "tools"]))
async def file_pro_command_entry(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document or target.audio):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ, ᴀᴜᴅɪᴏ ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ ғɪʟᴇ!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇᴅɪᴀ ᴡɪᴛʜ')} `/pro`"
            f"{format_watermark()}"
        )
    await show_file_pro_menu(target, message)

@Client.on_callback_query(filters.regex(r"^pro_menu_(\d+)"))
async def file_pro_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!"), show_alert=True)
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
        f"✦ **{to_smallcaps('sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ:')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{file_size}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{dur_str}`\n\n"
        f"💡 **{to_smallcaps('ᴄʜᴏᴏsᴇ ᴀ ғɪʟᴇ ᴘʀᴏ ᴀᴅᴠᴀɴᴄᴇ ғᴇᴀᴛᴜʀᴇ ʙᴇʟᴏᴡ:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('ᴍᴇᴅɪᴀɪɴғᴏ')}", callback_data=f"pro_mediainfo_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"🎵 {to_smallcaps('ᴇxᴛʀᴀᴄᴛ ᴀʟʟ ᴀᴜᴅɪᴏ')}", callback_data=f"pro_extaudio_{msg_id}"),
            InlineKeyboardButton(f"💬 {to_smallcaps('ᴇxᴛʀᴀᴄᴛ ᴀʟʟ sᴜʙᴛɪᴛʟᴇ')}", callback_data=f"pro_extsub_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"➕🎵 {to_smallcaps('ᴀᴅᴅ ᴀᴜᴅɪᴏ')}", callback_data=f"pro_addaudio_ask_{msg_id}"),
            InlineKeyboardButton(f"➕💬 {to_smallcaps('ᴀᴅᴅ sᴜʙᴛɪᴛʟᴇ')}", callback_data=f"pro_addsub_ask_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"✂️ {to_smallcaps('ᴛʀɪᴍ ᴠɪᴅᴇᴏ')}", callback_data=f"pro_trim_ask_{msg_id}")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data=f"back_to_media_{msg_id}"),
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
        ]
    ]

    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

@Client.on_callback_query(filters.regex(r"^back_to_media_(\d+)"))
async def back_to_media_handler(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    from app.bot.handlers.rename import incoming_file_entry
    original = await client.get_messages(query.message.chat.id, msg_id)
    if original and original.media:
        await query.message.delete()
        await incoming_file_entry(client, original)
    else:
        await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

# ==================== 1. MEDIAINFO ====================

@Client.on_callback_query(filters.regex(r"^pro_mediainfo_(\d+)"))
async def pro_mediainfo_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    status = await query.message.edit_text(f"🔍 **{to_smallcaps('ɢᴇɴᴇʀᴀᴛɪɴɢ ᴅᴇᴛᴀɪʟᴇᴅ ᴍᴇᴅɪᴀɪɴғᴏ...')}**")

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
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ʜᴇᴀᴅᴇʀ", status, time.time())
        )
    except Exception as e:
        clean_temp_files(temp_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    info = await get_detailed_mediainfo(temp_path)
    clean_temp_files(temp_path, download_dir)

    if not info:
        return await status.edit_text(f"❌ **{to_smallcaps('ғᴀɪʟᴇᴅ ᴛᴏ ᴇxᴛʀᴀᴄᴛ ᴍᴇᴅɪᴀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ.')}**")

    # Format human-friendly Mediainfo
    txt = f"✦ **{to_smallcaps('ᴍᴇᴅɪᴀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}** ✦\n\n"
    txt += f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{clean_name}`\n"
    txt += f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(info.get('size', 0))}`\n"
    txt += f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{time_formatter(seconds=info.get('duration', 0))}`\n"
    txt += f"• 🏷️ **{to_smallcaps('ᴄᴏɴᴛᴀɪɴᴇʀ')}** : `{info.get('container', 'Unknown')}`\n"
    if info.get('bitrate'):
        txt += f"• 🚀 **{to_smallcaps('ʙɪᴛʀᴀᴛᴇ')}** : `{humanbytes(info['bitrate'])}/s`\n"

    # Video streams
    v_streams = info.get("video_streams", [])
    if v_streams:
        txt += f"\n🎬 **{to_smallcaps('ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍs')}** (`{len(v_streams)}`):\n"
        for i, v in enumerate(v_streams, 1):
            txt += (
                f"  `#{i}` • **{v['codec']}** ({v['profile']}) | "
                f"`{v['width']}x{v['height']}` ({v['aspect_ratio']}) | "
                f"`{v['pix_fmt']}` | `{v['r_frame_rate']} fps`\n"
            )

    # Audio streams
    a_streams = info.get("audio_streams", [])
    if a_streams:
        txt += f"\n🎵 **{to_smallcaps('ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍs')}** (`{len(a_streams)}`):\n"
        for i, a in enumerate(a_streams, 1):
            txt += (
                f"  `#{i}` • **{a['codec']}** | {a['channels']}ch ({a['channel_layout']}) | "
                f"`{a['sample_rate']}Hz` | Lang: `{a['lang'].upper()}` | Title: `{a['title']}`\n"
            )

    # Subtitle streams
    s_streams = info.get("subtitle_streams", [])
    if s_streams:
        txt += f"\n💬 **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ sᴛʀᴇᴀᴍs')}** (`{len(s_streams)}`):\n"
        for i, s in enumerate(s_streams, 1):
            txt += f"  `#{i}` • **{s['codec']}** | Lang: `{s['lang'].upper()}` | Title: `{s['title']}`\n"

    txt += format_watermark()

    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ')}", callback_data=f"pro_menu_{msg_id}")]]

    if len(txt) <= 4000:
        await status.edit_text(txt, reply_markup=InlineKeyboardMarkup(btn))
    else:
        # Write to txt file if too large for Telegram message limit
        doc_path = f"downloads/Mediainfo_{clean_name}.txt"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(txt.replace("**", "").replace("`", ""))
        await query.message.reply_document(
            document=doc_path,
            caption=f"📊 **{to_smallcaps('ғᴜʟʟ ᴍᴇᴅɪᴀɪɴғᴏ ʀᴇᴘᴏʀᴛ')}** : `{clean_name}`{format_watermark()}",
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
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴇxᴛʀᴀᴄᴛ ᴀᴜᴅɪᴏ!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴡɪᴛʜ')} `/extractaudio`"
            f"{format_watermark()}"
        )
    await run_extract_all_audio(client, target, message)

@Client.on_callback_query(filters.regex(r"^pro_extaudio_(\d+)"))
async def pro_extaudio_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await run_extract_all_audio(client, original, query.message, is_callback=True)

async def run_extract_all_audio(client: Client, media_msg: Message, target_msg: Message, is_callback: bool = False):
    status = await (target_msg.edit_text if is_callback else target_msg.reply_text)(
        f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴀᴜᴅɪᴏ ᴇxᴛʀᴀᴄᴛɪᴏɴ...')}**"
    )

    media = media_msg.video or media_msg.document
    raw_name = getattr(media, "file_name", None) or f"video_{media_msg.id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{media_msg.from_user.id}_extaud_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    video_path = os.path.join(download_dir, clean_name)

    start_dl = time.time()
    try:
        await media_msg.download(
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    await status.edit_text(f"🎵 **{to_smallcaps('ᴇxᴛʀᴀᴄᴛɪɴɢ ᴀʟʟ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋs...')}**")
    tracks = await extract_all_audio_tracks(video_path, download_dir)

    if not tracks:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ɴᴏ ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍs ғᴏᴜɴᴅ ɪɴ ᴛʜɪs ᴠɪᴅᴇᴏ!')}**"
            f"{format_watermark()}"
        )

    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ')}** `{len(tracks)}` **{to_smallcaps('ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋ(s)...')}**")

    for t in tracks:
        track_path = t["path"]
        caption = (
            f"🎵 **{to_smallcaps('ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋ')}** `#{t['index']}`\n\n"
            f"• 🏷️ **{to_smallcaps('ʟᴀɴɢᴜᴀɢᴇ')}** : `{t['language'].upper()}`\n"
            f"• 🎼 **{to_smallcaps('ᴛɪᴛʟᴇ')}** : `{t['title']}`\n"
            f"• 🎚️ **{to_smallcaps('ᴄᴏᴅᴇᴄ')}** : `{t['codec']}`\n"
            f"• 📦 **{to_smallcaps('sɪᴢᴇ')}** : `{humanbytes(os.path.getsize(track_path))}`"
            f"{format_watermark()}"
        )
        try:
            await client.send_audio(
                chat_id=target_msg.chat.id,
                audio=track_path,
                caption=caption,
                duration=t["duration"],
                title=f"{t['title']} ({t['language'].upper()})",
                performer=Config.WATERMARK
            )
        except Exception as e:
            logger.error(f"Failed to upload audio track: {e}")

    clean_temp_files(video_path, download_dir)
    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ')}", callback_data=f"pro_menu_{media_msg.id}")]]
    await status.edit_text(
        f"✅ **{to_smallcaps('sᴜᴄᴄᴇssғᴜʟʟʏ ᴇxᴛʀᴀᴄᴛᴇᴅ')}** `{len(tracks)}` **{to_smallcaps('ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋ(s)!')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ==================== 3. EXTRACT ALL SUBTITLE ====================

@Client.on_message(filters.private & filters.command(["extractsub", "extsub"]))
async def extract_sub_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴇxᴛʀᴀᴄᴛ sᴜʙᴛɪᴛʟᴇs!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴡɪᴛʜ')} `/extractsub`"
            f"{format_watermark()}"
        )
    await run_extract_all_sub(client, target, message)

@Client.on_callback_query(filters.regex(r"^pro_extsub_(\d+)"))
async def pro_extsub_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await run_extract_all_sub(client, original, query.message, is_callback=True)

async def run_extract_all_sub(client: Client, media_msg: Message, target_msg: Message, is_callback: bool = False):
    status = await (target_msg.edit_text if is_callback else target_msg.reply_text)(
        f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ sᴜʙᴛɪᴛʟᴇ ᴇxᴛʀᴀᴄᴛɪᴏɴ...')}**"
    )

    media = media_msg.video or media_msg.document
    raw_name = getattr(media, "file_name", None) or f"video_{media_msg.id}.mp4"
    clean_name = sanitize_filename(raw_name)

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{media_msg.from_user.id}_extsub_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    video_path = os.path.join(download_dir, clean_name)

    start_dl = time.time()
    try:
        await media_msg.download(
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    await status.edit_text(f"💬 **{to_smallcaps('ᴇxᴛʀᴀᴄᴛɪɴɢ ᴀʟʟ sᴜʙᴛɪᴛʟᴇ ᴛʀᴀᴄᴋs...')}**")
    tracks = await extract_all_subtitle_tracks(video_path, download_dir)

    if not tracks:
        clean_temp_files(video_path, download_dir)
        return await status.edit_text(
            f"❌ **{to_smallcaps('ɴᴏ sᴜʙᴛɪᴛʟᴇ sᴛʀᴇᴀᴍs ғᴏᴜɴᴅ ɪɴ ᴛʜɪs ᴠɪᴅᴇᴏ!')}**"
            f"{format_watermark()}"
        )

    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ')}** `{len(tracks)}` **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ᴛʀᴀᴄᴋ(s)...')}**")

    for t in tracks:
        sub_path = t["path"]
        caption = (
            f"💬 **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ᴛʀᴀᴄᴋ')}** `#{t['index']}`\n\n"
            f"• 🏷️ **{to_smallcaps('ʟᴀɴɢᴜᴀɢᴇ')}** : `{t['language'].upper()}`\n"
            f"• 📝 **{to_smallcaps('ᴛɪᴛʟᴇ')}** : `{t['title']}`\n"
            f"• 🔤 **{to_smallcaps('ғᴏʀᴍᴀᴛ')}** : `{t['codec']}`"
            f"{format_watermark()}"
        )
        try:
            await client.send_document(
                chat_id=target_msg.chat.id,
                document=sub_path,
                caption=caption,
                file_name=os.path.basename(sub_path)
            )
        except Exception as e:
            logger.error(f"Failed to upload subtitle file: {e}")

    clean_temp_files(video_path, download_dir)
    btn = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ')}", callback_data=f"pro_menu_{media_msg.id}")]]
    await status.edit_text(
        f"✅ **{to_smallcaps('sᴜᴄᴄᴇssғᴜʟʟʏ ᴇxᴛʀᴀᴄᴛᴇᴅ')}** `{len(tracks)}` **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ᴛʀᴀᴄᴋ(s)!')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ==================== 4. ADD AUDIO ====================

@Client.on_message(filters.private & filters.command("addaudio"))
async def add_audio_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴀᴅᴅ ᴀᴜᴅɪᴏ!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴡɪᴛʜ')} `/addaudio`"
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
            f"🎵 **{to_smallcaps('ᴀᴅᴅ ᴀᴜᴅɪᴏ ᴛᴏ ᴠɪᴅᴇᴏ')}** ✦\n\n"
            f"💬 {to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪᴛʜ ᴛʜᴇ ᴀᴜᴅɪᴏ ғɪʟᴇ (.ᴍᴘ𝟹, .ᴍ𝟺ᴀ, .ᴀᴀᴄ, .ᴡᴀᴠ) ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴀᴅᴅ.')}\n\n"
            f"💡 {to_smallcaps('sᴇɴᴅ')} `/cancel` {to_smallcaps('ᴛᴏ ᴀʙᴏʀᴛ.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("sᴇɴᴅ ᴏʀ ʀᴇᴘʟʏ ᴡɪᴛʜ ᴀᴜᴅɪᴏ ғɪʟᴇ..."))
    )
    await cache.set(f"waiting_addaudio_{chat_id}", video_msg_id, ttl=300)

@Client.on_callback_query(filters.regex(r"^pro_addaud_mode_(\d+)_(\d+)_(add|replace)"))
async def execute_add_audio(client: Client, query: CallbackQuery):
    video_id = int(query.matches[0].group(1))
    audio_id = int(query.matches[0].group(2))
    mode = query.matches[0].group(3)
    replace = (mode == "replace")
    user_id = query.from_user.id

    status = await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴀᴜᴅɪᴏ ᴍᴜxɪɴɢ...')}**")

    video_msg = await client.get_messages(query.message.chat.id, video_id)
    audio_msg = await client.get_messages(query.message.chat.id, audio_id)

    if not video_msg or not audio_msg:
        return await status.edit_text(f"❌ **{to_smallcaps('ᴍᴇᴅɪᴀ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!')}**")

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
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, time.time())
        )
        await audio_msg.download(
            file_name=a_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴀᴜᴅɪᴏ", status, time.time())
        )
    except Exception as e:
        clean_temp_files(v_path, a_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    await status.edit_text(f"🎛️ **{to_smallcaps('ᴍᴜxɪɴɢ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋ ɪɴᴛᴏ ᴠɪᴅᴇᴏ...')}**")
    success = await add_audio_to_video(v_path, a_path, out_path, replace_existing=replace)

    if not success or not os.path.exists(out_path):
        clean_temp_files(v_path, a_path, out_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴀᴜᴅɪᴏ ᴍᴜxɪɴɢ ғᴀɪʟᴇᴅ!')}**{format_watermark()}")

    out_size = os.path.getsize(out_path)
    if out_size > MAX_BOT_FILE_SIZE:
        clean_temp_files(v_path, a_path, out_path, download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ!')}**")

    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('ᴀᴜᴅɪᴏ ᴍᴜxᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{time_formatter(seconds=dur)}`\n"
        f"• 🎚️ **{to_smallcaps('ᴍᴏᴅᴇ')}** : `{'REPLACE EXISTING' if replace else 'ADD NEW TRACK'}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ ᴡɪᴛʜ ɴᴇᴡ ᴀᴜᴅɪᴏ...')}**")

    try:
        sent = await client.send_video(
            chat_id=query.message.chat.id,
            video=out_path,
            caption=caption,
            duration=dur,
            width=int(attrs["width"]),
            height=int(attrs["height"]),
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

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
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴀᴅᴅ sᴜʙᴛɪᴛʟᴇs!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴡɪᴛʜ')} `/addsub`"
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
            f"💬 **{to_smallcaps('ᴀᴅᴅ sᴜʙᴛɪᴛʟᴇ ᴛᴏ ᴠɪᴅᴇᴏ')}** ✦\n\n"
            f"💬 {to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪᴛʜ ʏᴏᴜʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ (.sʀᴛ, .ᴀss, .ᴠᴛᴛ).')}\n\n"
            f"💡 {to_smallcaps('sᴇɴᴅ')} `/cancel` {to_smallcaps('ᴛᴏ ᴀʙᴏʀᴛ.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("sᴇɴᴅ ᴏʀ ʀᴇᴘʟʏ ᴡɪᴛʜ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ..."))
    )
    await cache.set(f"waiting_addsub_{chat_id}", video_msg_id, ttl=300)

async def execute_add_subtitle(client: Client, reply_msg: Message, video_id: int, sub_msg: Message):
    status = await reply_msg.reply_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ sᴜʙᴛɪᴛʟᴇ ᴍᴜxɪɴɢ...')}**")
    user_id = reply_msg.from_user.id

    video_msg = await client.get_messages(reply_msg.chat.id, video_id)
    if not video_msg or not video_msg.media:
        return await status.edit_text(f"❌ **{to_smallcaps('ᴠɪᴅᴇᴏ ᴍᴇssᴀɢᴇ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!')}**")

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
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, time.time())
        )
        await sub_msg.download(
            file_name=s_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ", status, time.time())
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    await status.edit_text(f"💬 **{to_smallcaps('sᴏғᴛ-ᴍᴜxɪɴɢ sᴜʙᴛɪᴛʟᴇ ɪɴᴛᴏ ᴠɪᴅᴇᴏ...')}**")
    success = await add_subtitle_to_video(v_path, s_path, out_path)

    if not success or not os.path.exists(out_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ᴍᴜxɪɴɢ ғᴀɪʟᴇᴅ!')}**")

    out_size = os.path.getsize(out_path)
    if out_size > MAX_BOT_FILE_SIZE:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ!')}**")

    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ᴍᴜxᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{time_formatter(seconds=dur)}`\n"
        f"• 💬 **{to_smallcaps('sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ')}** : `{s_name}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ ᴡɪᴛʜ sᴜʙᴛɪᴛʟᴇ...')}**")

    try:
        sent = await client.send_video(
            chat_id=reply_msg.chat.id,
            video=out_path,
            caption=caption,
            duration=dur,
            width=int(attrs["width"]),
            height=int(attrs["height"]),
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

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
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴛʀɪᴍ!')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴡɪᴛʜ')} `/trim`"
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
            f"✂️ **{to_smallcaps('ᴛʀɪᴍ ᴠɪᴅᴇᴏ sᴇɢᴍᴇɴᴛ')}** ✦\n\n"
            f"💬 {to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪᴛʜ sᴛᴀʀᴛ ᴀɴᴅ ᴇɴᴅ ᴛɪᴍᴇ.')}\n\n"
            f"• **{to_smallcaps('ғᴏʀᴍᴀᴛ')}** : `HH:MM:SS HH:MM:SS`\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')} 1** : `00:01:30 00:05:00`\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')} 2** : `01:30 to 05:00`\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')} 3** : `90 300` *(in seconds)*\n\n"
            f"💡 {to_smallcaps('sᴇɴᴅ')} `/cancel` {to_smallcaps('ᴛᴏ ᴀʙᴏʀᴛ.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("ᴇ.ɢ. 00:01:30 00:05:00"))
    )
    await cache.set(f"waiting_trim_{chat_id}", video_msg_id, ttl=300)

async def execute_trim_video(client: Client, reply_msg: Message, video_id: int, time_text: str):
    start_sec, end_sec = parse_time_range(time_text)
    if start_sec is None or end_sec is None or end_sec <= start_sec:
        return await reply_msg.reply_text(
            f"⚠️ **{to_smallcaps('ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ ʀᴀɴɢᴇ!')}**\n\n"
            f"• **{to_smallcaps('ғᴏʀᴍᴀᴛ')}** : `HH:MM:SS HH:MM:SS`\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}** : `00:01:30 00:05:00`\n"
            f"{format_watermark()}"
        )

    status = await reply_msg.reply_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴠɪᴅᴇᴏ ᴛʀɪᴍ...')}**")
    user_id = reply_msg.from_user.id

    video_msg = await client.get_messages(reply_msg.chat.id, video_id)
    if not video_msg or not video_msg.media:
        return await status.edit_text(f"❌ **{to_smallcaps('ᴠɪᴅᴇᴏ ᴍᴇssᴀɢᴇ ɴᴏ ʟᴏɴɢᴇʀ ᴇxɪsᴛs!')}**")

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
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, time.time())
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    await status.edit_text(f"✂️ **{to_smallcaps('ᴛʀɪᴍᴍɪɴɢ ᴠɪᴅᴇᴏ sᴇɢᴍᴇɴᴛ (sᴛʀᴇᴀᴍ ᴄᴏᴘʏ)...')}**")
    success = await trim_video(v_path, out_path, start_sec, end_sec)

    if not success or not os.path.exists(out_path):
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴠɪᴅᴇᴏ ᴛʀɪᴍ ғᴀɪʟᴇᴅ!')}**")

    out_size = os.path.getsize(out_path)
    if out_size > MAX_BOT_FILE_SIZE:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴛʀɪᴍᴍᴇᴅ ᴠɪᴅᴇᴏ ᴇxᴄᴇᴇᴅs 𝟸ɢʙ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ!')}**")

    attrs = await get_media_attributes(out_path)
    dur = int(attrs["duration"])
    thumb_path = await resolve_thumbnail(client, user_id, download_dir, out_path, dur)
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    caption = (
        f"✅ **{to_smallcaps('ᴠɪᴅᴇᴏ ᴛʀɪᴍᴍᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{out_name}`\n"
        f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{humanbytes(out_size)}`\n"
        f"• ⏱️ **{to_smallcaps('sᴇɢᴍᴇɴᴛ')}** : `{time_formatter(seconds=int(start_sec))}` ➔ `{time_formatter(seconds=int(end_sec))}`\n"
        f"• ⏱️ **{to_smallcaps('ᴛᴏᴛᴀʟ ʟᴇɴɢᴛʜ')}** : `{time_formatter(seconds=dur)}`"
        f"{format_watermark()}"
    )

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴛʀɪᴍᴍᴇᴅ ᴠɪᴅᴇᴏ...')}**")

    try:
        sent = await client.send_video(
            chat_id=reply_msg.chat.id,
            video=out_path,
            caption=caption,
            duration=dur,
            width=int(attrs["width"]),
            height=int(attrs["height"]),
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(download_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    clean_temp_files(download_dir)
    try:
        await status.delete()
    except Exception:
        pass

# ==================== FORCEREPLY DISPATCHER ====================

@Client.on_message(filters.private & filters.reply)
async def file_pro_force_reply_listener(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_markup:
        return
    if not isinstance(message.reply_to_message.reply_markup, ForceReply):
        return

    user_id = message.from_user.id

    # 1. Check waiting for addaudio
    aud_video_id = await cache.get(f"waiting_addaudio_{user_id}")
    if aud_video_id:
        await cache.delete(f"waiting_addaudio_{user_id}")
        if not (message.audio or message.voice or (message.document and message.document.mime_type and "audio" in message.document.mime_type)):
            return await message.reply_text(
                f"❌ **{to_smallcaps('ɴᴏ ᴠᴀʟɪᴅ ᴀᴜᴅɪᴏ ғɪʟᴇ ʀᴇᴄᴇɪᴠᴇᴅ!')}**\n\n"
                f"{to_smallcaps('ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴀᴜᴅɪᴏ ғɪʟᴇ (.ᴍᴘ𝟹, .ᴍ𝟺ᴀ, .ᴀᴀᴄ, .ᴡᴀᴠ).')}"
                f"{format_watermark()}"
            )
        btn = [
            [
                InlineKeyboardButton(f"➕ {to_smallcaps('ᴀᴅᴅ ᴀs ɴᴇᴡ ᴛʀᴀᴄᴋ')}", callback_data=f"pro_addaud_mode_{aud_video_id}_{message.id}_add"),
                InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇᴘʟᴀᴄᴇ ᴀᴜᴅɪᴏ')}", callback_data=f"pro_addaud_mode_{aud_video_id}_{message.id}_replace")
            ],
            [
                InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
            ]
        ]
        return await message.reply_text(
            f"✦ **{to_smallcaps('sᴇʟᴇᴄᴛ ᴀᴜᴅɪᴏ ᴍᴏᴅᴇ')}** ✦\n\n"
            f"• 🎵 **{to_smallcaps('ᴀᴜᴅɪᴏ')}** : `{getattr(message.audio or message.document, 'file_name', 'audio.mp3')}`\n\n"
            f"💡 **{to_smallcaps('ᴄʜᴏᴏsᴇ ʜᴏᴡ ᴛᴏ ᴍᴜx ᴛʜɪs ᴀᴜᴅɪᴏ ɪɴᴛᴏ ʏᴏᴜʀ ᴠɪᴅᴇᴏ:')}**"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    # 2. Check waiting for addsub
    sub_video_id = await cache.get(f"waiting_addsub_{user_id}")
    if sub_video_id:
        await cache.delete(f"waiting_addsub_{user_id}")
        if not (message.document and (message.document.file_name or "").lower().endswith((".srt", ".ass", ".vtt", ".sub"))):
            return await message.reply_text(
                f"❌ **{to_smallcaps('ɴᴏ ᴠᴀʟɪᴅ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ ʀᴇᴄᴇɪᴠᴇᴅ!')}**\n\n"
                f"{to_smallcaps('ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ .sʀᴛ, .ᴀss, ᴏʀ .ᴠᴛᴛ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ.')}"
                f"{format_watermark()}"
            )
        return await execute_add_subtitle(client, message, sub_video_id, message)

    # 3. Check waiting for trim
    trim_video_id = await cache.get(f"waiting_trim_{user_id}")
    if trim_video_id:
        await cache.delete(f"waiting_trim_{user_id}")
        if not message.text:
            return await message.reply_text(
                f"❌ **{to_smallcaps('ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ sᴛᴀʀᴛ ᴀɴᴅ ᴇɴᴅ ᴛɪᴍᴇ ᴛᴇxᴛ!')}**"
                f"{format_watermark()}"
            )
        return await execute_trim_video(client, message, trim_video_id, message.text.strip())
