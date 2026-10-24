from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.core_utils import cache, task_manager, to_smallcaps, format_watermark
from plugins.session import cleanup_sess_client

@Client.on_message(filters.private & filters.command("cancel"))
async def cancel_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await cache.delete(f"waiting_rename_{user_id}")
    await cache.delete(f"waiting_addaudio_{user_id}")
    await cache.delete(f"waiting_addsub_{user_id}")
    await cache.delete(f"waiting_trim_{user_id}")
    await cleanup_sess_client(user_id)
    cancelled_tasks = await task_manager.cancel_user_tasks(user_id)

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('back to home')}", callback_data="nav_home")]]
    await message.reply_text(
        f"✦ **{to_smallcaps('operation cancelled')}** ✦\n\n"
        f"✅ **{to_smallcaps('all pending prompts and active tasks have been cancelled successfully.')}** "
        f"(`{cancelled_tasks}` {to_smallcaps('tasks stopped')})\n\n"
        f"💡 {to_smallcaps('you can send a new file or command at any time.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^cancel_op$"))
async def cancel_callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await cache.delete(f"waiting_rename_{user_id}")
    await cache.delete(f"waiting_addaudio_{user_id}")
    await cache.delete(f"waiting_addsub_{user_id}")
    await cache.delete(f"waiting_trim_{user_id}")
    await cleanup_sess_client(user_id)
    await task_manager.cancel_user_tasks(user_id)
    await query.answer(to_smallcaps("cancelled!"), show_alert=False)

    btn = [[InlineKeyboardButton(f"🏠 {to_smallcaps('back to home')}", callback_data="nav_home")]]
    await query.message.edit_text(
        f"✦ **{to_smallcaps('operation cancelled')}** ✦\n\n"
        f"✅ **{to_smallcaps('all pending actions have been cancelled successfully.')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )
