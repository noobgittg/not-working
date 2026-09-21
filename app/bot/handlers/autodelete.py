from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark

@Client.on_message(filters.command(["autodelete", "set_timer", "timer"]))
async def autodelete_command_handler(client: Client, message: Message):
    if len(message.command) > 1 and message.command[1].isdigit():
        seconds = int(message.command[1])
        await user_repo.update_user(message.from_user.id, {"auto_delete_time": seconds})
        return await message.reply_text(
            f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ᴜᴘᴅᴀᴛᴇᴅ')}** ✦\n\n"
            f"⏱️ **{to_smallcaps('ᴛɪᴍᴇʀ sᴇᴛ ᴛᴏ')}** : `{seconds}s`\n\n"
            f"💡 {to_smallcaps('ᴀʟʟ ɴᴇᴡ ғɪʟᴇs sᴇɴᴛ ʙʏ ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʙᴇ ᴘᴜʀɢᴇᴅ ᴀғᴛᴇʀ ᴛʜɪs ᴅᴇʟᴀʏ.')}"
            f"{format_watermark()}"
        )

    btn = [
        [
            InlineKeyboardButton(f"⏱️ 5 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_300"),
            InlineKeyboardButton(f"⏱️ 15 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_900"),
            InlineKeyboardButton(f"⏱️ 30 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_1800")
        ],
        [
            InlineKeyboardButton(f"⏱️ 1 {to_smallcaps('ʜᴏᴜʀ')}", callback_data="autodel_3600"),
            InlineKeyboardButton(f"⏱️ 6 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_21600"),
            InlineKeyboardButton(f"⏱️ 12 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_43200")
        ],
        [
            InlineKeyboardButton(f"⏱️ 24 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_86400"),
            InlineKeyboardButton(f"⏱️ 48 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_172800"),
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴅɪsᴀʙʟᴇ')}", callback_data="autodel_0")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")
        ]
    ]

    await message.reply_text(
        f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ sᴄʜᴇᴅᴜʟᴇʀ')}** ✦\n\n"
        f"• ⏱️ **{to_smallcaps('ᴡʜᴀᴛ ɪs ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ?')}**\n"
        f"  {to_smallcaps('ᴛᴏ ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴄᴏɴᴛᴇɴᴛ, ᴛʜᴇ ʙᴏᴛ ᴄᴀɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇ ɪᴛs ʀᴇɴᴀᴍᴇᴅ ᴏʀ ᴄᴏᴍᴘʀᴇssᴇᴅ ᴏᴜᴛᴘᴜᴛ ᴍᴇssᴀɢᴇs ᴀғᴛᴇʀ ᴀ ᴘʀᴇ-sᴇᴛ ᴛɪᴍᴇ.')}\n\n"
        f"• 🛡️ **{to_smallcaps('sᴀғᴇ ʙᴀᴛᴄʜ sᴡᴇᴇᴘɪɴɢ')}** :\n"
        f"  {to_smallcaps('ᴅᴇʟᴇᴛɪᴏɴs ᴀʀᴇ ʙᴀᴛᴄʜᴇᴅ ɪɴ ᴄʜᴜɴᴋs ᴏғ ᴜᴘ ᴛᴏ 𝟷𝟶𝟶 ᴛᴏ ᴇɴsᴜʀᴇ ᴢᴇʀᴏ floodwait ᴀɴᴅ 𝟷𝟶𝟶% ʀᴇʟɪᴀʙɪʟɪᴛʏ.')}\n\n"
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ᴀɴ ɪɴᴛᴇʀᴠᴀʟ ʙᴇʟᴏᴡ:')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^(open_timer_menu|autodel_(\d+))"))
async def timer_callbacks(client: Client, query: CallbackQuery):
    if query.data == "open_timer_menu":
        btn = [
            [
                InlineKeyboardButton(f"⏱️ 5 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_300"),
                InlineKeyboardButton(f"⏱️ 15 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_900"),
                InlineKeyboardButton(f"⏱️ 30 {to_smallcaps('ᴍɪɴ')}", callback_data="autodel_1800")
            ],
            [
                InlineKeyboardButton(f"⏱️ 1 {to_smallcaps('ʜᴏᴜʀ')}", callback_data="autodel_3600"),
                InlineKeyboardButton(f"⏱️ 6 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_21600"),
                InlineKeyboardButton(f"⏱️ 12 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_43200")
            ],
            [
                InlineKeyboardButton(f"⏱️ 24 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_86400"),
                InlineKeyboardButton(f"⏱️ 48 {to_smallcaps('ʜᴏᴜʀs')}", callback_data="autodel_172800"),
                InlineKeyboardButton(f"❌ {to_smallcaps('ᴅɪsᴀʙʟᴇ')}", callback_data="autodel_0")
            ],
            [
                InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")
            ]
        ]
        return await query.message.edit_text(
            f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ sᴄʜᴇᴅᴜʟᴇʀ')}** ✦\n\n"
            f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴅᴇsɪʀᴇᴅ ᴅᴇʟᴇᴛɪᴏɴ ᴛɪᴍᴇ ɪɴᴛᴇʀᴠᴀʟ:')}**"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    seconds = int(query.matches[0].group(2))
    await user_repo.update_user(query.from_user.id, {"auto_delete_time": seconds})
    txt = (
        f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴜᴘᴅᴀᴛᴇᴅ')}** ✦\n\n"
        f"⏱️ **{to_smallcaps('ᴛɪᴍᴇʀ sᴇᴛ ᴛᴏ')}** : `{seconds}s`"
    ) if seconds > 0 else (
        f"✦ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴜᴘᴅᴀᴛᴇᴅ')}** ✦\n\n"
        f"❌ **{to_smallcaps('ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ɪs ɴᴏᴡ ᴅɪsᴀʙʟᴇᴅ!')}**"
    )

    await query.answer(to_smallcaps("ᴛɪᴍᴇʀ ᴜᴘᴅᴀᴛᴇᴅ!"), show_alert=False)
    await query.message.edit_text(
        f"{txt}\n\n"
        f"💡 {to_smallcaps('ʏᴏᴜ ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜɪs sᴇᴛᴛɪɴɢ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ ɪɴ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ sᴇᴛᴛɪɴɢs')}", callback_data="nav_settings")]])
    )
