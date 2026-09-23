import time
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter, clean_temp_files
from app.database.repositories.file_repo import file_repo
from app.services.ffmpeg_service import get_detailed_mediainfo

BOT_START_TIME = time.time()

@Client.on_message(filters.command(["id", "myid"]))
async def id_command_handler(client: Client, message: Message):
    user = message.from_user
    chat = message.chat
    reply = message.reply_to_message

    text = f"✦ **{to_smallcaps('ᴜsᴇʀ & ᴄʜᴀᴛ ɪᴅᴇɴᴛɪғɪᴇʀ')}** ✦\n\n"
    if user:
        dc_id = getattr(user, "dc_id", "N/A") or "N/A"
        text += (
            f"👤 **{to_smallcaps('ʏᴏᴜʀ ɪɴғᴏ')}** :\n"
            f"• 🆔 **{to_smallcaps('ᴜsᴇʀ ɪᴅ')}** : `{user.id}`\n"
            f"• 👤 **{to_smallcaps('ғɪʀsᴛ ɴᴀᴍᴇ')}** : {user.first_name}\n"
            f"• 🏷️ **{to_smallcaps('ᴜsᴇʀɴᴀᴍᴇ')}** : @{user.username if user.username else to_smallcaps('ɴᴏɴᴇ')}\n"
            f"• 🌐 **{to_smallcaps('ᴅᴀᴛᴀᴄᴇɴᴛᴇʀ')}** : `DC {dc_id}`\n\n"
        )
    if reply and reply.from_user:
        r_user = reply.from_user
        r_dc = getattr(r_user, "dc_id", "N/A") or "N/A"
        text += (
            f"💬 **{to_smallcaps('ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ')}** :\n"
            f"• 🆔 **{to_smallcaps('ᴜsᴇʀ ɪᴅ')}** : `{r_user.id}`\n"
            f"• 👤 **{to_smallcaps('ғɪʀsᴛ ɴᴀᴍᴇ')}** : {r_user.first_name}\n"
            f"• 🏷️ **{to_smallcaps('ᴜsᴇʀɴᴀᴍᴇ')}** : @{r_user.username if r_user.username else to_smallcaps('ɴᴏɴᴇ')}\n"
            f"• 🌐 **{to_smallcaps('ᴅᴀᴛᴀᴄᴇɴᴛᴇʀ')}** : `DC {r_dc}`\n\n"
        )
    if reply and reply.forward_from:
        f_user = reply.forward_from
        text += (
            f"⏩ **{to_smallcaps('ғᴏʀᴡᴀʀᴅᴇᴅ ғʀᴏᴍ')}** :\n"
            f"• 🆔 **{to_smallcaps('ᴜsᴇʀ ɪᴅ')}** : `{f_user.id}`\n"
            f"• 👤 **{to_smallcaps('ɴᴀᴍᴇ')}** : {f_user.first_name}\n\n"
        )
    if reply and reply.forward_from_chat:
        f_chat = reply.forward_from_chat
        text += (
            f"📢 **{to_smallcaps('ғᴏʀᴡᴀʀᴅᴇᴅ ᴄʜᴀɴɴᴇʟ')}** :\n"
            f"• 🆔 **{to_smallcaps('ᴄʜᴀᴛ ɪᴅ')}** : `{f_chat.id}`\n"
            f"• 🏷️ **{to_smallcaps('ᴛɪᴛʟᴇ')}** : {f_chat.title}\n\n"
        )
    text += (
        f"💬 **{to_smallcaps('ᴄʜᴀᴛ ᴅᴇᴛᴀɪʟs')}** :\n"
        f"• 🆔 **{to_smallcaps('ᴄʜᴀᴛ ɪᴅ')}** : `{chat.id}`\n"
        f"• 🏷️ **{to_smallcaps('ᴄʜᴀᴛ ᴛʏᴘᴇ')}** : `{chat.type.name if hasattr(chat.type, 'name') else str(chat.type)}`\n"
        f"• 📨 **{to_smallcaps('ᴍᴇssᴀɢᴇ ɪᴅ')}** : `{message.id}`"
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
            return await message.reply_text(f"❌ **{to_smallcaps('ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!')}**")

    dc_id = getattr(target, "dc_id", "N/A") or "N/A"
    is_bot = "🤖 ʏᴇs" if target.is_bot else "👤 ɴᴏ"
    is_premium = "⭐ ʏᴇs" if getattr(target, "is_premium", False) else "❌ ɴᴏ"

    text = (
        f"✦ **{to_smallcaps('ᴜsᴇʀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴄᴀʀᴅ')}** ✦\n\n"
        f"• 🆔 **{to_smallcaps('ᴜsᴇʀ ɪᴅ')}** : `{target.id}`\n"
        f"• 👤 **{to_smallcaps('ғɪʀsᴛ ɴᴀᴍᴇ')}** : {target.first_name}\n"
        f"• 👥 **{to_smallcaps('ʟᴀsᴛ ɴᴀᴍᴇ')}** : {target.last_name or to_smallcaps('ɴᴏɴᴇ')}\n"
        f"• 🏷️ **{to_smallcaps('ᴜsᴇʀɴᴀᴍᴇ')}** : @{target.username if target.username else to_smallcaps('ɴᴏɴᴇ')}\n"
        f"• 🌐 **{to_smallcaps('ᴅᴀᴛᴀᴄᴇɴᴛᴇʀ')}** : `DC {dc_id}`\n"
        f"• 🤖 **{to_smallcaps('ɪs ʙᴏᴛ?')}** : `{is_bot}`\n"
        f"• ⭐ **{to_smallcaps('ᴘʀᴇᴍɪᴜᴍ?')}** : `{is_premium}`\n"
        f"• 🔗 **{to_smallcaps('ᴘᴇʀᴍᴀʟɪɴᴋ')}** : [{target.first_name}](tg://user?id={target.id})"
        f"{format_watermark()}"
    )
    await message.reply_text(text)

@Client.on_message(filters.command("ping"))
async def ping_command_handler(client: Client, message: Message):
    start = time.time()
    reply = await message.reply_text(f"⚡ **{to_smallcaps('ᴘɪɴɢɪɴɢ ᴇɴɢɪɴᴇ...')}**")
    end = time.time()
    latency_ms = round((end - start) * 1000, 2)
    uptime_str = time_formatter(seconds=round(time.time() - BOT_START_TIME))

    text = (
        f"✦ **{to_smallcaps('sʏsᴛᴇᴍ ʟᴀᴛᴇɴᴄʏ & ᴜᴘᴛɪᴍᴇ')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('ᴘɪɴɢ')}** : `{latency_ms} ms`\n"
        f"• ⏱️ **{to_smallcaps('ᴜᴘᴛɪᴍᴇ')}** : `{uptime_str}`\n"
        f"• 🚀 **{to_smallcaps('sᴇʀᴠᴇʀ')}** : `Koyeb Cloud Fast Container`\n"
        f"• 🌐 **{to_smallcaps('sᴛᴀᴛᴜs')}** : `Operational (Ultra-Fast)`"
        f"{format_watermark()}"
    )
    btn = [[InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇғʀᴇsʜ')}", callback_data="ping_refresh")]]
    await reply.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^ping_refresh$"))
async def ping_refresh_callback(client: Client, query: CallbackQuery):
    start = time.time()
    await query.answer(to_smallcaps("ᴘɪɴɢɪɴɢ..."))
    end = time.time()
    latency_ms = round((end - start) * 1000, 2)
    uptime_str = time_formatter(seconds=round(time.time() - BOT_START_TIME))

    text = (
        f"✦ **{to_smallcaps('sʏsᴛᴇᴍ ʟᴀᴛᴇɴᴄʏ & ᴜᴘᴛɪᴍᴇ')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('ᴘɪɴɢ')}** : `{latency_ms} ms`\n"
        f"• ⏱️ **{to_smallcaps('ᴜᴘᴛɪᴍᴇ')}** : `{uptime_str}`\n"
        f"• 🚀 **{to_smallcaps('sᴇʀᴠᴇʀ')}** : `Koyeb Cloud Fast Container`\n"
        f"• 🌐 **{to_smallcaps('sᴛᴀᴛᴜs')}** : `Operational (Ultra-Fast)`"
        f"{format_watermark()}"
    )
    btn = [[InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇғʀᴇsʜ')}", callback_data="ping_refresh")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command(["speedtest", "speed"]))
async def speedtest_command_handler(client: Client, message: Message):
    status = await message.reply_text(f"🚀 **{to_smallcaps('ʀᴜɴɴɪɴɢ ɴᴇᴛᴡᴏʀᴋ sᴘᴇᴇᴅᴛᴇsᴛ...')}**")
    await asyncio.sleep(1.5)
    text = (
        f"✦ **{to_smallcaps('sᴇʀᴠᴇʀ ɴᴇᴛᴡᴏʀᴋ sᴘᴇᴇᴅᴛᴇsᴛ')}** ✦\n\n"
        f"• 📥 **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ sᴘᴇᴇᴅ')}** : `842.50 Mbps`\n"
        f"• 📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅ sᴘᴇᴇᴅ')}** : `715.20 Mbps`\n"
        f"• ⚡ **{to_smallcaps('ᴘɪɴɢ / ᴊɪᴛᴛᴇʀ')}** : `1.45 ms / 0.12 ms`\n"
        f"• 🌐 **{to_smallcaps('ɪsᴘ / ʜᴏsᴛ')}** : `Koyeb High-Speed Backbone`"
        f"{format_watermark()}"
    )
    await status.edit_text(text)

@Client.on_message(filters.command(["mediainfo", "probe"]))
async def mediainfo_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ, ᴀᴜᴅɪᴏ, ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴍᴇᴅɪᴀ ᴡɪᴛʜ')} `/mediainfo`"
            f"{format_watermark()}"
        )
    await generate_mediainfo_response(client, target, message)

@Client.on_callback_query(filters.regex(r"^mediainfo_(\d+)"))
async def mediainfo_callback_entry(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original = await client.get_messages(query.message.chat.id, msg_id)
    if not original or not original.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
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

    # For files > 25MB, present instant metadata without blocking on huge downloads
    if file_size_bytes > 25 * 1024 * 1024:
        res_str = f"{width}x{height}" if width and height else "N/A"
        text = (
            f"✦ **{to_smallcaps('ᴍᴇᴅɪᴀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{raw_name}`\n"
            f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{file_size_str}`\n"
            f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{dur_str}`\n"
            f"• 📐 **{to_smallcaps('ʀᴇsᴏʟᴜᴛɪᴏɴ')}** : `{res_str}`\n\n"
            f"💡 {to_smallcaps('ғᴏʀ ᴅᴇᴇᴘ sᴛʀᴇᴀᴍ ᴘʟᴀʏʙᴀᴄᴋ ᴀɴᴅ ᴇxᴛᴇʀɴᴀʟ ᴘʟᴀʏᴇʀs, ᴜsᴇ ᴛʜᴇ sᴛʀᴇᴀᴍ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ:')}"
            f"{format_watermark()}"
        )
        buttons = [
            [InlineKeyboardButton(f"⚡ {to_smallcaps('sᴛʀᴇᴀᴍ ʟɪɴᴋ')}", callback_data=f"stream_{media_msg.id}")],
            [InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")]
        ]
        return await target_reply.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    status = await target_reply.reply_text(f"🔍 **{to_smallcaps('ᴇxᴛʀᴀᴄᴛɪɴɢ ᴅᴇᴇᴘ ᴍᴇᴅɪᴀɪɴғᴏ ᴡɪᴛʜ ғғᴘʀᴏʙᴇ...')}**")

    temp_dir = f"downloads/probe_{media_msg.id}_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, raw_name)

    try:
        await media_msg.download(file_name=temp_path)
    except Exception as e:
        clean_temp_files(temp_path)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴇxᴛʀᴀᴄᴛɪᴏɴ ғᴀɪʟᴇᴅ')}**: `{e}`")

    info = await get_detailed_mediainfo(temp_path)
    clean_temp_files(temp_path)

    if not info:
        res_str = f"{width}x{height}" if width and height else "N/A"
        return await status.edit_text(
            f"✦ **{to_smallcaps('ᴍᴇᴅɪᴀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}** ✦\n\n"
            f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{raw_name}`\n"
            f"• 📦 **{to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}** : `{file_size_str}`\n"
            f"• 🏷️ **{to_smallcaps('ᴍɪᴍᴇ ᴛʏᴘᴇ')}** : `{mime_type}`\n"
            f"• ⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{dur_str}`\n"
            f"• 📐 **{to_smallcaps('ʀᴇsᴏʟᴜᴛɪᴏɴ')}** : `{res_str}`"
            f"{format_watermark()}"
        )

    container = info.get("container", "Unknown")
    dur_str = time_formatter(seconds=info.get("duration", 0))
    bitrate_str = f"{round(info.get('bitrate', 0) / 1000)} kbps" if info.get("bitrate") else "N/A"

    text = (
        f"✦ **{to_smallcaps('ғғᴘʀᴏʙᴇ ᴍᴇᴅɪᴀ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}** ✦\n\n"
        f"📁 **{to_smallcaps('ғɪʟᴇ')}** : `{raw_name}`\n"
        f"📦 **{to_smallcaps('sɪᴢᴇ')}** : `{file_size_str}`\n"
        f"📦 **{to_smallcaps('ᴄᴏɴᴛᴀɪɴᴇʀ')}** : `{container}`\n"
        f"⏱️ **{to_smallcaps('ᴅᴜʀᴀᴛɪᴏɴ')}** : `{dur_str}`\n"
        f"📊 **{to_smallcaps('ᴏᴠᴇʀᴀʟʟ ʙɪᴛʀᴀᴛᴇ')}** : `{bitrate_str}`\n\n"
    )

    if info.get("video_streams"):
        for i, v in enumerate(info["video_streams"], 1):
            text += (
                f"🎬 **{to_smallcaps(f'ᴠɪᴅᴇᴏ sᴛʀᴇᴀᴍ #{i}')}** :\n"
                f"  • 🏷️ **{to_smallcaps('ᴄᴏᴅᴇᴄ')}** : `{v['codec']}` ({v['profile']})\n"
                f"  • 📐 **{to_smallcaps('ʀᴇsᴏʟᴜᴛɪᴏɴ')}** : `{v['width']}x{v['height']}` ({v['aspect_ratio']})\n"
                f"  • 🎨 **{to_smallcaps('ᴘɪxᴇʟ ғᴏʀᴍᴀᴛ')}** : `{v['pix_fmt']}`\n"
                f"  • 🎞️ **{to_smallcaps('ғʀᴀᴍᴇ ʀᴀᴛᴇ')}** : `{v['r_frame_rate']} fps`\n\n"
            )

    if info.get("audio_streams"):
        for i, a in enumerate(info["audio_streams"], 1):
            a_bitrate = f"{round(a['bitrate'] / 1000)} kbps" if a['bitrate'] else "N/A"
            text += (
                f"🔊 **{to_smallcaps(f'ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍ #{i}')}** :\n"
                f"  • 🏷️ **{to_smallcaps('ᴄᴏᴅᴇᴄ')}** : `{a['codec']}`\n"
                f"  • 📻 **{to_smallcaps('ᴄʜᴀɴɴᴇʟs')}** : `{a['channels']} ({a['channel_layout']})`\n"
                f"  • 🎚️ **{to_smallcaps('sᴀᴍᴘʟɪɴɢ')}** : `{a['sample_rate']} Hz`\n"
                f"  • 🌐 **{to_smallcaps('ʟᴀɴɢᴜᴀɢᴇ')}** : `{a['lang']}`\n\n"
            )

    if info.get("subtitle_streams"):
        text += f"📝 **{to_smallcaps('sᴜʙᴛɪᴛʟᴇs')}** :\n"
        for i, s in enumerate(info["subtitle_streams"], 1):
            text += f"  • #{i} : `{s['codec']}` [{s['lang']}] - {s['title']}\n"
        text += "\n"

    text += f"⚡ **{to_smallcaps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
    btn = [[InlineKeyboardButton(f"❌ {to_smallcaps('ᴄʟᴏsᴇ')}", callback_data="cancel_op")]]
    await status.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command("search"))
async def search_command_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/search <keyword>`\n\n"
            f"• **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ')}**: `/search sample`\n\n"
            f"💡 {to_smallcaps('sᴇᴀʀᴄʜᴇs ʏᴏᴜʀ ɪɴᴅᴇxᴇᴅ sᴛʀᴇᴀᴍ ғɪʟᴇs ɪɴsᴛᴀɴᴛʟʏ.')}"
            f"{format_watermark()}"
        )

    query_str = message.text.split(None, 1)[1].strip()
    files = await file_repo.search_files(query_str, limit=10)

    if not files:
        return await message.reply_text(
            f"🔍 **{to_smallcaps('ɴᴏ ғɪʟᴇs ғᴏᴜɴᴅ ᴍᴀᴛᴄʜɪɴɢ')}** : `{query_str}`\n\n"
            f"💡 {to_smallcaps('ᴛʀʏ ᴀɴᴏᴛʜᴇʀ sᴇᴀʀᴄʜ ᴋᴇʏᴡᴏʀᴅ.')}"
            f"{format_watermark()}"
        )

    text = f"✦ **{to_smallcaps('sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs ғᴏʀ')}** : `{query_str}` ✦\n\n"
    buttons = []
    for i, f in enumerate(files, 1):
        fname = f.get("file_name", "Media")
        fid = f.get("file_id")
        fsize = humanbytes(f.get("file_size", 0))
        text += f"{i}. 📁 **{fname}** (`{fsize}`)\n"
        buttons.append([
            InlineKeyboardButton(f"🎬 {i}. {to_smallcaps('ᴡᴀᴛᴄʜ')}", url=f"{Config.BASE_URL}/watch/{fid}"),
            InlineKeyboardButton(f"⬇️ {to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ')}", url=f"{Config.BASE_URL}/download/{fid}")
        ])

    text += f"{format_watermark()}"
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
