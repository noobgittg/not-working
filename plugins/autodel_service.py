import time
import asyncio
from collections import defaultdict
from pyrogram import Client
from pyrogram.errors import FloodWait
from chat_repo import chat_repo
from logger import logger

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
                        chunk = msg_ids[i:i + 100]
                        try:
                            deleted = await client.delete_messages(chat_id=chat_id, message_ids=chunk)
                            if deleted is False:
                                raise RuntimeError("Telegram did not confirm batch deletion")
                        except FloodWait as exc:
                            wait_seconds = max(1, int(exc.value))
                            logger.warning("Auto-delete was rate-limited; waiting %s seconds.", wait_seconds)
                            await asyncio.sleep(wait_seconds)
                            continue
                        except Exception as exc:
                            logger.warning("Auto-delete batch failed (%s)", type(exc).__name__)
                            # Retry individually; reschedule failures to avoid starving newer tasks.
                            for index, message_id in enumerate(chunk):
                                try:
                                    deleted = await client.delete_messages(chat_id=chat_id, message_ids=message_id)
                                    if deleted is False:
                                        raise RuntimeError("Telegram did not confirm deletion")
                                except FloodWait as item_exc:
                                    wait_seconds = max(1, int(item_exc.value))
                                    logger.warning("Auto-delete retry was rate-limited; waiting %s seconds.", wait_seconds)
                                    for pending_id in chunk[index:]:
                                        await chat_repo.auto_del_col.update_one(
                                            {"chat_id": chat_id, "message_id": pending_id},
                                            {"$set": {"delete_at": float(time.time()) + wait_seconds + 5}},
                                        )
                                    await asyncio.sleep(wait_seconds)
                                    break
                                except Exception as item_exc:
                                    logger.debug("Auto-delete retry failed (%s)", type(item_exc).__name__)
                                    await chat_repo.auto_del_col.update_one(
                                        {"chat_id": chat_id, "message_id": message_id},
                                        {"$set": {"delete_at": float(time.time()) + 60}},
                                    )
                                else:
                                    await chat_repo.delete_auto_delete_task(chat_id, message_id)
                        else:
                            for message_id in chunk:
                                await chat_repo.delete_auto_delete_task(chat_id, message_id)
        except Exception as exc:
            logger.error("Auto-delete sweeper failed (%s).", type(exc).__name__)
        await asyncio.sleep(6)
