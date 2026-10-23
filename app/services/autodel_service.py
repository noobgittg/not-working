import time
import asyncio
from collections import defaultdict
from pyrogram import Client
from app.database.repositories.chat_repo import chat_repo
from app.utils.logger import logger

async def schedule_deletion(chat_id: int, message_id: int, seconds: int):
    """Schedules an auto-delete task in MongoDB."""
    if seconds <= 0:
        return
    delete_at = float(time.time()) + float(seconds)
    await chat_repo.create_auto_delete_task(chat_id, message_id, delete_at)

async def run_autodelete_sweeper(client: Client):
    """Background worker that continuously sweeps and purges expired auto-delete tasks."""
    logger.info("Auto-Delete background sweeper started.")
    while True:
        try:
            curr_time = float(time.time())
            expired_tasks = await chat_repo.get_expired_auto_delete(curr_time)
            if expired_tasks:
                chat_buckets = defaultdict(list)
                for item in expired_tasks:
                    chat_buckets[item["chat_id"]].append(item["message_id"])

                for chat_id, msg_ids in chat_buckets.items():
                    for i in range(0, len(msg_ids), 100):
                        chunk = msg_ids[i:i+100]
                        try:
                            await client.delete_messages(chat_id=chat_id, message_ids=chunk)
                        except Exception as e:
                            logger.debug(f"Failed deleting batch in {chat_id}: {e}")
                    for mid in msg_ids:
                        await chat_repo.delete_auto_delete_task(chat_id, mid)
        except Exception as e:
            logger.error(f"Auto-delete sweeper exception: {e}")
        await asyncio.sleep(6)
