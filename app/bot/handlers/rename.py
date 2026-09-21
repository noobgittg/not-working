import os
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from app.utils.logger import logger
from app.utils.task_manager import task_manager
from app.utils.font import to_small_caps
from app.utils.helpers import extract_clean_filename, format_bytes
from app.utils.progress import progress_for_pyrogram


def resolve_to_str_path(path_val) -> str:
    """Ensures the object is strictly a single string path, unpacking tuples if present."""
    if isinstance(path_val, (tuple, list)):
        if len(path_val) > 0:
            return str(path_val[0]).strip()
        raise ValueError("Cannot resolve empty tuple to a valid file path.")
    return str(path_val).strip()


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def rename_media_handler(client: Client, message: Message):
    """
    Receives media files and initiates an isolated, non-blocking rename process.
    Allows unlimited simultaneous operations for any user.
    """
    user_id = message.from_user.id
    task_id = task_manager.generate_task_id(user_id)
    work_dir = task_manager.create_workspace(user_id, task_id)

    media = message.document or message.video or message.audio
    current_name = getattr(media, "file_name", None) or f"file_{message.id}.mkv"

    # Ask the user for the new name or check if provided in caption
    prompt_msg = await message.reply_text(
        f"📝 **Current File Name:** `{current_name}`\n\n"
        f"Send the **new file name** with extension as a reply to this message.\n\n"
        f"⚡ *You can process unlimited files at the same time.*",
        quote=True,
    )


async def process_rename_job(
    client: Client,
    media_message: Message,
    status_message: Message,
    new_filename_raw: str,
    user_id: int,
    task_id: str,
    work_dir: str,
):
    """
    Worker function executed asynchronously.
    Guarantees no tuple errors and isolates temp files.
    """
    task = await task_manager.register_task(
        task_id=task_id,
        user_id=user_id,
        task_type="rename",
        work_dir=work_dir,
    )

    try:
        # 1. Sanitize the target new filename into a clean single string
        new_filename = extract_clean_filename(new_filename_raw)
        if isinstance(new_filename, (tuple, list)):
            new_filename = str(new_filename[0])
        new_filename = str(new_filename).strip()

        await status_message.edit_text(f"⏳ **Downloading file to isolated workspace...**")

        start_time = time.time()

        # 2. Download media to isolated directory
        download_result = await client.download_media(
            message=media_message,
            file_name=os.path.join(work_dir, "raw_download"),
            progress=progress_for_pyrogram,
            progress_args=("📥 **Downloading File...**", status_message, start_time),
        )

        # 3. Prevent the 'expected str, bytes or os.PathLike object, not tuple' error
        downloaded_path = resolve_to_str_path(download_result)

        if not os.path.exists(downloaded_path):
            raise FileNotFoundError(f"Downloaded media file not found at: {downloaded_path}")

        target_path = resolve_to_str_path(os.path.join(work_dir, new_filename))

        # Rename file on disk safely
        os.rename(downloaded_path, target_path)

        await status_message.edit_text(f"📤 **Uploading renamed file...**")

        # 4. Upload renamed file
        upload_start = time.time()
        caption = f"📁 **File:** `{new_filename}`"

        if media_message.video:
            await client.send_video(
                chat_id=user_id,
                video=target_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 **Uploading Video...**", status_message, upload_start),
            )
        elif media_message.audio:
            await client.send_audio(
                chat_id=user_id,
                audio=target_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 **Uploading Audio...**", status_message, upload_start),
            )
        else:
            await client.send_document(
                chat_id=user_id,
                document=target_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 **Uploading Document...**", status_message, upload_start),
            )

        await status_message.delete()

    except Exception as exc:
        logger.exception(f"Rename operation failed for task {task_id}: {exc}")
        header = to_small_caps("rename operation failed")
        error_text = str(exc)
        await status_message.edit_text(f"❌ {header}\n\n`{error_text}`")

    finally:
        await task_manager.cleanup_task(task_id)


@Client.on_message(filters.private & filters.reply & filters.text)
async def rename_reply_receiver(client: Client, message: Message):
    """Receives the new filename and starts the rename task concurrently."""
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_self:
        return

    # Check if replied to our prompt
    if "Current File Name:" not in (reply.text or ""):
        return

    original_media_msg = reply.reply_to_message
    if not original_media_msg:
        await message.reply_text("❌ Could not locate the original media message. Please try again.")
        return

    user_id = message.from_user.id
    new_filename_raw = message.text.strip()
    task_id = task_manager.generate_task_id(user_id)
    work_dir = task_manager.create_workspace(user_id, task_id)

    status_msg = await message.reply_text("⚡ **Initializing rename task...**", quote=True)

    # Launch task immediately in background (non-blocking for unlimited concurrent tasks)
    asyncio.create_task(
        process_rename_job(
            client=client,
            media_message=original_media_msg,
            status_message=status_msg,
            new_filename_raw=new_filename_raw,
            user_id=user_id,
            task_id=task_id,
            work_dir=work_dir,
        )
    )
