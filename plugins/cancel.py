from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from cache import cache
from font import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command("cancel"))
async def cancel_command_handler(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    for key in ("waiting_rename", "waiting_addaudio", "waiting_addsub", "waiting_trim"):
        await cache.delete(f"{key}_{user_id}")

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")]]
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ᴘᴇɴᴅɪɴɢ ᴡᴏʀᴋғʟᴏᴡ ɪɴᴘᴜᴛs ʜᴀᴠᴇ ʙᴇᴇɴ ᴄʟᴇᴀʀᴇᴅ.')}**\n\n"
        f"💡 {to_smallcaps('ʏᴏᴜ ᴄᴀɴ sᴇɴᴅ ᴀ ɴᴇᴡ ғɪʟᴇ ᴏʀ ᴄᴏᴍᴍᴀɴᴅ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^cancel_op$"))
async def cancel_callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    for key in ("waiting_rename", "waiting_addaudio", "waiting_addsub", "waiting_trim"):
        await cache.delete(f"{key}_{user_id}")
    await query.answer(to_smallcaps("ᴄᴀɴᴄᴇʟʟᴇᴅ!"), show_alert=False)

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")]]
    await query.message.edit_text(
        f"✦ **{to_smallcaps('ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ᴘᴇɴᴅɪɴɢ ᴡᴏʀᴋғʟᴏᴡ ɪɴᴘᴜᴛs ʜᴀᴠᴇ ʙᴇᴇɴ ᴄʟᴇᴀʀᴇᴅ.')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )
