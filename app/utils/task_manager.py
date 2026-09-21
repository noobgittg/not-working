import asyncio
import os
import shutil
import time
import uuid
from typing import Dict, Optional, Any, Callable
from app.utils.logger import logger


class MediaTask:
    """Represents an active background media task."""

    def __init__(
        self,
        task_id: str,
        user_id: int,
        task_type: str,
        work_dir: str,
        asyncio_task: Optional[asyncio.Task] = None,
        process: Optional[asyncio.subprocess.Process] = None,
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.work_dir = work_dir
        self.asyncio_task = asyncio_task
        self.process = process
        self.created_at = time.time()
        self.is_cancelled = False


class TaskManager:
    """
    Manages concurrent media operations.
    Allows unlimited simultaneous operations per user without blocking.
    """

    def __init__(self):
        # Key: task_id (str) -> MediaTask
        self._tasks: Dict[str, MediaTask] = {}
        self._lock = asyncio.Lock()

    def generate_task_id(self, user_id: int) -> str:
        """Generates a globally unique task identifier."""
        return f"{user_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    def create_workspace(self, user_id: int, task_id: str) -> str:
        """Creates an isolated working directory for this specific task."""
        work_dir = os.path.abspath(os.path.join("downloads", str(user_id), task_id))
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    async def register_task(
        self,
        task_id: str,
        user_id: int,
        task_type: str,
        work_dir: str,
        asyncio_task: Optional[asyncio.Task] = None,
    ) -> MediaTask:
        """Registers a new concurrent task without blocking any user."""
        async with self._lock:
            media_task = MediaTask(
                task_id=task_id,
                user_id=user_id,
                task_type=task_type,
                work_dir=work_dir,
                asyncio_task=asyncio_task,
            )
            self._tasks[task_id] = media_task
            logger.info(f"Registered {task_type} task {task_id} for user {user_id}. Total active: {len(self._tasks)}")
            return media_task

    def set_subprocess(self, task_id: str, process: asyncio.subprocess.Process) -> None:
        """Associates a running FFmpeg/subshell process with the task for cancellation."""
        if task_id in self._tasks:
            self._tasks[task_id].process = process

    def get_task(self, task_id: str) -> Optional[MediaTask]:
        """Retrieves a task by its unique ID."""
        return self._tasks.get(task_id)

    def get_user_tasks(self, user_id: int) -> list[MediaTask]:
        """Returns all running tasks for a specific user."""
        return [task for task in self._tasks.values() if task.user_id == user_id]

    def is_user_busy(self, user_id: int) -> bool:
        """
        Always returns False to allow unlimited concurrent tasks for all users.
        Kept for backward compatibility with older handler imports.
        """
        return False

    async def cancel_task(self, task_id: str) -> bool:
        """Cancels a running task and kills any active FFmpeg processes."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.is_cancelled = True

            # Terminate active child process (e.g., ffmpeg)
            if task.process and task.process.returncode is None:
                try:
                    task.process.kill()
                    logger.info(f"Killed subprocess for task {task_id}")
                except Exception as e:
                    logger.warning(f"Error killing subprocess for task {task_id}: {e}")

            # Cancel asyncio task
            if task.asyncio_task and not task.asyncio_task.done():
                task.asyncio_task.cancel()
                logger.info(f"Cancelled asyncio task {task_id}")

            return True

    async def cleanup_task(self, task_id: str) -> None:
        """Removes the task and cleans up its isolated workspace directory."""
        async with self._lock:
            task = self._tasks.pop(task_id, None)

        if task and task.work_dir and os.path.exists(task.work_dir):
            try:
                shutil.rmtree(task.work_dir, ignore_errors=True)
                logger.info(f"Cleaned up workspace directory for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to delete workspace {task.work_dir}: {e}")


# Global TaskManager singleton instance
task_manager = TaskManager()
