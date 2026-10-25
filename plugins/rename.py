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
from plugins.core_db import user_repo, file_repo
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
    telegram_media_metadata,
    resolve_thumbnail,
    extract_and_format_caption,
    schedule_deletion
)

MAX_BOT_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MiB (2GB Telegram Bot API Limit)

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def incoming_file_entry(client: Client, message: Message):
    user = message.from_user
    if user and await user_repo.is_banned(user.id):
        return await message.reply_text(
            f"🚫 **{to_smallcaps('you are banned from using this bot!')}**"
            f"{format_watermark()}"
        )

    # Check if user is replying to an addaudio / addsub ForceReply prompt first
    if message.reply_to_message and message.reply_to_message.reply_markup:
        if isinstance(message.reply_to_message.reply_markup, ForceReply):
            return

    u = await user_repo.get_or_create(user.id, user.first_name, user.username) if user else {}
    media = message.document or message.video or message.audio
    raw_file_name = getattr(media, "file_name", None) or "Unknown_File.mp4"
    file_name = raw_file_name.replace("`", "'")
    file_size_bytes = getattr(media, "file_size", 0)
    file_size = humanbytes(file_size_bytes)
    mime_type = getattr(media, "mime_type", "video/mp4")
    dur_val = getattr(media, "duration", 0)
    duration = time_formatter(seconds=dur_val) if dur_val > 0 else "N/A"

    is_video = bool(message.video or (message.document and mime_type and mime_type.startswith("video/")))
    is_compressible = is_video or bool(mime_type and mime_type.startswith("audio/"))
    media_metadata = telegram_media_metadata(media, message)

    # Auto-Index file in DB for instant 12 MB/s streaming & 4 External Players
    bin_chan = Config.BIN_CHANNEL if Config.BIN_CHANNEL != 0 else message.chat.id
    try:
        log_msg = await message.forward(bin_chan) if bin_chan != message.chat.id else message
    except Exception:
        log_msg = message

    file_id = secrets.token_urlsafe(10)
    await file_repo.save_file(
        file_id=file_id,
        chat_id=log_msg.chat.id,
        message_id=log_msg.id,
        file_name=file_name,
        file_size=file_size_bytes,
        mime_type=mime_type,
        user_id=user.id if user else 0,
        metadata=media_metadata,
        tg_file_id=getattr(media, "file_id", None)
    )
    watch_url = f"{Config.BASE_URL}/watch/{file_id}"
    download_url = f"{Config.BASE_URL}/download/{file_id}"

    # Check if Auto-Rename is enabled & user has prefix/suffix configured
    if u.get("auto_rename") and (u.get("prefix") or u.get("suffix")) and file_size_bytes <= MAX_BOT_FILE_SIZE:
        name_parts = os.path.splitext(raw_file_name)
        # run_rename_workflow applies the configured prefix/suffix exactly once.
        auto_target = sanitize_filename(f"{name_parts[0]}{name_parts[1] or '.mp4'}")
        await cache.set(f"rename_name_{user.id}_{message.id}", auto_target, ttl=600)
        upload_mode = "vid" if u.get("upload_mode", "video") == "video" else "doc"
        return await run_rename_workflow(client, message, message, user.id, message.id, auto_target, upload_mode, watch_url, download_url)

    # Check if Auto-Compress is enabled for videos
    if u.get("auto_compress") and is_compressible and file_size_bytes <= MAX_BOT_FILE_SIZE:
        from plugins.compressor import run_auto_compress_workflow
        return await run_auto_compress_workflow(client, message, user.id)

    if file_size_bytes > MAX_BOT_FILE_SIZE:
        text = (
            f"✦ **{to_smallcaps('smart media inspector (12 mb/s)')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('file name')}** : `{file_name}`\n"
            f"• 📦 **{to_smallcaps('file size')}** : `{file_size}`\n"
            f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s Turbo`\n"
            f"• 🏷️ **{to_smallcaps('mime type')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('duration')}** : `{duration}`\n\n"
            f"⚠️ **{to_smallcaps('note')}** : {to_smallcaps('file exceeds 2gb bot upload limit, but 12 mb/s stream & 4 external players are ready!')}"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🎬 {to_smallcaps('watch (4 players)')}", url=watch_url),
                InlineKeyboardButton(f"⬇️ {to_smallcaps('12 mb/s download')}", url=download_url)
            ],
            [InlineKeyboardButton(f"🗜️ {to_smallcaps('compress or stream only')}", callback_data=f"compress_menu_{message.id}")],
            [InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")]
        ]
        return await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

    has_thumb = "✅" if u and u.get("thumb_id") else "🌐 ᴛʜᴀᴍ_ᴜʀʟ"
    has_caption = "✅" if u and (u.get("custom_caption") or u.get("captions_list")) else "📄 ᴀᴜᴛᴏ"
    auto_ren_status = "🟢 ᴏɴ" if u.get("auto_rename") else "⚪ ᴏғғ"
    auto_comp_status = "🟢 ᴏɴ" if u.get("auto_compress") else "⚪ ᴏғғ"

    text = (
        f"✦ **{to_smallcaps('smart media studio & 12 mb/s stream')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('file name')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('file size')}** : `{file_size}`\n"
        f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s (PLAYit • MX • VLC • S Player)`\n"
        f"• 🏷️ **{to_smallcaps('mime type')}** : `{mime_type}`\n"
        f"• ⏱️ **{to_smallcaps('duration')}** : `{duration}`\n"
        f"• 🖼️ **{to_smallcaps('thumbnail')}** : `{has_thumb}` | 📝 **{to_smallcaps('caption')}** : `{has_caption}`\n"
        f"• 🤖 **{to_smallcaps('auto rename')}** : `{auto_ren_status}` | 🗜️ **{to_smallcaps('auto compress')}** : `{auto_comp_status}`\n\n"
        f"🔗 **{to_smallcaps('instant 4-player watch link')}** :\n{watch_url}\n\n"
        f"💡 **{to_smallcaps('select an action below to proceed:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"✏️ {to_smallcaps('rename file')}", callback_data=f"rename_{message.id}"),
            InlineKeyboardButton(f"⚡ {to_smallcaps('stream details')}", callback_data=f"stream_{message.id}")
        ],
        [
            InlineKeyboardButton(f"🎬 {to_smallcaps('watch (4 players)')}", url=watch_url),
            InlineKeyboardButton(f"⬇️ {to_smallcaps('12 mb/s download')}", url=download_url)
        ]
    ]
    row3 = []
    if is_compressible:
        row3.append(InlineKeyboardButton(f"🗜️ {to_smallcaps('compress media')}", callback_data=f"compress_menu_{message.id}"))
    row3.append(InlineKeyboardButton(f"📊 {to_smallcaps('mediainfo')}", callback_data=f"pro_mediainfo_{message.id}"))
    buttons.append(row3)
    buttons.append([
        InlineKeyboardButton(f"🎛️ {to_smallcaps('file pro advance features')}", callback_data=f"pro_menu_{message.id}")
    ])
    buttons.append([
        InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")
    ])

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True, disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["autorename", "auto_rename"]))
async def toggle_autorename_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    u = await user_repo.get_or_create(user_id, message.from_user.first_name, message.from_user.username)
    new_state = not bool(u.get("auto_rename", False))
    await user_repo.update_user(user_id, {"auto_rename": new_state})
    state_txt = "🟢 ᴇɴᴀʙʟᴇᴅ" if new_state else "⚪ ᴅɪsᴀʙʟᴇᴅ"
    await message.reply_text(
        f"✦ **{to_smallcaps('auto-rename mode')}** ✦\n\n"
        f"• 🤖 **{to_smallcaps('status')}** : `{state_txt}`\n"
        f"• 🏷️ **{to_smallcaps('prefix')}** : `{u.get('prefix') or 'None'}`\n"
        f"• 🏷️ **{to_smallcaps('suffix')}** : `{u.get('suffix') or 'None'}`\n\n"
        f"💡 {to_smallcaps('when enabled, incoming files are automatically renamed with your prefix/suffix and custom thumbnail + caption!')}"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["setprefix", "prefix"]))
async def set_prefix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('usage')}** : `/setprefix <prefix_text>`\n\n"
            f"• **{to_smallcaps('example')}** : `/setprefix [MMW] `\n\n"
            f"💡 {to_smallcaps('this prefix will be prepended to every renamed file.')}"
            f"{format_watermark()}"
        )
    prefix = message.text.split(None, 1)[1]
    await user_repo.update_user(message.from_user.id, {"prefix": prefix})
    await message.reply_text(
        f"✅ **{to_smallcaps('file prefix saved!')}**\n\n"
        f"• 🏷️ **{to_smallcaps('new prefix')}** : `{prefix}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["setsuffix", "suffix"]))
async def set_suffix_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('usage')}** : `/setsuffix <suffix_text>`\n\n"
            f"• **{to_smallcaps('example')}** : `/setsuffix @mallumovieworldmain2`\n\n"
            f"💡 {to_smallcaps('this suffix will be inserted before the file extension.')}"
            f"{format_watermark()}"
        )
    suffix = message.text.split(None, 1)[1]
    await user_repo.update_user(message.from_user.id, {"suffix": suffix})
    await message.reply_text(
        f"✅ **{to_smallcaps('file suffix saved!')}**\n\n"
        f"• 🏷️ **{to_smallcaps('new suffix')}** : `{suffix}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["delprefix", "delsuffix"]))
async def del_prefix_suffix(client: Client, message: Message):
    cmd = message.command[0].lower()
    if "prefix" in cmd:
        await user_repo.update_user(message.from_user.id, {"prefix": None})
        await message.reply_text(f"🗑️ **{to_smallcaps('file prefix removed successfully!')}**{format_watermark()}")
    else:
        await user_repo.update_user(message.from_user.id, {"suffix": None})
        await message.reply_text(f"🗑️ **{to_smallcaps('file suffix removed successfully!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("rename"))
async def rename_cmd_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a file or video to rename.')}**\n\n"
            f"• **{to_smallcaps('usage')}** : `/rename <new_name.ext>`"
            f"{format_watermark()}"
        )

    media = target.document or target.video or target.audio
    if getattr(media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('file too large (> 2gb)!')}**\n\n"
            f"💡 {to_smallcaps('use')} `/stream` {to_smallcaps('to generate a 12 mb/s streaming link instead!')}"
            f"{format_watermark()}"
        )

    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('please provide a new file name!')}**\n\n"
            f"• **{to_smallcaps('example')}** : `/rename sample_video.mp4`"
            f"{format_watermark()}"
        )

    raw_input_name = message.text.split(None, 1)[1]
    new_name = sanitize_filename(raw_input_name)

    orig_name = getattr(media, "file_name", "") or ""
    orig_ext = os.path.splitext(orig_name)[1]
    if not os.path.splitext(new_name)[1] and orig_ext:
        new_name = f"{new_name}{orig_ext}"

    await cache.set(f"rename_name_{message.from_user.id}_{target.id}", new_name, ttl=600)
    await show_rename_options(message, target.id, new_name)

@Client.on_callback_query(filters.regex(r"^rename_(\d+)"))
async def rename_callback_ask(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)

    media = original.document or original.video or original.audio
    if getattr(media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await query.message.edit_text(
            f"⚠️ **{to_smallcaps('file too large (> 2gb)!')}**\n\n"
            f"💡 {to_smallcaps('use the stream link button to watch or download at 12 mb/s!')}"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⚡ {to_smallcaps('stream link')}", callback_data=f"stream_{msg_id}")]])
        )

    old_name = getattr(media, "file_name", None) or "file.mp4"

    await query.message.delete()
    await client.send_message(
        chat_id=query.message.chat.id,
        text=(
            f"✏️ **{to_smallcaps('enter new file name')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('current')}** : `{old_name}`\n\n"
            f"💬 {to_smallcaps('reply to this message or send your new filename.')}\n"
            f"💡 {to_smallcaps('send')} `/cancel` {to_smallcaps('to abort.')}"
            f"{format_watermark()}"
        ),
        reply_markup=ForceReply(placeholder=to_smallcaps("enter new file name..."))
    )
    await cache.set(f"waiting_rename_{query.from_user.id}", msg_id, ttl=300)

@Client.on_message(filters.private & filters.text & ~filters.command([
    "start", "help", "about", "status", "settings", "cancel", "rename", "autorename", "auto_rename",
    "compress", "autocompress", "auto_compress", "stream", "getfile", "file", "revoke", "delfile",
    "revokestream", "pro", "filepro", "advance", "tools", "setprefix", "prefix", "setsuffix", "suffix",
    "delprefix", "delsuffix", "setcaption", "set_caption", "addcaption", "add_caption", "caption",
    "captions", "see_caption", "delcaption", "del_caption", "setthumb", "set_thumb", "thumb",
    "viewthumb", "view_thumb", "delthumb", "del_thumb", "autodelete", "set_timer", "timer",
    "session", "admin", "stats", "users", "user", "userinfo", "cache", "database", "dbstats",
    "logs", "devilmod", "devmode", "dev", "developer", "broadcast", "ban", "unban", "restart",
    "id", "myid", "info", "whois", "ping", "speedtest", "speed", "mediainfo", "probe", "search",
    "extractaudio", "extaudio", "extractsub", "extsub", "addaudio", "addsub", "trim", "clean", "purge"
]))
async def reply_force_rename_collector(client: Client, message: Message):
    user_id = message.from_user.id

    # If user is waiting for trim time in file_pro, let file_pro handle it
    if await cache.get(f"waiting_trim_{user_id}"):
        from plugins.file_pro import execute_trim_video
        trim_vid_id = await cache.get(f"waiting_trim_{user_id}")
        await cache.delete(f"waiting_trim_{user_id}")
        return await execute_trim_video(client, message, trim_vid_id, message.text.strip())

    # If user is in interactive session generator step, let session.py handle it
    if await cache.get(f"sess_step_{user_id}"):
        from plugins.session import handle_session_text_step
        return await handle_session_text_step(client, message)

    msg_id = await cache.get(f"waiting_rename_{user_id}")
    if not msg_id:
        return

    await cache.delete(f"waiting_rename_{user_id}")
    new_name = sanitize_filename(message.text.strip())

    try:
        orig_msg = await client.get_messages(message.chat.id, msg_id)
        if orig_msg and orig_msg.media:
            orig_media = orig_msg.document or orig_msg.video or orig_msg.audio
            orig_file_name = getattr(orig_media, "file_name", "") or ""
            orig_ext = os.path.splitext(orig_file_name)[1]
            if not os.path.splitext(new_name)[1] and orig_ext:
                new_name = f"{new_name}{orig_ext}"
    except Exception:
        pass

    await cache.set(f"rename_name_{user_id}_{msg_id}", new_name, ttl=600)
    await show_rename_options(message, msg_id, new_name)

async def show_rename_options(message: Message, target_id: int, new_name: str):
    btn = [
        [
            InlineKeyboardButton(f"📁 {to_smallcaps('upload as document')}", callback_data=f"renameto_doc_{target_id}"),
            InlineKeyboardButton(f"🎬 {to_smallcaps('upload as video')}", callback_data=f"renameto_vid_{target_id}")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")
        ]
    ]
    await message.reply_text(
        f"✦ **{to_smallcaps('select upload type')}** ✦\n\n"
        f"• 🏷️ **{to_smallcaps('target name')}** : `{new_name}`\n\n"
        f"💡 {to_smallcaps('choose whether to send the file as a streamable video or a raw document.')}"
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
        return await query.answer(to_smallcaps("session expired! please try again."), show_alert=True)

    original_msg = await client.get_messages(query.message.chat.id, target_id)
    if not original_msg or not original_msg.media:
        return await query.message.edit_text(f"❌ **{to_smallcaps('original media no longer exists!')}**")

    await run_rename_workflow(client, original_msg, query.message, user_id, target_id, new_name, upload_type, is_edit=True)

async def run_rename_workflow(
    client: Client,
    original_msg: Message,
    reply_msg: Message,
    user_id: int,
    target_id: int,
    new_name: str,
    upload_type: str = "vid",
    watch_url: str = "",
    download_url: str = "",
    is_edit: bool = False
):
    source_media = original_msg.document or original_msg.video or original_msg.audio
    if getattr(source_media, "file_size", 0) > MAX_BOT_FILE_SIZE:
        return await reply_msg.reply_text(
            f"🚫 **{to_smallcaps('rename is limited to files below 2 gb.')}**\n\n"
            f"⚡ {to_smallcaps('use stream for oversized files, or compress them after reducing the size.')}{format_watermark()}"
        )
    status_msg = await (reply_msg.edit_text if is_edit else reply_msg.reply_text)(
        f"⏳ **{to_smallcaps('initializing fast rename workflow...')}**"
    )

    media = source_media
    u = await user_repo.get_user(user_id)
    prefix = (u.get("prefix") if u else "") or ""
    suffix = (u.get("suffix") if u else "") or ""

    name_parts = os.path.splitext(new_name)
    base_name = name_parts[0]
    ext = name_parts[1]
    if not ext:
        orig_file_name = getattr(media, "file_name", "") or ""
        ext = os.path.splitext(orig_file_name)[1] or ".mp4"

    if prefix and not base_name.startswith(prefix):
        base_name = f"{prefix}{base_name}"
    if suffix and not base_name.endswith(suffix):
        base_name = f"{base_name}{suffix}"

    final_name = sanitize_filename(f"{base_name}{ext}")

    unique_token = secrets.token_hex(4)
    download_dir = os.path.join(Config.DOWNLOAD_DIR, f"{user_id}_{target_id}_{unique_token}")
    os.makedirs(download_dir, exist_ok=True)
    download_path = os.path.join(download_dir, final_name)

    start_time = time.time()
    try:
        await original_msg.download(
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 downloading file", status_msg, start_time)
        )
    except Exception as e:
        clean_temp_files(download_path, download_dir)
        return await status_msg.edit_text(f"❌ **{to_smallcaps('download failed')}** : `{e}`")

    if not os.path.exists(download_path):
        clean_temp_files(download_dir)
        return await status_msg.edit_text(f"❌ **{to_smallcaps('file not found after download!')}**")

    attrs = await get_media_attributes(download_path)
    dur = int(attrs.get("duration", 0))
    thumb_path = await resolve_thumbnail(
        client=client,
        user_id=user_id,
        temp_dir=download_dir,
        video_path=download_path,
        duration=dur
    )
    if not isinstance(thumb_path, str) or not os.path.exists(thumb_path):
        thumb_path = None

    orig_caption = original_msg.caption or ""
    final_caption = await extract_and_format_caption(
        user_id=user_id,
        file_path=download_path,
        original_caption=orig_caption,
        file_id=str(target_id)
    )

    upload_start = time.time()
    await status_msg.edit_text(f"📤 **{to_smallcaps('uploading renamed file...')}**")

    sent_msg = None
    try:
        if upload_type == "vid":
            w = int(attrs.get("width", 1280)) or 1280
            h = int(attrs.get("height", 720)) or 720
            try:
                sent_msg = await client.send_video(
                    chat_id=reply_msg.chat.id,
                    video=download_path,
                    caption=final_caption,
                    duration=dur,
                    width=w,
                    height=h,
                    thumb=thumb_path,
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=("📤 uploading video", status_msg, upload_start)
                )
            except Exception:
                sent_msg = await client.send_document(
                    chat_id=reply_msg.chat.id,
                    document=download_path,
                    caption=final_caption,
                    thumb=thumb_path,
                    force_document=True,
                    progress=progress_for_pyrogram,
                    progress_args=("📤 uploading document", status_msg, upload_start)
                )
        else:
            sent_msg = await client.send_document(
                chat_id=reply_msg.chat.id,
                document=download_path,
                caption=final_caption,
                thumb=thumb_path,
                force_document=True,
                progress=progress_for_pyrogram,
                progress_args=("📤 uploading document", status_msg, upload_start)
            )
    except Exception as e:
        clean_temp_files(download_path, thumb_path, download_dir)
        return await status_msg.edit_text(f"❌ **{to_smallcaps('upload failed')}** : `{e}`")

    clean_temp_files(download_path, thumb_path, download_dir)
    try:
        await status_msg.delete()
    except Exception:
        pass

    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_msg:
        await schedule_deletion(sent_msg.chat.id, sent_msg.id, del_time)
