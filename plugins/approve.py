from pyrogram import Client
from pyrogram.types import ChatJoinRequest
from config import Config
from font import to_smallcaps
from logger import logger

@Client.on_chat_join_request()
async def join_request_approver(client: Client, request: ChatJoinRequest):
    chat = request.chat
    user = request.from_user

    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        logger.info(f"Auto-approved user {user.id} in {chat.title} ({chat.id})")

        welcome_text = (
            f"🎉 **{to_smallcaps('ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!')}**\n\n"
            f"👋 **{to_smallcaps('ʜᴇʟʟᴏ')} {user.mention}**, {to_smallcaps('ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ')} **{chat.title}** {to_smallcaps('ʜᴀs ʙᴇᴇɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴘᴘʀᴏᴠᴇᴅ!')}\n\n"
            f"⚡ **{to_smallcaps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
        )
        try:
            await client.send_message(chat_id=user.id, text=welcome_text)
        except Exception:
            pass
    except Exception as exc:
        logger.warning("Join request approval failed for chat %s (%s).", chat.id, type(exc).__name__)
