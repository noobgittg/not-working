import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from plugins.core_utils import to_smallcaps, format_watermark

SERVICE_FILTERS = filters.service

@Client.on_message(filters.group & SERVICE_FILTERS)
async def service_message_cleaner(client: Client, message: Message):
    try:
        await message.delete()
    except Exception:
        pass

@Client.on_message(filters.group & filters.command(["clean", "purge"]))
async def manual_group_purge(client: Client, message: Message):
    is_admin_user = False
    if message.from_user:
        if message.from_user.id in Config.ADMINS:
            is_admin_user = True
        else:
            try:
                member = await client.get_chat_member(message.chat.id, message.from_user.id)
                if str(member.status).lower() in ["administrator", "owner", "chatmemberstatus.administrator", "chatmemberstatus.owner"]:
                    is_admin_user = True
            except Exception:
                pass
    elif message.sender_chat and message.sender_chat.id == message.chat.id:
        is_admin_user = True

    if not is_admin_user:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('permission denied')}**\n\n"
            f"• {to_smallcaps('you must be a group administrator to use this command.')}"
            f"{format_watermark()}"
        )

    count = 15
    if len(message.command) > 1 and message.command[1].isdigit():
        count = min(100, int(message.command[1]))

    status = await message.reply_text(f"🧹 **{to_smallcaps(f'purging {count} messages...')}**")
    msg_ids = []
    async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
        if msg.id != status.id:
            msg_ids.append(msg.id)

    if msg_ids:
        try:
            await client.delete_messages(chat_id=message.chat.id, message_ids=msg_ids)
        except Exception:
            pass

    await status.edit_text(
        f"✦ **{to_smallcaps('group cleaner')}** ✦\n\n"
        f"✅ **{to_smallcaps(f'purged {len(msg_ids)} messages successfully!')}**"
        f"{format_watermark()}"
    )
    await asyncio.sleep(5)
    try:
        await status.delete()
    except Exception:
        pass
