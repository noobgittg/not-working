import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Set, Optional


# Operations are intentionally not serialized per user. Multiple users and multiple
# operations from the same user may run concurrently. Resource limits are delegated
# to Telegram, FFmpeg and the host instead of returning a false "already running" error.
_active: Dict[int, Set[asyncio.Task]] = {}
_lock = asyncio.Lock()


async def register_current(user_id: int) -> asyncio.Task:
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("No running asyncio task")
    async with _lock:
        _active.setdefault(user_id, set()).add(task)
    return task


async def unregister(user_id: int, task: Optional[asyncio.Task] = None):
    async with _lock:
        tasks = _active.get(user_id)
        if not tasks:
            return
        if task is None:
            tasks.clear()
        else:
            tasks.discard(task)
        if not tasks:
            _active.pop(user_id, None)


async def cancel_user(user_id: int) -> bool:
    async with _lock:
        tasks = list(_active.get(user_id, set()))
    cancelled = False
    for task in tasks:
        if not task.done():
            task.cancel()
            cancelled = True
    return cancelled


@asynccontextmanager
async def operation_slot(user_id: int):
    task = await register_current(user_id)
    try:
        yield
    finally:
        await unregister(user_id, task)


def active_count() -> int:
    return sum(len(tasks) for tasks in _active.values())
