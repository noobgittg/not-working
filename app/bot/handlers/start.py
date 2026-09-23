from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.font import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command(["start", "help", "about", "status", "settings"]))
async def command_start_family(client: Client, message: Message):
    user = message.from_user
    cmd = message.command[0].lower() if message.command else "start"

    # Check if banned
    if await user_repo.is_banned(user.id):
        return await message.reply_text(
            f"🚫 **{to_smallcaps('ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.')}**\n\n"
            f"⚠️ **{to_smallcaps('ʀᴇᴀsᴏɴ')}** : `{to_smallcaps('ᴠɪᴏʟᴀᴛɪᴏɴ ᴏғ ᴛᴇʀᴍs ᴏʀ ᴀᴅᴍɪɴ ʀᴇsᴛʀɪᴄᴛɪᴏɴ')}`"
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
                [InlineKeyboardButton(f"📢 {to_smallcaps('ᴊᴏɪɴ ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ')}", url=invite_link)],
                [InlineKeyboardButton(f"🔄 {to_smallcaps('ᴠᴇʀɪғʏ & ᴄᴏɴᴛɪɴᴜᴇ')}", callback_data="nav_home")]
            ]
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('ᴀᴄᴄᴇss ʀᴇǫᴜɪʀᴇs ᴄʜᴀɴɴᴇʟ ᴍᴇᴍʙᴇʀsʜɪᴘ')}**\n\n"
                f"👋 **{to_smallcaps('ʜᴇʟʟᴏ')} {user.mention}** !\n"
                f"{to_smallcaps('ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴏғғɪᴄɪᴀʟ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜɴʟᴏᴄᴋ ᴀʟʟ ʙᴏᴛ ғᴇᴀᴛᴜʀᴇs.')}\n\n"
                f"⚡ {to_smallcaps('ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴊᴏɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴠᴇʀɪғʏ!')}"
                f"{format_watermark()}",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True
            )

    is_admin = user.id in Config.ADMINS

    if cmd == "start":
        text = (
            f"✦ **{to_smallcaps('ᴍᴍᴡ ᴀʟʟ-ɪɴ-ᴏɴᴇ ᴘʀᴏ')}** ✦\n\n"
            f"👋 **{to_smallcaps('ʜᴇʟʟᴏ')} {user.mention}** !\n\n"
            f"🚀 **{to_smallcaps('ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴜʟᴛʀᴀ-ғᴀsᴛ ᴍᴜʟᴛɪ-ᴘᴜʀᴘᴏsᴇ ᴘʀᴏ ʙᴏᴛ!')}**\n\n"
            f"💎 **{to_smallcaps('ᴇxᴘᴀɴᴅᴇᴅ ғᴇᴀᴛᴜʀᴇ sᴜɪᴛᴇ')}** :\n"
            f"• ✏️ **{to_smallcaps('ᴜʟᴛʀᴀ-ғᴀsᴛ ʀᴇɴᴀᴍᴇʀ')}** : {to_smallcaps('ʀᴇɴᴀᴍᴇ ᴡɪᴛʜ ᴄᴜsᴛᴏᴍ ᴘʀᴇғɪx, sᴜғғɪx & ᴛʏᴘᴇ')}\n"
            f"• 🗜️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssᴏʀ')}** : {to_smallcaps('sᴜᴘᴇʀ-ғᴀsᴛ ʜ.𝟸𝟼𝟺 ᴄᴏᴍᴘʀᴇssɪᴏɴ & ᴘʀᴇsᴇᴛs')}\n"
            f"• ⚡ **{to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ sᴛʀᴇᴀᴍᴇʀ')}** : {to_smallcaps('ʜᴛᴛᴘ 𝟸𝟶𝟼 ʀᴀɴɢᴇ sᴇᴇᴋɪɴɢ & ᴘʟʏʀ ᴡᴇʙ ᴘʟᴀʏᴇʀ')}\n"
            f"• 🖼️ **{to_smallcaps('sᴍᴀʀᴛ ᴛʜᴜᴍʙɴᴀɪʟs')}** : {to_smallcaps('ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ + ᴛʜᴀᴍ_ᴜʀʟ ᴀᴜᴛᴏ-ғᴀʟʟʙᴀᴄᴋ')}\n"
            f"• 📝 **{to_smallcaps('ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs')}** : {to_smallcaps('ғᴜʟʟ ᴛᴇᴍᴘʟᴀᴛɪɴɢ ({filename}, {filesize}, cap[])')}\n"
            f"• ⏱️ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ')}** : {to_smallcaps('sᴄʜᴇᴅᴜʟᴇᴅ ʙᴀᴛᴄʜ ᴍᴇssᴀɢᴇ sᴡᴇᴇᴘᴇʀ')}\n"
            f"• 🤝 **{to_smallcaps('ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇ ᴊᴏɪɴs')}** : {to_smallcaps('ɪɴsᴛᴀɴᴛʟʏ ᴀᴄᴄᴇᴘᴛ ᴄʜᴀɴɴᴇʟ & ɢʀᴏᴜᴘ ʀᴇǫᴜᴇsᴛs')}\n"
            f"• 🧹 **{to_smallcaps('sᴇʀᴠɪᴄᴇ ᴄʟᴇᴀɴᴇʀ')}** : {to_smallcaps('ᴀᴜᴛᴏ-ᴘᴜʀɢᴇ sᴇʀᴠɪᴄᴇ ɴᴏᴛɪᴄᴇs & ᴍᴀɴᴜᴀʟ ᴄʟᴇᴀɴ')}\n"
            f"• 🔑 **{to_smallcaps('sᴛʀɪɴɢ sᴇssɪᴏɴ')}** : {to_smallcaps('ɪɴ-ᴍᴇᴍᴏʀʏ ᴘʏʀᴏɢʀᴀᴍ & ᴛᴇʟᴇᴛʜᴏɴ ɢᴇɴᴇʀᴀᴛᴏʀ')}\n"
            f"• 👑 **{to_smallcaps('ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ')}** : {to_smallcaps('ʟɪᴠᴇ ᴍᴇᴛʀɪᴄs, ʙʀᴏᴀᴅᴄᴀsᴛ & ᴜsᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ')}\n\n"
            f"💡 **{to_smallcaps('ǫᴜɪᴄᴋ sᴛᴀʀᴛ')}** : {to_smallcaps('sᴇɴᴅ ᴏʀ ғᴏʀᴡᴀʀᴅ ᴀɴʏ ғɪʟᴇ ᴏʀ ᴠɪᴅᴇᴏ ᴛᴏ ᴏᴘᴇɴ ᴛʜᴇ sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ᴍᴇɴᴜ!')}"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"📖 {to_smallcaps('ʜᴇʟᴘ ɢᴜɪᴅᴇ')}", callback_data="nav_help"),
                InlineKeyboardButton(f"⚙️ {to_smallcaps('sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")
            ],
            [
                InlineKeyboardButton(f"📊 {to_smallcaps('sʏsᴛᴇᴍ sᴛᴀᴛᴜs')}", callback_data="nav_status"),
                InlineKeyboardButton(f"ℹ️ {to_smallcaps('ᴀʙᴏᴜᴛ ʙᴏᴛ')}", callback_data="nav_about")
            ]
        ]
        if is_admin:
            buttons.append([InlineKeyboardButton(f"👑 {to_smallcaps('ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ')}", callback_data="admin_panel_back")])
        buttons.append([
            InlineKeyboardButton(f"📢 {to_smallcaps('ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ')}", url=Config.WATERMARK_URL)
        ])

        await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif cmd == "help":
        help_text = (
            f"✦ **{to_smallcaps('sᴍᴀʀᴛ ʜᴇʟᴘ ᴄᴇɴᴛᴇʀ')}** ✦\n\n"
            f"👋 **{to_smallcaps('ʜᴇʟʟᴏ')} {user.mention}** !\n"
            f"{to_smallcaps('ᴇxᴘʟᴏʀᴇ ᴏᴜʀ ᴄᴀᴛᴇɢᴏʀɪᴢᴇᴅ ɢᴜɪᴅᴇs ʙᴇʟᴏᴡ ғᴏʀ ᴅᴇᴛᴀɪʟᴇᴅ ɪɴsᴛʀᴜᴄᴛɪᴏɴs ᴀɴᴅ ᴇxᴀᴍᴘʟᴇs:')}\n\n"
            f"• ✏️ **{to_smallcaps('ʀᴇɴᴀᴍᴇʀ')}** : {to_smallcaps('ғɪʟᴇ ʀᴇɴᴀᴍɪɴɢ, ᴘʀᴇғɪx, sᴜғғɪx, ᴍᴏᴅᴇ ᴄᴏɴᴠᴇʀsɪᴏɴ')}\n"
            f"• 🗜️ **{to_smallcaps('ᴄᴏᴍᴘʀᴇssᴏʀ')}** : {to_smallcaps('ᴠɪᴅᴇᴏ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴘʀᴇsᴇᴛs & ᴄʀғ ᴛᴜɴɪɴɢ')}\n"
            f"• ⚡ **{to_smallcaps('sᴛʀᴇᴀᴍᴇʀ')}** : {to_smallcaps('ᴡᴇʙ ᴘʟᴀʏᴇʀ, ʜᴛᴛᴘ 𝟸𝟶𝟼 ʟɪɴᴋs, ᴀᴘᴘ ɪɴᴛᴇɴᴛs')}\n"
            f"• 🖼️ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ')}** : {to_smallcaps('ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ ᴘʜᴏᴛᴏs & ᴛʜᴀᴍ_ᴜʀʟ ᴄᴀᴄʜɪɴɢ')}\n"
            f"• 📝 **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴs')}** : {to_smallcaps('ᴅʏɴᴀᴍɪᴄ ᴛᴇᴍᴘʟᴀᴛᴇs & ᴄᴀᴘ[] ǫᴜᴇᴜᴇ ᴍᴀɴᴀɢᴇʀ')}\n"
            f"• ⏱️ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ')}** : {to_smallcaps('ᴛɪᴍᴇᴅ ᴍᴇssᴀɢᴇ sᴄʜᴇᴅᴜʟɪɴɢ & ʙᴀᴛᴄʜ ᴄʟᴇᴀɴɪɴɢ')}\n"
            f"• 🔑 **{to_smallcaps('sᴇssɪᴏɴ')}** : {to_smallcaps('ᴘʏʀᴏɢʀᴀᴍ & ᴛᴇʟᴇᴛʜᴏɴ sᴛʀɪɴɢ sᴇssɪᴏɴ ɢᴇɴᴇʀᴀᴛɪᴏɴ')}\n"
            f"• 🧹 **{to_smallcaps('ᴄʟᴇᴀɴᴇʀ')}** : {to_smallcaps('ɢʀᴏᴜᴘ sᴇʀᴠɪᴄᴇ ᴍᴇssᴀɢᴇs ᴘᴜʀɢᴇʀ')}\n"
            f"• 🛠️ **{to_smallcaps('ᴛᴏᴏʟs')}** : {to_smallcaps('ɪᴅ, ɪɴғᴏ, ᴘɪɴɢ, sᴘᴇᴇᴅᴛᴇsᴛ, ᴍᴇᴅɪᴀɪɴғᴏ & sᴇᴀʀᴄʜ')}\n"
        )
        if is_admin:
            help_text += f"• 👑 **{to_smallcaps('ᴀᴅᴍɪɴ')}** : {to_smallcaps('ʙʀᴏᴀᴅᴄᴀsᴛ, ʙᴀɴ/ᴜɴʙᴀɴ & sʏsᴛᴇᴍ ʀᴇsᴛᴀʀᴛ')}\n"

        help_text += f"{format_watermark()}"

        buttons = [
            [
                InlineKeyboardButton(f"✏️ {to_smallcaps('ʀᴇɴᴀᴍᴇʀ')}", callback_data="help_renamer"),
                InlineKeyboardButton(f"🗜️ {to_smallcaps('ᴄᴏᴍᴘʀᴇssᴏʀ')}", callback_data="help_compressor")
            ],
            [
                InlineKeyboardButton(f"⚡ {to_smallcaps('sᴛʀᴇᴀᴍᴇʀ')}", callback_data="help_streamer"),
                InlineKeyboardButton(f"🖼️ {to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ')}", callback_data="help_thumbnail")
            ],
            [
                InlineKeyboardButton(f"📝 {to_smallcaps('ᴄᴀᴘᴛɪᴏɴs')}", callback_data="help_caption"),
                InlineKeyboardButton(f"⏱️ {to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ')}", callback_data="help_autodelete")
            ],
            [
                InlineKeyboardButton(f"🔑 {to_smallcaps('sᴇssɪᴏɴ')}", callback_data="help_session"),
                InlineKeyboardButton(f"🧹 {to_smallcaps('ᴄʟᴇᴀɴᴇʀ')}", callback_data="help_cleaner")
            ],
            [
                InlineKeyboardButton(f"🛠️ {to_smallcaps('ᴛᴏᴏʟs & ᴇxᴛʀᴀs')}", callback_data="help_tools"),
                InlineKeyboardButton(f"🌐 {to_smallcaps('ᴡᴇʙ ᴅᴀsʜʙᴏᴀʀᴅ')}", url=f"{Config.BASE_URL}/stats")
            ]
        ]
        if is_admin:
            buttons.append([InlineKeyboardButton(f"👑 {to_smallcaps('ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ')}", callback_data="help_admin")])
        buttons.append([InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")])

        await message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif cmd == "settings":
        u = await user_repo.get_user(user.id)
        has_thumb = "✅" if u and u.get("thumb_id") else "❌"
        has_caption = "✅" if u and (u.get("custom_caption") or u.get("captions_list")) else "❌"
        timer = u.get("auto_delete_time", 0) if u else 0
        timer_str = f"{timer}s" if timer > 0 else to_smallcaps("ᴅɪsᴀʙʟᴇᴅ")
        prefix_str = u.get("prefix") or to_smallcaps("ɴᴏɴᴇ")
        suffix_str = u.get("suffix") or to_smallcaps("ɴᴏɴᴇ")
        tham_url_str = u.get("tham_url") or Config.THAM_URL

        settings_text = (
            f"✦ **{to_smallcaps('sᴍᴀʀᴛ sᴇᴛᴛɪɴɢs ᴅᴀsʜʙᴏᴀʀᴅ')}** ✦\n\n"
            f"👤 **{to_smallcaps('ᴜsᴇʀ')}** : {user.mention} (`{user.id}`)\n\n"
            f"• 🖼️ **{to_smallcaps('ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ')}** : `{has_thumb}`\n"
            f"• 📝 **{to_smallcaps('ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ')}** : `{has_caption}`\n"
            f"• 🏷️ **{to_smallcaps('ғɪʟᴇ ᴘʀᴇғɪx')}** : `{prefix_str}`\n"
            f"• 🏷️ **{to_smallcaps('ғɪʟᴇ sᴜғғɪx')}** : `{suffix_str}`\n"
            f"• ⏱️ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ')}** : `{timer_str}`\n"
            f"• 🔗 **{to_smallcaps('ᴛʜᴀᴍ_ᴜʀʟ ғᴀʟʟʙᴀᴄᴋ')}** : `{tham_url_str}`\n\n"
            f"💡 **{to_smallcaps('ᴄʟɪᴄᴋ ᴀ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴍᴏᴅɪғʏ ᴀɴʏ sᴇᴛᴛɪɴɢ:')}**"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🖼️ {to_smallcaps('ᴠɪᴇᴡ ᴛʜᴜᴍʙ')}", callback_data="settings_view_thumb"),
                InlineKeyboardButton(f"📝 {to_smallcaps('ᴠɪᴇᴡ ᴄᴀᴘᴛɪᴏɴ')}", callback_data="settings_view_caption")
            ],
            [
                InlineKeyboardButton(f"⏱️ {to_smallcaps('ᴛɪᴍᴇʀ sᴇᴛᴛɪɴɢs')}", callback_data="open_timer_menu"),
                InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇsᴇᴛ ᴀʟʟ')}", callback_data="settings_reset_all")
            ],
            [
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")
            ]
        ]
        await message.reply_text(settings_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif cmd in ["about", "status"]:
        users_count = await user_repo.get_total_users()
        chats_count = await chat_repo.get_total_chats()
        text = (
            f"✦ **{to_smallcaps('sʏsᴛᴇᴍ & ʙᴏᴛ sᴛᴀᴛᴜs')}** ✦\n\n"
            f"• 🤖 **{to_smallcaps('ʙᴏᴛ ɴᴀᴍᴇ')}** : `MMW All-In-One Pro`\n"
            f"• 💎 **{to_smallcaps('ᴇᴅɪᴛɪᴏɴ')}** : `v2.5.0 Production`\n"
            f"• 👥 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴜsᴇʀs')}** : `{users_count}`\n"
            f"• 📢 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴄʜᴀᴛs')}** : `{chats_count}`\n"
            f"• ⚡ **{to_smallcaps('ᴄᴀᴄʜɪɴɢ')}** : `FastMemoryCache (TTL Active)`\n"
            f"• 💓 **{to_smallcaps('ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ')}** : `6 Types Every 6s (Active)`\n"
            f"• 🔄 **{to_smallcaps('24ʜ ʀᴇsᴛᴀʀᴛ')}** : `Auto-Scheduled (Active)`\n"
            f"• 🌐 **{to_smallcaps('ᴡᴇʙ sᴇʀᴠᴇʀ')}** : `FastAPI + Uvicorn (HTTP 206 Ready)`\n"
            f"• 🚀 **{to_smallcaps('sᴇʀᴠᴇʀ ʜᴇᴀʟᴛʜ')}** : `Operational & Ultra-Fast`"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇғʀᴇsʜ')}", callback_data="nav_status"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")
            ]
        ]
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
