import time
import os
import socket
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from plugins.core_utils import to_smallcaps, format_watermark, humanbytes, time_formatter, clean_temp_files
from plugins.core_db import file_repo
from plugins.core_services import get_detailed_mediainfo

BOT_START_TIME = time.time()

@Client.on_message(filters.command(["id", "myid"]))
async def id_command_handler(client: Client, message: Message):
    user = message.from_user
    chat = message.chat
    reply = message.reply_to_message

    text = f"✦ **{to_smallcaps('user & chat identifier')}** ✦\n\n"
    if user:
        dc_id = getattr(user, "dc_id", "N/A") or "N/A"
        text += (
            f"👤 **{to_smallcaps('your info')}** :\n"
            f"• 🆔 **{to_smallcaps('user id')}** : `{user.id}`\n"
            f"• 👤 **{to_smallcaps('first name')}** : {user.first_name}\n"
            f"• 🏷️ **{to_smallcaps('username')}** : @{user.username if user.username else to_smallcaps('none')}\n"
            f"• 🌐 **{to_smallcaps('datacenter')}** : `DC {dc_id}`\n\n"
        )
    if reply and reply.from_user:
        r_user = reply.from_user
        r_dc = getattr(r_user, "dc_id", "N/A") or "N/A"
        text += (
            f"💬 **{to_smallcaps('replied user')}** :\n"
            f"• 🆔 **{to_smallcaps('user id')}** : `{r_user.id}`\n"
            f"• 👤 **{to_smallcaps('first name')}** : {r_user.first_name}\n"
            f"• 🏷️ **{to_smallcaps('username')}** : @{r_user.username if r_user.username else to_smallcaps('none')}\n"
            f"• 🌐 **{to_smallcaps('datacenter')}** : `DC {r_dc}`\n\n"
        )
    if reply and reply.forward_from:
        f_user = reply.forward_from
        text += (
            f"⏩ **{to_smallcaps('forwarded from')}** :\n"
            f"• 🆔 **{to_smallcaps('user id')}** : `{f_user.id}`\n"
            f"• 👤 **{to_smallcaps('name')}** : {f_user.first_name}\n\n"
        )
    if reply and reply.forward_from_chat:
        f_chat = reply.forward_from_chat
        text += (
            f"📢 **{to_smallcaps('forwarded channel')}** :\n"
            f"• 🆔 **{to_smallcaps('chat id')}** : `{f_chat.id}`\n"
            f"• 🏷️ **{to_smallcaps('title')}** : {f_chat.title}\n\n"
        )
    text += (
        f"💬 **{to_smallcaps('chat details')}** :\n"
        f"• 🆔 **{to_smallcaps('chat id')}** : `{chat.id}`\n"
        f"• 🏷️ **{to_smallcaps('chat type')}** : `{chat.type.name if hasattr(chat.type, 'name') else str(chat.type)}`\n"
        f"• 📨 **{to_smallcaps('message id')}** : `{message.id}`"
        f"{format_watermark()}"
    )
    await message.reply_text(text)

@Client.on_message(filters.command(["info", "whois"]))
async def info_command_handler(client: Client, message: Message):
    target = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target = await client.get_users(message.command[1])
        except Exception:
            return await message.reply_text(f"❌ **{to_smallcaps('user not found!')}**")

    dc_id = getattr(target, "dc_id", "N/A") or "N/A"
    is_bot = "🤖 ʏᴇs" if target.is_bot else "👤 ɴᴏ"
    is_premium = "⭐ ʏᴇs" if getattr(target, "is_premium", False) else "❌ ɴᴏ"

    text = (
        f"✦ **{to_smallcaps('user information card')}** ✦\n\n"
        f"• 🆔 **{to_smallcaps('user id')}** : `{target.id}`\n"
        f"• 👤 **{to_smallcaps('first name')}** : {target.first_name}\n"
        f"• 👥 **{to_smallcaps('last name')}** : {target.last_name or to_smallcaps('none')}\n"
        f"• 🏷️ **{to_smallcaps('username')}** : @{target.username if target.username else to_smallcaps('none')}\n"
        f"• 🌐 **{to_smallcaps('datacenter')}** : `DC {dc_id}`\n"
        f"• 🤖 **{to_smallcaps('is bot?')}** : `{is_bot}`\n"
        f"• ⭐ **{to_smallcaps('premium?')}** : `{is_premium}`\n"
        f"• 🔗 **{to_smallcaps('permalink')}** : [{target.first_name}](tg://user?id={target.id})"
        f"{format_watermark()}"
    )
    await message.reply_text(text)

@Client.on_message(filters.command("ping"))
async def ping_command_handler(client: Client, message: Message):
    start = time.time()
    reply = await message.reply_text(f"⚡ **{to_smallcaps('pinging engine...')}**")
    end = time.time()
    latency_ms = round((end - start) * 1000, 2)
    uptime_str = time_formatter(seconds=round(time.time() - BOT_START_TIME))

    text = (
        f"✦ **{to_smallcaps('system latency & uptime')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('ping')}** : `{latency_ms} ms`\n"
        f"• ⏱️ **{to_smallcaps('uptime')}** : `{uptime_str}`\n"
        f"• 🚀 **{to_smallcaps('stream mode')}** : `adaptive HTTP byte-range (4 Players)`\n"
        f"• 🌐 **{to_smallcaps('status')}** : `Operational (Fast)`"
        f"{format_watermark()}"
    )
    btn = [[InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="ping_refresh")]]
    await reply.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^ping_refresh$"))
async def ping_refresh_callback(client: Client, query: CallbackQuery):
    start = time.time()
    await query.answer(to_smallcaps("pinging..."))
    end = time.time()
    latency_ms = round((end - start) * 1000, 2)
    uptime_str = time_formatter(seconds=round(time.time() - BOT_START_TIME))

    text = (
        f"✦ **{to_smallcaps('system latency & uptime')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('ping')}** : `{latency_ms} ms`\n"
        f"• ⏱️ **{to_smallcaps('uptime')}** : `{uptime_str}`\n"
        f"• 🚀 **{to_smallcaps('stream mode')}** : `adaptive HTTP byte-range (4 Players)`\n"
        f"• 🌐 **{to_smallcaps('status')}** : `Operational (Fast)`"
        f"{format_watermark()}"
    )
    btn = [[InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="ping_refresh")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command(["speedtest", "speed"]))
async def speedtest_command_handler(client: Client, message: Message):
    status = await message.reply_text(f"🚀 **{to_smallcaps('measuring real server network latency...')}**")
    loop = asyncio.get_running_loop()

    targets = [
        ("Cloudflare DNS", "1.1.1.1", 53),
        ("Google DNS", "8.8.8.8", 53),
        ("Telegram DC", "149.154.167.50", 443),
    ]

    results = []
    for label, host, port in targets:
        def _test_sock():
            t0 = time.time()
            try:
                s = socket.create_connection((host, port), timeout=3)
                s.close()
                return round((time.time() - t0) * 1000, 2)
            except Exception:
                return -1
        ms = await loop.run_in_executor(None, _test_sock)
        results.append((label, ms))

    text = f"✦ **{to_smallcaps('server network latency report')}** ✦\n\n"
    for label, ms in results:
        val = f"`{ms} ms`" if ms > 0 else "`Timeout / Blocked`"
        text += f"• 🌐 **{to_smallcaps(label)}** : {val}\n"
    text += (
        f"\n• ⚡ **{to_smallcaps('stream mode')}** : `adaptive HTTP byte-range ready`\n"
        f"• ⏱️ **{to_smallcaps('server status')}** : `Operational & Ultra-Responsive`"
        f"{format_watermark()}"
    )
    await status.edit_text(text)

@Client.on_message(filters.command(["mediainfo", "probe"]))
async def mediainfo_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to a video, audio, or document.')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply to media with')} `/mediainfo`"
            f"{format_watermark()}"
        )
    await generate_mediainfo_response(client, target, message)

@Client.on_callback_query(filters.regex(r"^mediainfo_(\d+)"))
async def mediainfo_callback_entry(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("media not found!"), show_alert=True)
    await query.answer()
    await generate_mediainfo_response(client, original, query.message)

async def generate_mediainfo_response(client: Client, media_msg: Message, target_reply: Message):
    media = media_msg.video or media_msg.document or media_msg.audio
    raw_name = getattr(media, "file_name", None) or "sample_media"
    file_size_bytes = getattr(media, "file_size", 0)
    file_size_str = humanbytes(file_size_bytes)
    mime_type = getattr(media, "mime_type", "unknown")
    dur = getattr(media, "duration", 0)
    dur_str = time_formatter(seconds=dur) if dur > 0 else "N/A"
    width = getattr(media, "width", 0)
    height = getattr(media, "height", 0)

    if file_size_bytes > 25 * 1024 * 1024:
        res_str = f"{width}x{height}" if width and height else "N/A"
        text = (
            f"✦ **{to_smallcaps('media information')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('file name')}** : `{raw_name}`\n"
            f"• 📦 **{to_smallcaps('file size')}** : `{file_size_str}`\n"
            f"• 🏷️ **{to_smallcaps('mime type')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('duration')}** : `{dur_str}`\n"
            f"• 📐 **{to_smallcaps('resolution')}** : `{res_str}`\n\n"
            f"💡 {to_smallcaps('for external playback in playit, mx, vlc, or s player, use the stream button below:')}"
            f"{format_watermark()}"
        )
        buttons = [
            [InlineKeyboardButton(f"⚡ {to_smallcaps('adaptive stream link')}", callback_data=f"stream_{media_msg.id}")],
            [InlineKeyboardButton(f"❌ {to_smallcaps('close')}", callback_data="cancel_op")]
        ]
        return await target_reply.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    status = await target_reply.reply_text(f"🔍 **{to_smallcaps('extracting deep mediainfo with ffprobe...')}**")

    temp_dir = os.path.join(Config.DOWNLOAD_DIR, f"probe_{media_msg.id}_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, raw_name)

    try:
        await media_msg.download(file_name=temp_path)
    except Exception as e:
        clean_temp_files(temp_path, temp_dir)
        return await status.edit_text(f"❌ **{to_smallcaps('extraction failed')}** : `{e}`")

    info = await get_detailed_mediainfo(temp_path)
    clean_temp_files(temp_path, temp_dir)

    if not info:
        res_str = f"{width}x{height}" if width and height else "N/A"
        return await status.edit_text(
            f"✦ **{to_smallcaps('media information')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('file name')}** : `{raw_name}`\n"
            f"• 📦 **{to_smallcaps('file size')}** : `{file_size_str}`\n"
            f"• 🏷️ **{to_smallcaps('mime type')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('duration')}** : `{dur_str}`\n"
            f"• 📐 **{to_smallcaps('resolution')}** : `{res_str}`"
            f"{format_watermark()}"
        )

    container = info.get("container", "Unknown")
    dur_str = time_formatter(seconds=info.get("duration", 0))
    bitrate_str = f"{round(info.get('bitrate', 0) / 1000)} kbps" if info.get("bitrate") else "N/A"

    text = (
        f"✦ **{to_smallcaps('ffprobe media information')}** ✦\n\n"
        f"📁 **{to_smallcaps('file')}** : `{raw_name}`\n"
        f"📦 **{to_smallcaps('size')}** : `{file_size_str}`\n"
        f"📦 **{to_smallcaps('container')}** : `{container}`\n"
        f"⏱️ **{to_smallcaps('duration')}** : `{dur_str}`\n"
        f"📊 **{to_smallcaps('overall bitrate')}** : `{bitrate_str}`\n\n"
    )

    if info.get("video_streams"):
        for i, v in enumerate(info["video_streams"], 1):
            text += (
                f"🎬 **{to_smallcaps(f'video stream #{i}')}** :\n"
                f"  • 🏷️ **{to_smallcaps('codec')}** : `{v['codec']}` ({v['profile']})\n"
                f"  • 📐 **{to_smallcaps('resolution')}** : `{v['width']}x{v['height']}` ({v['aspect_ratio']})\n"
                f"  • 🎨 **{to_smallcaps('pixel format')}** : `{v['pix_fmt']}`\n"
                f"  • 🎞️ **{to_smallcaps('frame rate')}** : `{v['r_frame_rate']} fps`\n\n"
            )

    if info.get("audio_streams"):
        for i, a in enumerate(info["audio_streams"], 1):
            lang_val = a.get("language") or a.get("lang") or "Undetermined"
            text += (
                f"🔊 **{to_smallcaps(f'audio stream #{i}')}** :\n"
                f"  • 🏷️ **{to_smallcaps('codec')}** : `{a['codec']}`\n"
                f"  • 📻 **{to_smallcaps('channels')}** : `{a['channels']} ({a['channel_layout']})`\n"
                f"  • 🎚️ **{to_smallcaps('sampling')}** : `{a['sample_rate']} Hz`\n"
                f"  • 🌐 **{to_smallcaps('language')}** : `{lang_val}`\n\n"
            )

    if info.get("subtitle_streams"):
        text += f"📝 **{to_smallcaps('subtitles')}** :\n"
        for i, s in enumerate(info["subtitle_streams"], 1):
            lang_val = s.get("language") or s.get("lang") or "Undetermined"
            text += f"  • #{i} : `{s['codec']}` [{lang_val}] - {s['title']}\n"
        text += "\n"

    text += f"⚡ **{to_smallcaps('powered by')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
    btn = [[InlineKeyboardButton(f"❌ {to_smallcaps('close')}", callback_data="cancel_op")]]
    await status.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command("search"))
async def search_command_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('usage')}** : `/search <keyword>`\n\n"
            f"• **{to_smallcaps('example')}** : `/search sample`\n\n"
            f"💡 {to_smallcaps('searches your indexed stream files instantly.')}"
            f"{format_watermark()}"
        )

    query_str = message.text.split(None, 1)[1].strip()
    files = await file_repo.search_files(query_str, limit=10)

    if not files:
        return await message.reply_text(
            f"🔍 **{to_smallcaps('no files found matching')}** : `{query_str}`\n\n"
            f"💡 {to_smallcaps('try another search keyword.')}"
            f"{format_watermark()}"
        )

    text = f"✦ **{to_smallcaps('search results for')}** : `{query_str}` ✦\n\n"
    buttons = []
    for i, f in enumerate(files, 1):
        fname = f.get("file_name", "Media")
        fid = f.get("file_id")
        fsize = humanbytes(f.get("file_size", 0))
        text += f"{i}. 📁 **{fname}** (`{fsize}`)\n"
        buttons.append([
            InlineKeyboardButton(f"🎬 {i}. {to_smallcaps('watch (4 players)')}", url=f"{Config.BASE_URL}/watch/{fid}"),
            InlineKeyboardButton(f"⬇️ {to_smallcaps('download')}", url=f"{Config.BASE_URL}/download/{fid}")
        ])

    text += format_watermark()
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
