from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.utils.font import to_smallcaps, format_watermark

@Client.on_callback_query(filters.regex(r"^nav_(home|help|about|status|settings)"))
async def navigation_callbacks(client: Client, query: CallbackQuery):
    action = query.matches[0].group(1)
    user = query.from_user
    is_admin = user.id in Config.ADMINS

    if action == "home":
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
            f"• 🛠️ **{to_smallcaps('ᴛᴏᴏʟs & ᴇxᴛʀᴀs')}** : {to_smallcaps('ɪᴅ, ɪɴғᴏ, ᴘɪɴɢ, sᴘᴇᴇᴅᴛᴇsᴛ & ᴍᴇᴅɪᴀɪɴғᴏ')}\n"
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
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "help":
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
            f"• 🛠️ **{to_smallcaps('ᴛᴏᴏʟs')}** : {to_smallcaps('ɪᴅ, ɪɴғᴏ, ᴘɪɴɢ, sᴘᴇᴇᴅᴛᴇsᴛ & ᴍᴇᴅɪᴀɪɴғᴏ')}\n"
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

        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "about":
        about_text = (
            f"✦ **{to_smallcaps('ᴀʙᴏᴜᴛ ᴍᴍᴡ ᴀʟʟ-ɪɴ-ᴏɴᴇ ᴘʀᴏ')}** ✦\n\n"
            f"• 🤖 **{to_smallcaps('ʙᴏᴛ ɴᴀᴍᴇ')}** : `MMW All-In-One Pro`\n"
            f"• 💎 **{to_smallcaps('ᴇᴅɪᴛɪᴏɴ')}** : `v2.5.0 God-Mode Release`\n"
            f"• 🐍 **{to_smallcaps('ᴇɴɢɪɴᴇ')}** : `Python 3.10+ / Pyrofork (Non-blocking Async)`\n"
            f"• 🍃 **{to_smallcaps('ᴅᴀᴛᴀʙᴀsᴇ')}** : `MongoDB Motor with Indexing & Connection Pooling`\n"
            f"• 🎬 **{to_smallcaps('sᴛʀᴇᴀᴍᴇʀ')}** : `FastAPI + Plyr.js Engine (Byte-Accurate Range 206)`\n"
            f"• 🗜️ **{to_smallcaps('ᴄᴏᴍᴘʀᴇssᴏʀ')}** : `FFmpeg with YUV420p & Even-Dimension Enforcement`\n"
            f"• 💓 **{to_smallcaps('ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ')}** : `6 Concurrent Standard-Lib Pingers (6s Cycle)`\n"
            f"• 🔄 **{to_smallcaps('24ʜ ʀᴇsᴛᴀʀᴛ')}** : `Automatic Memory Sweeper & Daily Reboot Alerts`\n"
            f"• 🛡️ **{to_smallcaps('sᴇᴄᴜʀɪᴛʏ')}** : `Filename Sanitization & In-Memory Session Gen`"
            f"{format_watermark()}"
        )
        buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")]]
        await query.message.edit_text(about_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "status":
        users_count = await user_repo.get_total_users()
        chats_count = await chat_repo.get_total_chats()
        status_text = (
            f"✦ **{to_smallcaps('sʏsᴛᴇᴍ & ʙᴏᴛ sᴛᴀᴛᴜs')}** ✦\n\n"
            f"• 👥 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴜsᴇʀs')}** : `{users_count}`\n"
            f"• 📢 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴄʜᴀᴛs')}** : `{chats_count}`\n"
            f"• ⚡ **{to_smallcaps('ᴄᴀᴄʜɪɴɢ')}** : `FastMemoryCache (TTL Active)`\n"
            f"• 🌐 **{to_smallcaps('ᴡᴇʙ sᴇʀᴠᴇʀ')}** : `FastAPI Operational on Koyeb`\n"
            f"• 💓 **{to_smallcaps('ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ')}** : `6 Types Every 6s (Active)`\n"
            f"• 🔄 **{to_smallcaps('24ʜ ʀᴇsᴛᴀʀᴛ')}** : `Auto-Scheduled (Active)`\n"
            f"• 🚀 **{to_smallcaps('sᴇʀᴠᴇʀ sᴛᴀᴛᴜs')}** : `Online & Ultra-Fast`"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇғʀᴇsʜ')}", callback_data="nav_status"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")
            ]
        ]
        await query.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "settings":
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
        await query.message.edit_text(settings_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# Categorized Help Subpages
@Client.on_callback_query(filters.regex(r"^help_(renamer|compressor|streamer|thumbnail|caption|autodelete|session|cleaner|admin|tools)"))
async def help_subpages(client: Client, query: CallbackQuery):
    cat = query.matches[0].group(1)
    buttons = [
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ')}", callback_data="nav_help"),
            InlineKeyboardButton(f"🏠 {to_smallcaps('ʜᴏᴍᴇ')}", callback_data="nav_home")
        ]
    ]

    text = ""
    if cat == "renamer":
        text = (
            f"✦ **{to_smallcaps('ʀᴇɴᴀᴍᴇʀ — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• ✏️ **{to_smallcaps('ʜᴏᴡ ᴛᴏ ʀᴇɴᴀᴍᴇ ᴀ ғɪʟᴇ')}** :\n"
            f"  1. {to_smallcaps('sᴇɴᴅ ᴏʀ ғᴏʀᴡᴀʀᴅ ᴀɴʏ ғɪʟᴇ ᴏʀ ᴠɪᴅᴇᴏ ᴛᴏ ᴛʜᴇ ʙᴏᴛ.')}\n"
            f"  2. {to_smallcaps('ᴄʟɪᴄᴋ')} [✏️ {to_smallcaps('ʀᴇɴᴀᴍᴇ')}] {to_smallcaps('ᴏɴ ᴛʜᴇ ᴍᴇᴅɪᴀ ɪɴғᴏ ᴄᴀʀᴅ.')}\n"
            f"  3. {to_smallcaps('ᴛʏᴘᴇ ʏᴏᴜʀ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ (ɪɴᴄʟᴜᴅɪɴɢ ᴇxᴛᴇɴsɪᴏɴ, ᴇ.ɢ. movie.mkv).')}\n"
            f"  4. {to_smallcaps('ᴄʜᴏᴏsᴇ ᴡʜᴇᴛʜᴇʀ ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴀs ᴅᴏᴄᴜᴍᴇɴᴛ ᴏʀ sᴛʀᴇᴀᴍᴀʙʟᴇ ᴠɪᴅᴇᴏ.')}\n\n"
            f"• 🏷️ **{to_smallcaps('ғɪʟᴇ ᴘʀᴇғɪx & sᴜғғɪx')}** :\n"
            f"  • `/setprefix <text>` : {to_smallcaps('ᴀᴅᴅ ᴛᴇxᴛ ᴛᴏ ᴛʜᴇ sᴛᴀʀᴛ ᴏғ ᴀʟʟ ʀᴇɴᴀᴍᴇᴅ ғɪʟᴇs.')}\n"
            f"  • `/setsuffix <text>` : {to_smallcaps('ᴀᴅᴅ ᴛᴇxᴛ ʙᴇғᴏʀᴇ ᴛʜᴇ ᴇxᴛᴇɴsɪᴏɴ ᴏɴ ᴀʟʟ ғɪʟᴇs.')}\n"
            f"  • `/delprefix` : {to_smallcaps('ᴄʟᴇᴀʀ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴘʀᴇғɪx.')}\n"
            f"  • `/delsuffix` : {to_smallcaps('ᴄʟᴇᴀʀ ʏᴏᴜʀ sᴀᴠᴇᴅ sᴜғғɪx.')}\n\n"
            f"• 🛡️ **{to_smallcaps('sᴀɴɪᴛɪᴢᴀᴛɪᴏɴ')}** : {to_smallcaps('ᴀʟʟ ɪʟʟᴇɢᴀʟ ғɪʟᴇsʏsᴛᴇᴍ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴀʀᴇ ᴀᴜᴛᴏ-sᴛʀɪᴘᴘᴇᴅ.')}"
            f"{format_watermark()}"
        )
    elif cat == "compressor":
        text = (
            f"✦ **{to_smallcaps('ᴄᴏᴍᴘʀᴇssᴏʀ — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 🗜️ **{to_smallcaps('ʜᴏᴡ ᴛᴏ ᴄᴏᴍᴘʀᴇss ᴀ ᴠɪᴅᴇᴏ')}** :\n"
            f"  1. {to_smallcaps('sᴇɴᴅ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴡɪᴛʜ')} `/compress`.\n"
            f"  2. {to_smallcaps('ᴄʜᴏᴏsᴇ ᴀ ᴄᴏᴍᴘʀᴇssɪᴏɴ ǫᴜᴀʟɪᴛʏ ᴘʀᴇsᴇᴛ:')}\n"
            f"     • 𝟽𝟸𝟶ᴘ ʜᴅ : {to_smallcaps('ʙᴇsᴛ ʙᴀʟᴀɴᴄᴇ ᴏғ ᴄʟᴀʀɪᴛʏ ᴀɴᴅ sɪᴢᴇ sᴀᴠɪɴɢs.')}\n"
            f"     • 𝟺𝟾𝟶ᴘ sᴅ : {to_smallcaps('sᴜᴘᴇʀ-ғᴀsᴛ ᴇɴᴄᴏᴅɪɴɢ ғᴏʀ ᴍᴏʙɪʟᴇ ᴠɪᴇᴡɪɴɢ.')}\n"
            f"     • 𝟹𝟼𝟶ᴘ ʟᴏᴡ : {to_smallcaps('ᴍᴀxɪᴍᴜᴍ sɪᴢᴇ ʀᴇᴅᴜᴄᴛɪᴏɴ (ᴜᴘ ᴛᴏ 𝟾𝟶% sᴀᴠᴇᴅ).')}\n"
            f"     • 𝟷𝟶𝟾𝟶ᴘ ғᴜʟʟ ʜᴅ : {to_smallcaps('ʜɪɢʜ-ʙɪᴛʀᴀᴛᴇ ᴘʀᴇsᴇʀᴠᴀᴛɪᴏɴ ᴡɪᴛʜ ᴄʀғ 𝟸𝟺.')}\n\n"
            f"• ⚙️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴛᴇᴄʜɴɪᴄᴀʟ ɢᴜᴀʀᴀɴᴛᴇᴇs')}** :\n"
            f"  • {to_smallcaps('ᴇɴғᴏʀᴄᴇs yuv420p ᴘɪxᴇʟ ғᴏʀᴍᴀᴛ ғᴏʀ 𝟷𝟶𝟶% ᴘʟᴀʏᴇʀ ᴄᴏᴍᴘᴀᴛɪʙɪʟɪᴛʏ.')}\n"
            f"  • {to_smallcaps('ᴀᴜᴛᴏ-sᴄᴀʟᴇs ᴛᴏ ᴇᴠᴇɴ ᴅɪᴍᴇɴsɪᴏɴs ᴛᴏ ᴘʀᴇᴠᴇɴᴛ ᴇɴᴄᴏᴅᴇʀ ᴄʀᴀsʜᴇs.')}\n"
            f"  • {to_smallcaps('ᴘʀᴇsᴇʀᴠᴇs ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋs ᴀɴᴅ sᴜʙᴛɪᴛʟᴇs.')}"
            f"{format_watermark()}"
        )
    elif cat == "streamer":
        text = (
            f"✦ **{to_smallcaps('sᴛʀᴇᴀᴍᴇʀ — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• ⚡ **{to_smallcaps('ʜᴏᴡ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀ sᴛʀᴇᴀᴍ ʟɪɴᴋ')}** :\n"
            f"  1. {to_smallcaps('sᴇɴᴅ ᴀɴʏ ғɪʟᴇ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ғɪʟᴇ ᴡɪᴛʜ')} `/stream`.\n"
            f"  2. {to_smallcaps('ᴛʜᴇ ʙᴏᴛ ɪɴsᴛᴀɴᴛʟʏ ɢᴇɴᴇʀᴀᴛᴇs ʜɪɢʜ-sᴘᴇᴇᴅ ᴡᴇʙ & sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋs.')}\n\n"
            f"• 🎬 **{to_smallcaps('ᴡᴇʙ ᴘʟᴀʏᴇʀ ғᴇᴀᴛᴜʀᴇs')}** :\n"
            f"  • {to_smallcaps('ᴘʟʏʀ ᴠ𝟹 ᴘʟᴀʏᴇʀ ᴡɪᴛʜ sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟs, ᴘɪᴘ & ғᴜʟʟsᴄʀᴇᴇɴ.')}\n"
            f"  • {to_smallcaps('ʙʏᴛᴇ-ᴀᴄᴄᴜʀᴀᴛᴇ ʜᴛᴛᴘ 𝟸𝟶𝟼 ʀᴀɴɢᴇ sᴇᴇᴋɪɴɢ (ɴᴏ ʟᴀɢ/ʙᴜғғᴇʀɪɴɢ).')}\n\n"
            f"• 📱 **{to_smallcaps('ᴏɴᴇ-ᴄʟɪᴄᴋ ᴀɴᴅʀᴏɪᴅ ᴀᴘᴘ ɪɴᴛᴇɴᴛs')}** :\n"
            f"  • ᴍx ᴘʟᴀʏᴇʀ, ᴠʟᴄ, ᴘʟᴀʏɪᴛ, ᴋᴍᴘʟᴀʏᴇʀ & ᴊᴜsᴛᴘʟᴀʏᴇʀ."
            f"{format_watermark()}"
        )
    elif cat == "thumbnail":
        text = (
            f"✦ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 🖼️ **{to_smallcaps('sᴇᴛᴛɪɴɢ ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ')}** :\n"
            f"  • {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴘʜᴏᴛᴏ ᴡɪᴛʜ')} `/setthumb`.\n"
            f"  • {to_smallcaps('ᴏʀ ᴘᴀss ᴀ ᴅɪʀᴇᴄᴛ ɪᴍᴀɢᴇ ᴜʀʟ')}: `/setthumb <image_url>`.\n\n"
            f"• 👁️ **{to_smallcaps('ᴠɪᴇᴡ ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ')}** : `/thumb`\n"
            f"• 🗑️ **{to_smallcaps('ᴅᴇʟᴇᴛᴇ ᴛʜᴜᴍʙɴᴀɪʟ')}** : `/delthumb`\n\n"
            f"• ⚡ **{to_smallcaps('sᴍᴀʀᴛ ғᴀʟʟʙᴀᴄᴋ ᴄᴀᴄʜᴇ')}** :\n"
            f"  {to_smallcaps('ɪғ ɴᴏ ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ ɪs sᴇᴛ, ᴛʜᴇ ʙᴏᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴘᴘʟɪᴇs ʏᴏᴜʀ')} `THAM_URL` {to_smallcaps('ᴡɪᴛʜ ʟᴏᴄᴀʟ ᴅɪsᴋ ᴄᴀᴄʜɪɴɢ.')}"
            f"{format_watermark()}"
        )
    elif cat == "caption":
        text = (
            f"✦ **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴs — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('sᴇᴛ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ')}** :\n"
            f"  `/setcaption <template>`\n\n"
            f"• 🏷️ **{to_smallcaps('ᴀᴠᴀɪʟᴀʙʟᴇ ᴅʏɴᴀᴍɪᴄ ᴛᴀɢs')}** :\n"
            f"  • `{'{filename}'}` : {to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}\n"
            f"  • `{'{filesize}'}` : {to_smallcaps('ғɪʟᴇ sɪᴢᴇ')}\n"
            f"  • `{'{duration}'}` : {to_smallcaps('ᴠɪᴅᴇᴏ ʟᴇɴɢᴛʜ')}\n"
            f"  • `{'{ext}'}` : {to_smallcaps('ғɪʟᴇ ᴇxᴛᴇɴsɪᴏɴ')}\n"
            f"  • `{'{original_caption}'}` : {to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ᴄᴀᴘᴛɪᴏɴ')}\n"
            f"  • `{'{date}'}` : {to_smallcaps('ᴜᴛᴄ ᴛɪᴍᴇsᴛᴀᴍᴘ')}\n\n"
            f"• 📚 **{to_smallcaps('ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs ʟɪsᴛ (ᴄᴀᴘ[])')}** :\n"
            f"  • `/addcaption <template>` : {to_smallcaps('ᴀᴅᴅ ᴛᴏ ᴍᴜʟᴛɪ-ᴄᴀᴘᴛɪᴏɴ ǫᴜᴇᴜᴇ.')}\n"
            f"  • `/caption` : {to_smallcaps('ᴠɪᴇᴡ ᴀʟʟ ᴀᴄᴛɪᴠᴇ ᴀɴᴅ sᴀᴠᴇᴅ ᴄᴀᴘᴛɪᴏɴs.')}\n"
            f"  • `/delcaption` : {to_smallcaps('ʀᴇsᴇᴛ ᴄᴀᴘᴛɪᴏɴs ᴛᴏ ᴅᴇғᴀᴜʟᴛ.')}"
            f"{format_watermark()}"
        )
    elif cat == "autodelete":
        text = (
            f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ — ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴀɢᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• ⏱️ **{to_smallcaps('ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴍᴇssᴀɢᴇ ᴘᴜʀɢɪɴɢ')}** :\n"
            f"  {to_smallcaps('ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴄᴏɴᴛᴇɴᴛ ʙʏ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛɪɴɢ ʙᴏᴛ ᴏᴜᴛᴘᴜᴛ ғɪʟᴇs ᴀғᴛᴇʀ ᴀ sᴇᴛ ᴅᴜʀᴀᴛɪᴏɴ.')}\n\n"
            f"• ⚙️ **{to_smallcaps('ᴄᴏᴍᴍᴀɴᴅ ᴜsᴀɢᴇ')}** :\n"
            f"  • `/autodelete` : {to_smallcaps('ᴏᴘᴇɴ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ᴛɪᴍᴇʀ sᴇʟᴇᴄᴛɪᴏɴ ᴍᴇɴᴜ.')}\n"
            f"  • `/autodelete <seconds>` : {to_smallcaps('sᴇᴛ ᴀ ᴄᴜsᴛᴏᴍ ᴅᴜʀᴀᴛɪᴏɴ (ᴇ.ɢ. 𝟼𝟶𝟶 ғᴏʀ 𝟷𝟶 ᴍɪɴ).')}\n\n"
            f"• 🛡️ **{to_smallcaps('sᴀғᴇ ʙᴀᴛᴄʜ sᴡᴇᴇᴘɪɴɢ')}** :\n"
            f"  {to_smallcaps('ᴇxᴘɪʀᴇᴅ ᴍᴇssᴀɢᴇs ᴀʀᴇ ᴘᴜʀɢᴇᴅ ɪɴ ʙᴀᴛᴄʜᴇs ᴏғ ᴜᴘ ᴛᴏ 𝟷𝟶𝟶 ᴛᴏ ᴘʀᴇᴠᴇɴᴛ floodwait.')}"
            f"{format_watermark()}"
        )
    elif cat == "session":
        text = (
            f"✦ **{to_smallcaps('sᴛʀɪɴɢ sᴇssɪᴏɴ — ᴄᴏᴍᴘʟᴇᴛᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 🔑 **{to_smallcaps('ɢᴇɴᴇʀᴀᴛᴇ ᴛᴇʟᴇɢʀᴀᴍ sᴇssɪᴏɴ')}** :\n"
            f"  • {to_smallcaps('sᴜᴘᴘᴏʀᴛs ʙᴏᴛʜ')} **Pyrogram / Pyrofork** {to_smallcaps('ᴀɴᴅ')} **Telethon**.\n"
            f"  • {to_smallcaps('ɢᴇɴᴇʀᴀᴛᴇᴅ 𝟷𝟶𝟶% ɪɴ-ᴍᴇᴍᴏʀʏ (ɴᴏ sᴇssɪᴏɴ ғɪʟᴇs ᴡʀɪᴛᴛᴇɴ ᴛᴏ ᴅɪsᴋ).')}\n"
            f"  • {to_smallcaps('ғᴜʟʟ ᴛᴡᴏ-ғᴀᴄᴛᴏʀ ᴀᴜᴛʜᴇɴᴛɪᴄᴀᴛɪᴏɴ (𝟸ғᴀ) sᴜᴘᴘᴏʀᴛ.')}\n\n"
            f"• 🚀 **{to_smallcaps('ʜᴏᴡ ᴛᴏ sᴛᴀʀᴛ')}** :\n"
            f"  {to_smallcaps('ᴜsᴇ')} `/session` {to_smallcaps('ᴀɴᴅ ғᴏʟʟᴏᴡ ᴛʜᴇ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ sᴛᴇᴘ-ʙʏ-sᴛᴇᴘ ᴘʀᴏᴍᴘᴛs.')}\n\n"
            f"• 🔒 **{to_smallcaps('sᴇᴄᴜʀɪᴛʏ ᴡᴀʀɴɪɴɢ')}** :\n"
            f"  {to_smallcaps('ɴᴇᴠᴇʀ sʜᴀʀᴇ ʏᴏᴜʀ sᴇssɪᴏɴ sᴛʀɪɴɢ ᴡɪᴛʜ ᴀɴʏᴏɴᴇ! ᴛʜᴇ ʙᴏᴛ sᴇɴᴅs ʏᴏᴜʀ sᴇssɪᴏɴ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs.')}"
            f"{format_watermark()}"
        )
    elif cat == "cleaner":
        text = (
            f"✦ **{to_smallcaps('sᴇʀᴠɪᴄᴇ ᴄʟᴇᴀɴᴇʀ — ᴄᴏᴍᴘʟᴇᴛᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 🧹 **{to_smallcaps('ᴀᴜᴛᴏᴍᴀᴛɪᴄ sᴇʀᴠɪᴄᴇ ᴄʟᴇᴀɴᴇʀ')}** :\n"
            f"  {to_smallcaps('ᴀᴅᴅ ᴛʜᴇ ʙᴏᴛ ᴀs ᴀɴ ᴀᴅᴍɪɴ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴛᴏ ɪɴsᴛᴀɴᴛʟʏ ᴅᴇʟᴇᴛᴇ:')}\n"
            f"  • {to_smallcaps('ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴊᴏɪɴᴇᴅ ɴᴏᴛɪᴄᴇs')}\n"
            f"  • {to_smallcaps('ᴍᴇᴍʙᴇʀ ʟᴇғᴛ ɴᴏᴛɪᴄᴇs')}\n"
            f"  • {to_smallcaps('ᴘɪɴɴᴇᴅ ᴍᴇssᴀɢᴇ ɴᴏᴛɪᴄᴇs')}\n"
            f"  • {to_smallcaps('ᴄʜᴀᴛ ᴛɪᴛʟᴇ & ᴘʜᴏᴛᴏ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇs')}\n\n"
            f"• 🗑️ **{to_smallcaps('ᴍᴀɴᴜᴀʟ ᴘᴜʀɢᴇ')}** :\n"
            f"  • `/clean <count>` : {to_smallcaps('ᴘᴜʀɢᴇ ʀᴇᴄᴇɴᴛ ᴍᴇssᴀɢᴇs (ᴜᴘ ᴛᴏ 𝟷𝟶𝟶).')}"
            f"{format_watermark()}"
        )
    elif cat == "tools":
        text = (
            f"✦ **{to_smallcaps('ᴛᴏᴏʟs & ᴇxᴛʀᴀs — ᴄᴏᴍᴘʟᴇᴛᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 🆔 **{to_smallcaps('ᴜsᴇʀ & ᴄʜᴀᴛ ɪᴅ')}** :\n"
            f"  • `/id` : {to_smallcaps('ᴠɪᴇᴡ ʏᴏᴜʀ ᴜsᴇʀ ɪᴅ, ᴅᴀᴛᴀᴄᴇɴᴛᴇʀ (ᴅᴄ), ᴄʜᴀᴛ ɪᴅ & ᴍᴇssᴀɢᴇ ɪᴅ.')}\n"
            f"  • `/info` : {to_smallcaps('ᴠɪᴇᴡ ᴅᴇᴛᴀɪʟᴇᴅ ᴘʀᴏғɪʟᴇ ᴄᴀʀᴅ ᴏғ ᴀɴʏ ᴜsᴇʀ.')}\n\n"
            f"• ⚡ **{to_smallcaps('ʟᴀᴛᴇɴᴄʏ & sᴘᴇᴇᴅ')}** :\n"
            f"  • `/ping` : {to_smallcaps('ᴍᴇᴀsᴜʀᴇ ʀᴇᴀʟ-ᴛɪᴍᴇ ʙᴏᴛ ʀᴇsᴘᴏɴsᴇ ʟᴀᴛᴇɴᴄʏ ᴀɴᴅ ᴜᴘᴛɪᴍᴇ.')}\n"
            f"  • `/speedtest` : {to_smallcaps('ʀᴜɴ ɴᴇᴛᴡᴏʀᴋ ʙᴀɴᴅᴡɪᴅᴛʜ sᴘᴇᴇᴅᴛᴇsᴛ.')}\n\n"
            f"• 🔍 **{to_smallcaps('ғғᴘʀᴏʙᴇ ᴍᴇᴅɪᴀɪɴғᴏ')}** :\n"
            f"  • `/mediainfo` : {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴠɪᴅᴇᴏ/ᴀᴜᴅɪᴏ ᴛᴏ ɪɴsᴘᴇᴄᴛ ᴄᴏᴅᴇᴄs, ʙɪᴛʀᴀᴛᴇ, ʀᴇsᴏʟᴜᴛɪᴏɴ & ᴛʀᴀᴄᴋs.')}\n\n"
            f"• 🔎 **{to_smallcaps('ғɪʟᴇ sᴇᴀʀᴄʜ')}** :\n"
            f"  • `/search <keyword>` : {to_smallcaps('sᴇᴀʀᴄʜ ɪɴᴅᴇxᴇᴅ sᴛʀᴇᴀᴍ ғɪʟᴇs.')}\n\n"
            f"• ❌ **{to_smallcaps('ᴜɴɪᴠᴇʀsᴀʟ ᴄᴀɴᴄᴇʟ')}** :\n"
            f"  • `/cancel` : {to_smallcaps('ᴀʙᴏʀᴛ ᴀɴʏ ᴘᴇɴᴅɪɴɢ ᴏᴘᴇʀᴀᴛɪᴏɴ ᴏʀ ɪɴᴘᴜᴛ ᴘʀᴏᴍᴘᴛ.')}"
            f"{format_watermark()}"
        )
    elif cat == "admin":
        text = (
            f"✦ **{to_smallcaps('ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ — ᴄᴏᴍᴘʟᴇᴛᴇ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 👑 **{to_smallcaps('ᴀᴅᴍɪɴɪsᴛʀᴀᴛɪᴠᴇ ᴄᴏᴍᴍᴀɴᴅs')}** :\n"
            f"  • `/admin` : {to_smallcaps('ᴏᴘᴇɴ ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ ᴡɪᴛʜ ʟɪᴠᴇ ᴍᴇᴛʀɪᴄs.')}\n"
            f"  • `/broadcast` : {to_smallcaps('ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇs ᴛᴏ ᴀʟʟ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴜsᴇʀs.')}\n"
            f"  • `/ban <user_id>` : {to_smallcaps('ʙᴀɴ ᴀ ᴜsᴇʀ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ.')}\n"
            f"  • `/unban <user_id>` : {to_smallcaps('ᴜɴʙᴀɴ ᴀ ᴘʀᴇᴠɪᴏᴜsʟʏ ʙᴀɴɴᴇᴅ ᴜsᴇʀ.')}\n"
            f"  • `/restart` : {to_smallcaps('sᴀғᴇʟʏ ʀᴇʙᴏᴏᴛ ᴛʜᴇ ʙᴏᴛ ᴘʀᴏᴄᴇss.')}"
            f"{format_watermark()}"
        )

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# Settings View & Actions
@Client.on_callback_query(filters.regex(r"^settings_(view_thumb|view_caption|reset_all)"))
async def settings_actions(client: Client, query: CallbackQuery):
    action = query.matches[0].group(1)
    user_id = query.from_user.id
    buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")]]

    if action == "view_thumb":
        u = await user_repo.get_user(user_id)
        thumb_id = u.get("thumb_id") if u else None
        if thumb_id:
            await query.answer()
            await query.message.reply_photo(
                photo=thumb_id,
                caption=f"🖼️ **{to_smallcaps('ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ')}**{format_watermark()}"
            )
        else:
            tham_url = (u.get("tham_url") if u else None) or Config.THAM_URL
            await query.message.edit_text(
                f"ℹ️ **{to_smallcaps('ɴᴏ ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ ᴛʜᴜᴍʙɴᴀɪʟ sᴇᴛ.')}**\n\n"
                f"• 🔗 **{to_smallcaps('ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴛʜᴀᴍ_ᴜʀʟ')}** : `{tham_url}`\n\n"
                f"💡 {to_smallcaps('ᴛᴏ sᴇᴛ ᴀ ᴘʜᴏᴛᴏ, ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ɪᴍᴀɢᴇ ᴡɪᴛʜ')} `/setthumb`."
                f"{format_watermark()}",
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )

    elif action == "view_caption":
        u = await user_repo.get_user(user_id)
        c = u.get("custom_caption") if u else None
        cap_list = u.get("captions_list", []) if u else []
        text = f"✦ **{to_smallcaps('ʏᴏᴜʀ ᴄᴀᴘᴛɪᴏɴ sᴇᴛᴛɪɴɢs')}** ✦\n\n"
        if c:
            text += f"• 📝 **{to_smallcaps('ᴀᴄᴛɪᴠᴇ ᴄᴀᴘᴛɪᴏɴ')}** :\n`{c}`\n\n"
        else:
            text += f"• 📝 **{to_smallcaps('ᴀᴄᴛɪᴠᴇ ᴄᴀᴘᴛɪᴏɴ')}** : `{to_smallcaps('ᴅᴇғᴀᴜʟᴛ (ғᴀʟʟʙᴀᴄᴋ ᴛᴏ ғɪʟᴇ ᴄᴀᴘᴛɪᴏɴ)')}`\n\n"

        if cap_list:
            text += f"📚 **{to_smallcaps('sᴀᴠᴇᴅ ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs (ᴄᴀᴘ[])')}** :\n"
            for i, cap in enumerate(cap_list, 1):
                text += f"{i}. `{cap}`\n"
            text += "\n"

        text += f"💡 {to_smallcaps('ᴜsᴇ')} `/setcaption <template>` {to_smallcaps('ᴛᴏ ᴜᴘᴅᴀᴛᴇ.')}"
        text += f"{format_watermark()}"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "reset_all":
        await user_repo.update_user(user_id, {
            "thumb_id": None,
            "custom_caption": None,
            "captions_list": [],
            "prefix": None,
            "suffix": None,
            "auto_delete_time": 0
        })
        await query.answer(to_smallcaps("ᴀʟʟ sᴇᴛᴛɪɴɢs ʀᴇsᴇᴛ!"), show_alert=True)
        await query.message.edit_text(
            f"✅ **{to_smallcaps('ᴀʟʟ ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ sᴇᴛᴛɪɴɢs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴇᴛ ᴛᴏ ᴅᴇғᴀᴜʟᴛ!')}**"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
