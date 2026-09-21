import time
import asyncio
from pyrogram import Client
from app.database.repositories.chat_repo import chat_repo
from app.utils.logger import logger

async def schedule_deletion(chat_id: int, message_id: int, seconds: int):
    if seconds <= 0:
        return
    delete_at = time.time() + seconds
    await chat_repo.add_auto_delete_task(chat_id, message_id, delete_at)

async def run_autodelete_sweeper(client: Client):
    logger.info("Auto-Delete background sweeper started.")
    while True:
        try:
            now = time.time()
            expired_tasks = await chat_repo.get_expired_auto_delete(now)
            for item in expired_tasks:
                try:
                    await client.delete_messages(chat_id=item["chat_id"], message_ids=item["message_id"])
                except Exception:
                    pass
                await chat_repo.remove_auto_delete_task(item["chat_id"], item["message_id"])
        except Exception as e:
            logger.error(f"Auto-delete sweeper exception: {e}")
        await asyncio.sleep(8)
