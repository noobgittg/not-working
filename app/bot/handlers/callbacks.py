from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.font import to_smallcaps, format_watermark


@Client.on_callback_query(filters.regex(r"^(nav_home|nav_help|nav_settings|nav_status|nav_about)$"))
async def navigation_callbacks(client: Client, query: CallbackQuery):
    """Handle basic navigation callbacks used throughout the bot UI."""
    action = query.data or "nav_home"
    await query.answer()

    if action == "nav_home":
        text = (
            f"🏠 **{to_smallcaps('ʜᴏᴍᴇ')}**\n\n"
            f"👋 {to_smallcaps('ʏᴏᴜʀ ʙᴏᴛ ɪs ʀᴇᴀᴅʏ.')}\n"
            f"💡 {to_smallcaps('ᴜʟɪᴄᴋ /start ᴛᴏ ᴏᴘᴇɴ ᴛʜᴇ ғᴜʟʟ ᴍᴇɴᴜ.')}"
        )
    elif action == "nav_help":
        text = (
            f"📖 **{to_smallcaps('ʜᴇʟᴘ')}**\n\n"
            f"• {to_smallcaps('ʀᴇɴᴀᴍᴇ, ᴄᴏᴍᴘʀᴇss, sᴛʀᴇᴀᴍ, ᴀɴᴅ ᴄᴀᴘᴛɪᴏɴ ᴛᴏᴏʟs ᴀʀᴇ ᴀᴠᴀɪʟᴀʙʟᴇ.')}\n"
            f"• {to_smallcaps('uѕᴇ /help ғᴏʀ ᴛʜᴇ ᴄᴏᴍᴩʟᴇᴛᴇ ɢᴜɪᴅᴇ.')}"
        )
    elif action == "nav_settings":
        text = (
            f"⚙️ **{to_smallcaps('sᴇᴛᴛɪɴɢs')}**\n\n"
            f"• {to_smallcaps('ᴍᴀɴᴀɢᴇ ᴄᴀᴘᴛɪᴏɴs, ᴛʜᴜᴍʙɴᴀɪʟs, ᴀɴᴅ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀs.')}"
        )
    elif action == "nav_status":
        text = (
            f"📊 **{to_smallcaps('sʏsᴛᴇᴍ sᴛᴀᴛᴜs')}**\n\n"
            f"• {to_smallcaps('ʙᴏᴛ sᴇʀᴠɪᴄᴇs ᴀʀᴇ ʀᴜɴɴɪɴɢ ɴᴏʀᴍᴀʟʟʏ.')}"
        )
    else:
        text = (
            f"ℹ️ **{to_smallcaps('ᴀʙᴏᴜᴛ')}**\n\n"
            f"• {to_smallcaps('ᴍᴍᴡ ᴀʟʟ-ɪɴ-ᴏɴᴇ ᴘʀᴏ ʙᴏᴛ')}"
        )

    text += f"{format_watermark()}"
    buttons = [[InlineKeyboardButton(f"🏠 {to_smallcaps('ʜᴏᴍᴇ')}", callback_data="nav_home")]]
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    except Exception:
        pass
