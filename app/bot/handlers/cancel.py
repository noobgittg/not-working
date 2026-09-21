from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.cache import cache
from app.utils.font import to_smallcaps, format_watermark
from app.utils.task_manager import cancel_user

@Client.on_message(filters.private & filters.command("cancel"))
async def cancel_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await cache.delete(f"waiting_rename_{user_id}")
    await cancel_user(user_id)

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")]]
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ᴀʟʟ ᴘᴇɴᴅɪɴɢ ᴀᴄᴛɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.')}**\n\n"
        f"💡 {to_smallcaps('ʏᴏᴜ ᴄᴀɴ sᴇɴᴅ ᴀ ɴᴇᴡ ғɪʟᴇ ᴏʀ ᴄᴏᴍᴍᴀɴᴅ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^cancel_op$"))
async def cancel_callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await cache.delete(f"waiting_rename_{user_id}")
    await cancel_user(user_id)
    await query.answer(to_smallcaps("ᴄᴀɴᴄᴇʟʟᴇᴅ!"), show_alert=False)

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")]]
    await query.message.edit_text(
        f"✦ **{to_smallcaps('ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ᴀʟʟ ᴘᴇɴᴅɪɴɢ ᴀᴄᴛɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )
