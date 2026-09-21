import sys
import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.database.repositories.file_repo import file_repo
from app.utils.cache import cache
from app.utils.font import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command("admin"))
async def admin_panel_handler(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return await message.reply_text(
            f"🚫 **{to_smallcaps('ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ')}**\n\n"
            f"• {to_smallcaps('ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs ᴏɴʟʏ.')}"
        )
    await render_admin_dashboard(message)

@Client.on_callback_query(filters.regex(r"^admin_(panel_back|stats|clear_cache|restart)"))
async def admin_callbacks(client: Client, query: CallbackQuery):
    if query.from_user.id not in Config.ADMINS:
        return await query.answer(to_smallcaps("ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ!"), show_alert=True)

    action = query.matches[0].group(1)

    if action == "panel_back":
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "clear_cache":
        await cache.clear()
        await query.answer(to_smallcaps("ɪɴ-ᴍᴇᴍᴏʀʏ ᴄᴀᴄʜᴇ ᴄʟᴇᴀʀᴇᴅ!"), show_alert=True)
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "restart":
        await query.answer(to_smallcaps("ɪɴɪᴛɪᴀᴛɪɴɢ ʙᴏᴛ ʀᴇsᴛᴀʀᴛ..."), show_alert=True)
        await query.message.edit_text(f"🔄 **{to_smallcaps('ʙᴏᴛ ɪs ʀᴇsᴛᴀʀᴛɪɴɢ ɴᴏᴡ...')}**")
        os.execl(sys.executable, sys.executable, "main.py")

async def render_admin_dashboard(target_msg: Message, is_edit: bool = False):
    total_users = await user_repo.get_total_users()
    total_chats = await chat_repo.get_total_chats()
    total_files = await file_repo.get_total_files()
    banned_count = await user_repo.get_banned_users_count()

    text = (
        f"✦ **{to_smallcaps('ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ')}** ✦\n\n"
        f"👑 **{to_smallcaps('ᴀᴅᴍɪɴ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ')}**\n\n"
        f"• 👥 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴜsᴇʀs')}** : `{total_users}`\n"
        f"• 📢 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴄʜᴀᴛs')}** : `{total_chats}`\n"
        f"• 📁 **{to_smallcaps('sᴛʀᴇᴀᴍ ғɪʟᴇs')}** : `{total_files}`\n"
        f"• 🚫 **{to_smallcaps('ʙᴀɴɴᴇᴅ ᴜsᴇʀs')}** : `{banned_count}`\n"
        f"• ⚡ **{to_smallcaps('ᴄᴀᴄʜᴇ ᴇɴɢɪɴᴇ')}** : `FastMemoryCache (Active)`\n"
        f"• 💓 **{to_smallcaps('ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ')}** : `6 Pingers Every 6s (Active)`\n"
        f"• 🔄 **{to_smallcaps('24ʜ ʀᴇsᴛᴀʀᴛ')}** : `Auto-Scheduled (Active)`\n"
        f"• 🚀 **{to_smallcaps('ᴇxᴇᴄᴜᴛɪᴏɴ')}** : `Production Async Engine`\n\n"
        f"💡 **{to_smallcaps('ᴀᴅᴍɪɴ ǫᴜɪᴄᴋ ᴀᴄᴛɪᴏɴs:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"📢 {to_smallcaps('ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ')}", callback_data="admin_broadcast_info"),
            InlineKeyboardButton(f"🧹 {to_smallcaps('ᴄʟᴇᴀʀ ᴄᴀᴄʜᴇ')}", callback_data="admin_clear_cache")
        ],
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('ʀᴇsᴛᴀʀᴛ ʙᴏᴛ')}", callback_data="admin_restart"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ')}", callback_data="nav_home")
        ]
    ]

    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

@Client.on_callback_query(filters.regex(r"^admin_broadcast_info$"))
async def admin_broadcast_guide(client: Client, query: CallbackQuery):
    text = (
        f"✦ **{to_smallcaps('ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴsᴛʀᴜᴄᴛɪᴏɴs')}** ✦\n\n"
        f"• 📢 **{to_smallcaps('ᴜsᴀɢᴇ')}** :\n"
        f"  {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇssᴀɢᴇ, ᴘʜᴏᴛᴏ, ᴏʀ ғɪʟᴇ ᴡɪᴛʜ')} `/broadcast`\n\n"
        f"• 🚀 **{to_smallcaps('ᴍᴇᴄʜᴀɴɪsᴍ')}** :\n"
        f"  {to_smallcaps('ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴄᴏᴘʏ ᴛʜᴇ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴜsᴇʀs ᴡɪᴛʜ ғʟᴏᴏᴅᴡᴀɪᴛ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ.')}"
        f"{format_watermark()}"
    )
    buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('ʙᴀᴄᴋ')}", callback_data="admin_panel_back")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("broadcast"))
async def broadcast_command_handler(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return
    if not message.reply_to_message:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ')} `/broadcast`"
        )

    users = await user_repo.get_all_users()
    status = await message.reply_text(f"📢 **{to_smallcaps(f'sᴛᴀʀᴛɪɴɢ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ {len(users)} ᴜsᴇʀs...')}**")

    success = 0
    failed = 0
    for u in users:
        uid = u["user_id"]
        try:
            await message.reply_to_message.copy(uid)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status.edit_text(
        f"✦ **{to_smallcaps('ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ')}** ✦\n\n"
        f"• ✅ **{to_smallcaps('sᴜᴄᴄᴇssғᴜʟ')}** : `{success}`\n"
        f"• ❌ **{to_smallcaps('ғᴀɪʟᴇᴅ / ʙʟᴏᴄᴋᴇᴅ')}** : `{failed}`\n"
        f"• 👥 **{to_smallcaps('ᴛᴏᴛᴀʟ ᴛᴀʀɢᴇᴛs')}** : `{len(users)}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command("ban"))
async def ban_user_handler(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/ban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.ban_user(target_id)
    await message.reply_text(f"🚫 **{to_smallcaps(f'ᴜsᴇʀ {target_id} ʜᴀs ʙᴇᴇɴ ʙᴀɴɴᴇᴅ!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("unban"))
async def unban_user_handler(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('ᴜsᴀɢᴇ')}**: `/unban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.unban_user(target_id)
    await message.reply_text(f"✅ **{to_smallcaps(f'ᴜsᴇʀ {target_id} ʜᴀs ʙᴇᴇɴ ᴜɴʙᴀɴɴᴇᴅ!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("restart"))
async def restart_command_handler(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return
    await message.reply_text(f"🔄 **{to_smallcaps('ʙᴏᴛ ɪs ʀᴇsᴛᴀʀᴛɪɴɢ ɴᴏᴡ...')}**")
    os.execl(sys.executable, sys.executable, "main.py")
