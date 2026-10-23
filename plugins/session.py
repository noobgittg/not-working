from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.utils.font import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command("session"))
async def session_generator_command(client: Client, message: Message):
    btn = [
        [
            InlineKeyboardButton(f"⚡ {to_smallcaps('ᴘʏʀᴏɢʀᴀᴍ / ᴘʏʀᴏғᴏʀᴋ')}", callback_data="sess_pyro"),
            InlineKeyboardButton(f"🚀 {to_smallcaps('ᴛᴇʟᴇᴛʜᴏɴ')}", callback_data="sess_tele")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")
        ]
    ]

    await message.reply_text(
        f"✦ **{to_smallcaps('sᴛʀɪɴɢ sᴇssɪᴏɴ ɢᴇɴᴇʀᴀᴛᴏʀ')}** ✦\n\n"
        f"🔐 **{to_smallcaps('ɢᴇɴᴇʀᴀᴛᴇ sᴇᴄᴜʀᴇ ᴛᴇʟᴇɢʀᴀᴍ sᴇssɪᴏɴs')}**\n\n"
        f"• ⚡ **{to_smallcaps('ᴘʏʀᴏɢʀᴀᴍ / ᴘʏʀᴏғᴏʀᴋ')}** : {to_smallcaps('ᴜsᴇᴅ ғᴏʀ ᴍᴏᴅᴇʀɴ ᴜsᴇʀʙᴏᴛs & ᴘʏʀᴏɢʀᴀᴍ ᴠ𝟸 ᴀᴘᴘs.')}\n"
        f"• 🚀 **{to_smallcaps('ᴛᴇʟᴇᴛʜᴏɴ')}** : {to_smallcaps('ᴜsᴇᴅ ғᴏʀ ᴛᴇʟᴇᴛʜᴏɴ-ʙᴀsᴇᴅ ᴜsᴇʀʙᴏᴛs & sᴄʀɪᴘᴛs.')}\n\n"
        f"🛡️ **{to_smallcaps('sᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴀɴᴛᴇᴇ')}** :\n"
        f"• {to_smallcaps('𝟷𝟶𝟶% ɪɴ-ᴍᴇᴍᴏʀʏ ɢᴇɴᴇʀᴀᴛɪᴏɴ (ᴢᴇʀᴏ ᴅɪsᴋ sᴛᴏʀᴀɢᴇ).')}\n"
        f"• {to_smallcaps('ᴛʜᴇ sᴇssɪᴏɴ sᴛʀɪɴɢ ɪs sᴇɴᴛ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs.')}\n\n"
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛ ʟɪʙʀᴀʀʏ ʙᴇʟᴏᴡ:')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^sess_(pyro|tele)"))
async def session_lib_choice(client: Client, query: CallbackQuery):
    lib = query.matches[0].group(1)
    lib_name = "Pyrogram / Pyrofork" if lib == "pyro" else "Telethon"
    buttons = [
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data="nav_home"),
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
        ]
    ]

    await query.message.edit_text(
        f"✦ **{to_smallcaps(f'{lib_name} sᴇssɪᴏɴ')}** ✦\n\n"
        f"📋 **{to_smallcaps('sᴛᴇᴘ-ʙʏ-sᴛᴇᴘ ɢᴇɴᴇʀᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴍᴇɴᴛs')}** :\n\n"
        f"1. **{to_smallcaps('ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟs')}** :\n"
        f"   • {to_smallcaps('ᴏʙᴛᴀɪɴ ʏᴏᴜʀ')} `API_ID` {to_smallcaps('ᴀɴᴅ')} `API_HASH` {to_smallcaps('ғʀᴏᴍ')} [my.telegram.org](https://my.telegram.org).\n\n"
        f"2. **{to_smallcaps('ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ')}** :\n"
        f"   • {to_smallcaps('ᴇɴsᴜʀᴇ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ɪs ɪɴ ɪɴᴛᴇʀɴᴀᴛɪᴏɴᴀʟ ғᴏʀᴍᴀᴛ (ᴇ.ɢ. +𝟿𝟷𝟿𝟾𝟽𝟼𝟻𝟺𝟹𝟸𝟷𝟶 ᴏʀ +𝟷𝟺𝟷𝟻𝟻𝟻𝟻𝟸𝟼𝟽𝟷).')}\n\n"
        f"3. **{to_smallcaps('ᴏᴛᴘ & 𝟸ғᴀ')}** :\n"
        f"   • {to_smallcaps('ʏᴏᴜ ᴡɪʟʟ ʀᴇᴄᴇɪᴠᴇ ᴀ ʟᴏɢɪɴ ᴄᴏᴅᴇ ᴅɪʀᴇᴄᴛʟʏ ғʀᴏᴍ ᴛᴇʟᴇɢʀᴀᴍ.')}\n"
        f"   • {to_smallcaps('ɪғ ʏᴏᴜ ʜᴀᴠᴇ ᴛᴡᴏ-sᴛᴇᴘ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴇɴᴀʙʟᴇᴅ, ʏᴏᴜ ᴡɪʟʟ ʙᴇ ᴘʀᴏᴍᴘᴛᴇᴅ ғᴏʀ ʏᴏᴜʀ ᴄʟᴏᴜᴅ ᴘᴀssᴡᴏʀᴅ.')}\n\n"
        f"⚠️ **{to_smallcaps('sᴇᴄᴜʀɪᴛʏ ᴡᴀʀɴɪɴɢ')}** :\n"
        f"{to_smallcaps('ɴᴇᴠᴇʀ sʜᴀʀᴇ ʏᴏᴜʀ sᴇssɪᴏɴ sᴛʀɪɴɢ ᴏʀ ᴏᴛᴘ ᴡɪᴛʜ ᴀɴʏᴏɴᴇ! ɪᴛ ɢʀᴀɴᴛs ᴄᴏᴍᴘʟᴇᴛᴇ ᴀᴄᴄᴇss ᴛᴏ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )
