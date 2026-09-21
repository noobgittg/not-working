from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import is_valid_url

@Client.on_message(filters.private & filters.command(["setthumb", "set_thumb"]))
async def set_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.photo:
        thumb_id = message.reply_to_message.photo.file_id
        await user_repo.update_user(user_id, {"thumb_id": thumb_id})
        return await message.reply_text(
            f"✦ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ ᴜᴘᴅᴀᴛᴇᴅ')}** ✦\n\n"
            f"✅ **{to_smallcaps('ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ sᴀᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
            f"💡 {to_smallcaps('ᴛʜɪs ᴛʜᴜᴍʙɴᴀɪʟ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴘᴘʟɪᴇᴅ ᴛᴏ ᴀʟʟ ʏᴏᴜʀ ʀᴇɴᴀᴍᴇᴅ ᴀɴᴅ ᴄᴏᴍᴘʀᴇssᴇᴅ ᴠɪᴅᴇᴏs.')}"
            f"{format_watermark()}"
        )

    if len(message.command) > 1:
        url = message.text.split(None, 1)[1].strip()
        if not is_valid_url(url):
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('ɪɴᴠᴀʟɪᴅ ɪᴍᴀɢᴇ ᴜʀʟ ᴘʀᴏᴠɪᴅᴇᴅ!')}**\n\n"
                f"• {to_smallcaps('ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ʜᴛᴛᴘ/ʜᴛᴛᴘs ᴅɪʀᴇᴄᴛ ɪᴍᴀɢᴇ ʟɪɴᴋ.')}"
                f"{format_watermark()}"
            )
        await user_repo.update_user(user_id, {"tham_url": url})
        return await message.reply_text(
            f"✦ **{to_smallcaps('ᴛʜᴀᴍ_ᴜʀʟ ᴜᴘᴅᴀᴛᴇᴅ')}** ✦\n\n"
            f"✅ **{to_smallcaps('ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴛʜᴀᴍ_ᴜʀʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
            f"• 🔗 **{to_smallcaps('ᴄᴀᴄʜᴇᴅ ᴜʀʟ')}** : `{url}`\n\n"
            f"💡 {to_smallcaps('ᴛʜɪs ᴜʀʟ ᴡɪʟʟ ʙᴇ ᴄᴀᴄʜᴇᴅ ʟᴏᴄᴀʟʟʏ ᴀɴᴅ ᴜsᴇᴅ ᴡʜᴇɴ ɴᴏ ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ ɪs sᴇᴛ.')}"
            f"{format_watermark()}"
        )

    await message.reply_text(
        f"✦ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ ᴍᴀɴᴀɢᴇʀ ɢᴜɪᴅᴇ')}** ✦\n\n"
        f"• 🖼️ **{to_smallcaps('sᴇᴛᴛɪɴɢ ᴠɪᴀ ᴘʜᴏᴛᴏ')}** :\n"
        f"  {to_smallcaps('sᴇɴᴅ ᴀ ᴘʜᴏᴛᴏ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴘʜᴏᴛᴏ ᴡɪᴛʜ')} `/setthumb`.\n\n"
        f"• 🔗 **{to_smallcaps('sᴇᴛᴛɪɴɢ ᴠɪᴀ ᴜʀʟ')}** :\n"
        f"  `/setthumb <image_direct_url>`\n\n"
        f"• 👁️ **{to_smallcaps('ᴠɪᴇᴡ ᴀᴄᴛɪᴠᴇ ᴛʜᴜᴍʙɴᴀɪʟ')}** : `/thumb`\n"
        f"• 🗑️ **{to_smallcaps('ᴅᴇʟᴇᴛᴇ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ')}** : `/delthumb`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["thumb", "viewthumb", "view_thumb"]))
async def view_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    u = await user_repo.get_user(user_id)
    thumb_id = u.get("thumb_id") if u else None

    if thumb_id:
        buttons = [
            [
                InlineKeyboardButton(f"🗑️ {to_smallcaps('ᴅᴇʟᴇᴛᴇ ᴛʜᴜᴍʙɴᴀɪʟ')}", callback_data="thumb_del_cb"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data="nav_settings")
            ]
        ]
        await message.reply_photo(
            photo=thumb_id,
            caption=(
                f"✦ **{to_smallcaps('ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ')}** ✦\n\n"
                f"• 🖼️ **{to_smallcaps('sᴛᴀᴛᴜs')}** : `{to_smallcaps('ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ ᴀᴄᴛɪᴠᴇ')}`\n"
                f"• 📦 **{to_smallcaps('ᴀᴜᴛᴏ-ᴀᴘᴘʟʏ')}** : `{to_smallcaps('ᴇɴᴀʙʟᴇᴅ ғᴏʀ ʀᴇɴᴀᴍᴇ & ᴄᴏᴍᴘʀᴇss')}`"
                f"{format_watermark()}"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        tham_url = (u.get("tham_url") if u else None) or Config.THAM_URL
        buttons = [
            [
                InlineKeyboardButton(f"⚙️ {to_smallcaps('sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data="nav_home")
            ]
        ]
        await message.reply_text(
            f"✦ **{to_smallcaps('ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ sᴛᴀᴛᴜs')}** ✦\n\n"
            f"ℹ️ **{to_smallcaps('ɴᴏ ᴄᴜsᴛᴏᴍ ᴘʜᴏᴛᴏ ᴛʜᴜᴍʙɴᴀɪʟ sᴇᴛ.')}**\n\n"
            f"• 🔗 **{to_smallcaps('ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴛʜᴀᴍ_ᴜʀʟ ғᴀʟʟʙᴀᴄᴋ')}** :\n`{tham_url}`\n\n"
            f"💡 {to_smallcaps('ᴛᴏ sᴇᴛ ᴀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ, sɪᴍᴘʟʏ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴘʜᴏᴛᴏ ᴡɪᴛʜ')} `/setthumb`."
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

@Client.on_message(filters.private & filters.command(["delthumb", "del_thumb"]))
async def del_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await user_repo.update_user(user_id, {"thumb_id": None})
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴛʜᴜᴍʙɴᴀɪʟ ᴅᴇʟᴇᴛᴇᴅ')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ ʜᴀs ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ.')}**\n\n"
        f"💡 {to_smallcaps('ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ɴᴏᴡ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ғᴀʟʟ ʙᴀᴄᴋ ᴛᴏ ᴛʜᴀᴍ_ᴜʀʟ ᴏʀ ɢʟᴏʙᴀʟ ᴅᴇғᴀᴜʟᴛ.')}"
        f"{format_watermark()}"
    )

@Client.on_callback_query(filters.regex(r"^thumb_del_cb$"))
async def thumb_del_callback(client: Client, query: CallbackQuery):
    await user_repo.update_user(query.from_user.id, {"thumb_id": None})
    await query.answer(to_smallcaps("ᴛʜᴜᴍʙɴᴀɪʟ ᴅᴇʟᴇᴛᴇᴅ!"), show_alert=True)
    await query.message.delete()
