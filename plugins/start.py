from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from plugins.core_db import user_repo, chat_repo, file_repo
from plugins.core_utils import to_smallcaps, format_watermark, logger

@Client.on_message(filters.private & filters.command(["start", "help", "about", "status", "settings"]))
async def command_start_family(client: Client, message: Message):
    user = message.from_user
    cmd = message.command[0].lower() if message.command else "start"

    if await user_repo.is_banned(user.id):
        return await message.reply_text(
            f"🚫 **{to_smallcaps('you are banned from using this bot.')}**\n\n"
            f"⚠️ **{to_smallcaps('reason')}** : `{to_smallcaps('violation of terms or admin restriction')}`"
            f"{format_watermark()}"
        )

    await user_repo.get_or_create(user.id, user.first_name, user.username)

    if Config.FORCE_SUB_CHANNEL:
        try:
            member = await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user.id)
            if member.status in ["kicked", "left"]:
                raise Exception()
        except Exception:
            invite_link = Config.FORCE_SUB_CHANNEL if str(Config.FORCE_SUB_CHANNEL).startswith("http") else f"https://t.me/{Config.FORCE_SUB_CHANNEL.replace('@', '')}"
            btn = [
                [InlineKeyboardButton(f"📢 {to_smallcaps('join official channel')}", url=invite_link)],
                [InlineKeyboardButton(f"🔄 {to_smallcaps('verify & continue')}", callback_data="nav_home")]
            ]
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('access requires channel membership')}**\n\n"
                f"👋 **{to_smallcaps('hello')} {user.mention}** !\n"
                f"{to_smallcaps('you must join our official updates channel to unlock all bot features.')}\n\n"
                f"⚡ {to_smallcaps('click the button below to join, then click verify!')}"
                f"{format_watermark()}",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True
            )

    if cmd == "start" and len(message.command) > 1:
        payload = message.command[1].strip()
        file_id = payload
        if payload.startswith("file_"):
            file_id = payload[5:]
        elif payload.startswith("getfile_"):
            file_id = payload[8:]
        elif payload.startswith("get_"):
            file_id = payload[4:]

        file_doc = await file_repo.get_file(file_id)
        if file_doc:
            try:
                msg = await client.get_messages(file_doc["chat_id"], file_doc["message_id"])
                if msg and msg.media:
                    await msg.copy(chat_id=message.chat.id)
                    return
                else:
                    return await message.reply_text(f"❌ **{to_smallcaps('original media no longer exists in storage channel!')}**")
            except Exception as e:
                logger.error(f"Error copying media file for start payload {file_id}: {e}")
                return await message.reply_text(f"❌ **{to_smallcaps('failed to send file')}** : `{e}`")
        else:
            return await message.reply_text(
                f"❌ **{to_smallcaps('file not found or stream link has been revoked!')}**"
                f"{format_watermark()}"
            )

    is_admin = user.id in Config.ADMINS

    if cmd == "start":
        text = (
            f"✦ **{to_smallcaps('mmw all-in-one pro')}** ✦\n\n"
            f"👋 **{to_smallcaps('hello')} {user.mention}** !\n\n"
            f"🚀 **{to_smallcaps('welcome to your ultra-fast multi-purpose pro bot!')}**\n\n"
            f"💎 **{to_smallcaps('all auto & pro features')}** :\n"
            f"• ✏️ **{to_smallcaps('auto & pro renamer')}** : {to_smallcaps('rename with custom prefix, suffix & thumb')}\n"
            f"• 🗜️ **{to_smallcaps('auto & pro compressor')}** : {to_smallcaps('ffmpeg h.264 presets & target size')}\n"
            f"• ⚡ **{to_smallcaps('12 mb/s fast streamer')}** : {to_smallcaps('http 206 range + 4 external players only (playit, mx, vlc, s player)')}\n"
            f"• 📝 **{to_smallcaps('auto dynamic captions')}** : {to_smallcaps('full templating ({filename}, {filesize}, cap[])')}\n"
            f"• 🤝 **{to_smallcaps('auto accept joins')}** : {to_smallcaps('instantly accept channel & group requests')}\n"
            f"• 🖼️ **{to_smallcaps('smart thumbnails')}** : {to_smallcaps('custom photo + tham_url auto-fallback')}\n"
            f"• ⏱️ **{to_smallcaps('auto-delete timer')}** : {to_smallcaps('scheduled batch message sweeper')}\n"
            f"• 🎛️ **{to_smallcaps('file pro studio')}** : {to_smallcaps('mediainfo, extract/add audio & subs, trim')}\n"
            f"• 🔑 **{to_smallcaps('string session')}** : {to_smallcaps('in-memory pyrogram & telethon generator')}\n"
            f"• 👑 **{to_smallcaps('admin control')}** : {to_smallcaps('single db, fast cache, broadcast & stats')}\n\n"
            f"💡 **{to_smallcaps('quick start')}** : {to_smallcaps('send or forward any file or video to start!')}"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"📖 {to_smallcaps('help guide')}", callback_data="nav_help"),
                InlineKeyboardButton(f"⚙️ {to_smallcaps('settings & auto')}", callback_data="nav_settings")
            ],
            [
                InlineKeyboardButton(f"📊 {to_smallcaps('system status')}", callback_data="nav_status"),
                InlineKeyboardButton(f"ℹ️ {to_smallcaps('about bot')}", callback_data="nav_about")
            ]
        ]
        if is_admin:
            buttons.append([InlineKeyboardButton(f"👑 {to_smallcaps('admin control panel')}", callback_data="admin_panel_back")])
        buttons.append([
            InlineKeyboardButton(f"📢 {to_smallcaps('official channel')}", url=Config.WATERMARK_URL)
        ])

        await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif cmd == "help":
        from plugins.callbacks import render_help_menu
        await render_help_menu(message, user, is_admin, is_edit=False)

    elif cmd == "settings":
        from plugins.callbacks import render_settings_menu
        await render_settings_menu(message, user, is_edit=False)

    elif cmd in ["about", "status"]:
        users_count = await user_repo.get_total_users()
        chats_count = await chat_repo.get_total_chats()
        files_count = await file_repo.get_total_files()
        text = (
            f"✦ **{to_smallcaps('system & bot status')}** ✦\n\n"
            f"• 🤖 **{to_smallcaps('bot name')}** : `MMW All-In-One Pro`\n"
            f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s (HTTP 206 Range)`\n"
            f"• 📱 **{to_smallcaps('4 external players')}** : `PLAYit • MX • VLC • S Player`\n"
            f"• 👥 **{to_smallcaps('total users')}** : `{users_count}`\n"
            f"• 📢 **{to_smallcaps('total chats')}** : `{chats_count}`\n"
            f"• 📁 **{to_smallcaps('indexed files')}** : `{files_count}`\n"
            f"• 🍃 **{to_smallcaps('database')}** : `Single Unified MongoDB + O(1) Cache`\n"
            f"• 🚀 **{to_smallcaps('server health')}** : `Operational & Ultra-Fast`"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="nav_status"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")
            ]
        ]
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
