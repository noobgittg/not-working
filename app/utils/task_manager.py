import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Optional

from config import Config
from app.utils.logger import logger


_operation_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)
_active: Dict[int, asyncio.Task] = {}
_lock = asyncio.Lock()


async def register_current(user_id: int) -> asyncio.Task:
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("No running asyncio task")
    async with _lock:
        previous = _active.get(user_id)
        if previous and not previous.done() and previous is not task:
            raise RuntimeError("Another media operation is already running for this user")
        _active[user_id] = task
    return task


async def unregister(user_id: int, task: Optional[asyncio.Task] = None):
    async with _lock:
        current = _active.get(user_id)
        if task is None or current is task:
            _active.pop(user_id, None)


async def cancel_user(user_id: int) -> bool:
    async with _lock:
        task = _active.get(user_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


@asynccontextmanager
async def operation_slot(user_id: int):
    await register_current(user_id)
    try:
        async with _operation_semaphore:
            yield
    finally:
        await unregister(user_id)


def active_count() -> int:
    return sum(1 for task in _active.values() if not task.done())
