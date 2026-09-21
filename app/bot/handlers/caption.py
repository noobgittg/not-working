from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command(["setcaption", "set_caption"]))
async def set_caption_handler(client: Client, message: Message):
    if len(message.command) < 2:
        help_text = (
            f"✦ **{to_smallcaps('ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛɪɴɢ ɢᴜɪᴅᴇ')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/setcaption <template>`\n\n"
            f"• 🏷️ **{to_smallcaps('sᴜᴘᴘᴏʀᴛᴇᴅ ᴅʏɴᴀᴍɪᴄ ᴠᴀʀɪᴀʙʟᴇs')}** :\n"
            f"  • `{'{filename}'}` : {to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ (ᴇ.ɢ. movie.mkv)')}\n"
            f"  • `{'{filesize}'}` : {to_smallcaps('ʜᴜᴍᴀɴ-ʀᴇᴀᴅᴀʙʟᴇ sɪᴢᴇ (ᴇ.ɢ. 1.25 GB)')}\n"
            f"  • `{'{duration}'}` : {to_smallcaps('ᴠɪᴅᴇᴏ ʟᴇɴɢᴛʜ (ᴇ.ɢ. 02:15:30)')}\n"
            f"  • `{'{ext}'}` : {to_smallcaps('ғɪʟᴇ ᴇxᴛᴇɴsɪᴏɴ (ᴇ.ɢ. mp4, mkv)')}\n"
            f"  • `{'{original_caption}'}` : {to_smallcaps('ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ᴄᴀᴘᴛɪᴏɴ')}\n"
            f"  • `{'{date}'}` : {to_smallcaps('ᴄᴜʀʀᴇɴᴛ ᴜᴛᴄ ᴛɪᴍᴇsᴛᴀᴍᴘ')}\n\n"
            f"• 💡 **{to_smallcaps('ᴇxᴀᴍᴘʟᴇ ᴛᴇᴍᴘʟᴀᴛᴇ')}** :\n"
            f"`📁 {to_smallcaps('ғɪʟᴇ')}: {{filename}}\\n📦 {to_smallcaps('sɪᴢᴇ')}: {{filesize}}\\n⏱️ {to_smallcaps('ᴛɪᴍᴇ')}: {{duration}}`"
            f"{format_watermark()}"
        )
        return await message.reply_text(help_text)

    caption = message.text.split(None, 1)[1]
    await user_repo.update_user(message.from_user.id, {"custom_caption": caption})
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ sᴀᴠᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ʏᴏᴜʀ ᴛᴇᴍᴘʟᴀᴛᴇ ʜᴀs ʙᴇᴇɴ sᴀᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!')}**\n\n"
        f"• 📝 **{to_smallcaps('ᴘʀᴇᴠɪᴇᴡ')}** :\n`{caption}`\n\n"
        f"💡 {to_smallcaps('ᴛʜɪs ᴄᴀᴘᴛɪᴏɴ ᴡɪʟʟ ʙᴇ ᴀᴘᴘʟɪᴇᴅ ᴛᴏ ᴀʟʟ ʀᴇɴᴀᴍᴇᴅ & ᴄᴏᴍᴘʀᴇssᴇᴅ ғɪʟᴇs.')}"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["addcaption", "add_caption"]))
async def add_caption_to_list(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"✦ **{to_smallcaps('ᴀᴅᴅ ᴛᴏ ᴄᴀᴘ[] ǫᴜᴇᴜᴇ')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/addcaption <template>`\n\n"
            f"💡 {to_smallcaps('ᴀᴅᴅs ᴀ ɴᴇᴡ ᴛᴇᴍᴘʟᴀᴛᴇ ᴛᴏ ʏᴏᴜʀ ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs ʟɪsᴛ.')}"
            f"{format_watermark()}"
        )
    caption = message.text.split(None, 1)[1]
    await user_repo.add_caption(message.from_user.id, caption)
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴ ᴀᴅᴅᴇᴅ')}** ✦\n\n"
        f"✅ **{to_smallcaps('ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs ʟɪsᴛ (ᴄᴀᴘ[])!')}**\n\n"
        f"• 📝 **{to_smallcaps('ᴛᴇᴍᴘʟᴀᴛᴇ')}** :\n`{caption}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["caption", "captions", "see_caption"]))
async def view_caption_handler(client: Client, message: Message):
    u = await user_repo.get_user(message.from_user.id)
    c = u.get("custom_caption") if u else None
    cap_list = u.get("captions_list", []) if u else []

    text = f"✦ **{to_smallcaps('ʏᴏᴜʀ ᴄᴀᴘᴛɪᴏɴ sᴇᴛᴛɪɴɢs')}** ✦\n\n"
    if c:
        text += f"• 📝 **{to_smallcaps('ᴀᴄᴛɪᴠᴇ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ')}** :\n`{c}`\n\n"
    else:
        text += f"• 📝 **{to_smallcaps('ᴀᴄᴛɪᴠᴇ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ')}** : `{to_smallcaps('ᴅᴇғᴀᴜʟᴛ (ғᴀʟʟʙᴀᴄᴋ ᴛᴏ ғɪʟᴇ ᴄᴀᴘᴛɪᴏɴ)')}`\n\n"

    if cap_list:
        text += f"📚 **{to_smallcaps('sᴀᴠᴇᴅ ᴅʏɴᴀᴍɪᴄ ᴄᴀᴘᴛɪᴏɴs (ᴄᴀᴘ[])')}** :\n"
        for i, cap in enumerate(cap_list, 1):
            text += f"  {i}. `{cap}`\n"
        text += "\n"

    text += f"💡 {to_smallcaps('ᴜsᴇ')} `/setcaption <template>` {to_smallcaps('ᴛᴏ ᴜᴘᴅᴀᴛᴇ ᴏʀ')} `/delcaption` {to_smallcaps('ᴛᴏ ʀᴇsᴇᴛ.')}"
    text += f"{format_watermark()}"

    buttons = [
        [
            InlineKeyboardButton(f"🗑️ {to_smallcaps('ʀᴇsᴇᴛ ᴄᴀᴘᴛɪᴏɴs')}", callback_data="caption_reset_cb"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data="nav_settings")
        ]
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["delcaption", "del_caption"]))
async def del_caption_handler(client: Client, message: Message):
    await user_repo.update_user(message.from_user.id, {"custom_caption": None, "captions_list": []})
    await message.reply_text(
        f"✦ **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴs ʀᴇsᴇᴛ')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('ᴀʟʟ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴇᴛ ᴛᴏ ᴅᴇғᴀᴜʟᴛ!')}**"
        f"{format_watermark()}"
    )

@Client.on_callback_query(filters.regex(r"^caption_reset_cb$"))
async def caption_reset_callback(client: Client, query: CallbackQuery):
    await user_repo.update_user(query.from_user.id, {"custom_caption": None, "captions_list": []})
    await query.answer(to_smallcaps("ᴄᴀᴘᴛɪᴏɴs ʀᴇsᴇᴛ!"), show_alert=True)
    await query.message.edit_text(
        f"✦ **{to_smallcaps('ᴄᴀᴘᴛɪᴏɴs ʀᴇsᴇᴛ')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('ᴀʟʟ ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴇᴛ ᴛᴏ ᴅᴇғᴀᴜʟᴛ.')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")]])
    )
