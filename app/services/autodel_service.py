import asyncio
import time

from pyrogram import Client

from app.database.repositories.chat_repo import chat_repo
from app.utils.logger import logger


async def schedule_deletion(chat_id: int, message_id: int, seconds: int):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return
    if seconds <= 0:
        return
    await chat_repo.add_auto_delete_task(int(chat_id), int(message_id), time.time() + seconds)


async def run_autodelete_sweeper(client: Client):
    logger.info("Auto-Delete background sweeper started.")
    while True:
        try:
            expired = await chat_repo.get_expired_auto_delete(time.time(), limit=200)
            if expired:
                groups = {}
                for item in expired:
                    groups.setdefault(int(item["chat_id"]), []).append((int(item["message_id"]), item))
                completed = []
                for chat_id, message_items in groups.items():
                    for offset in range(0, len(message_items), 100):
                        batch = message_items[offset:offset + 100]
                        message_ids = [message_id for message_id, _ in batch]
                        try:
                            await client.delete_messages(chat_id=chat_id, message_ids=message_ids)
                            completed.extend(item for _, item in batch)
                        except Exception as exc:
                            logger.debug("Auto-delete Telegram cleanup failed for %s: %s", chat_id, exc)
                if completed:
                    await chat_repo.remove_auto_delete_tasks(completed)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Auto-delete sweeper exception: %s", exc)
        await asyncio.sleep(8)
