from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from plugins.core_db import chat_repo
from plugins.core_utils import to_smallcaps, format_watermark, logger

@Client.on_chat_join_request()
async def join_request_approver(client: Client, request: ChatJoinRequest):
    chat = request.chat
    user = request.from_user

    chat_doc = await chat_repo.get_or_create_chat(chat.id, chat.title or "Channel", str(chat.type))
    if not chat_doc.get("auto_approve_joins", True):
        return

    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        logger.info(f"🤝 Auto-approved user {user.id} in {chat.title} ({chat.id})")

        welcome_text = (
            f"🎉 **{to_smallcaps('join request accepted!')}** ✨\n\n"
            f"👋 **{to_smallcaps('hello')} {user.mention}**, {to_smallcaps('your request to join')} **{chat.title}** "
            f"{to_smallcaps('has been automatically accepted!')} ✅"
            f"{format_watermark()}"
        )
        btn = [[InlineKeyboardButton(f"📢 {to_smallcaps('official channel')}", url=Config.WATERMARK_URL)]]
        try:
            await client.send_message(
                chat_id=user.id,
                text=welcome_text,
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Error approving join request for {user.id} in {chat.id}: {e}")

@Client.on_message(filters.command(["autoapprove", "accept", "autoaccept"]) & (filters.group | filters.private))
async def auto_approve_command(client: Client, message: Message):
    chat_id = message.chat.id
    if message.chat.type not in ("private", "bot"):
        try:
            member = await client.get_chat_member(chat_id, message.from_user.id)
            if member.status not in ("administrator", "owner"):
                return await message.reply_text(
                    f"🚫 **{to_smallcaps('only chat administrators can change auto-accept settings.')}**"
                    f"{format_watermark()}"
                )
        except Exception as exc:
            logger.warning("Unable to verify auto-accept permissions in %s: %s", chat_id, exc)
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('unable to verify administrator permissions.')}**"
                f"{format_watermark()}"
            )
    chat_doc = await chat_repo.get_or_create_chat(chat_id, message.chat.title or "Chat", str(message.chat.type))
    curr = bool(chat_doc.get("auto_approve_joins", True))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        curr = False if arg in ["off", "disable", "0", "false"] else True
    else:
        curr = not curr

    await chat_repo.update_chat(chat_id, {"auto_approve_joins": curr})
    status_str = "🟢 ᴇɴᴀʙʟᴇᴅ" if curr else "⚪ ᴅɪsᴀʙʟᴇᴅ"

    await message.reply_text(
        f"✦ **{to_smallcaps('auto-accept join requests')}** ✦\n\n"
        f"• 🤝 **{to_smallcaps('status')}** : `{status_str}`\n"
        f"• 💬 **{to_smallcaps('chat')}** : `{message.chat.title or 'Private / Channels'}`\n\n"
        f"💡 {to_smallcaps('add the bot as admin in your channel or group with invite users permission to auto-accept all join requests instantly!')}"
        f"{format_watermark()}"
    )
