import asyncio
import os
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.utils.logger import logger
from app.utils.task_manager import task_manager
from app.utils.font import to_small_caps
from app.utils.progress import progress_for_pyrogram
from app.services.ffmpeg_service import ffmpeg_service, sanitize_path


@Client.on_message(filters.private & (filters.video | filters.document))
async def compress_request_handler(client: Client, message: Message):
    """
    Presents compression options to the user without checking or blocking on running tasks.
    Enables unlimited concurrent compressions for all users.
    """
    user_id = message.from_user.id
    media = message.video or message.document

    if not media:
        return

    # Provide quick quality selection buttons
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⚡ Fast (CRF 28)", callback_data=f"cmp_{message.id}_28_veryfast"),
                InlineKeyboardButton("⚖️ Medium (CRF 24)", callback_data=f"cmp_{message.id}_24_faster"),
            ],
            [
                InlineKeyboardButton("🎬 High Quality (CRF 20)", callback_data=f"cmp_{message.id}_20_slow"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"cmp_cancel_{message.id}"),
            ],
        ]
    )

    await message.reply_text(
        "🗜️ **Video Compressor**\n\n"
        "Choose your target compression profile below:\n"
        "*(Multiple compressions can run simultaneously)*",
        reply_markup=buttons,
        quote=True,
    )


@Client.on_callback_query(filters.regex(r"^cmp_(\d+)_(\d+)_([a-z]+)$"))
async def compress_action_callback(client: Client, query: CallbackQuery):
    """Parses button choices and launches compression in the background."""
    msg_id, crf_str, preset = query.data.split("_")[1:]
    crf = int(crf_str)
    user_id = query.from_user.id

    try:
        media_message = await client.get_messages(chat_id=query.message.chat.id, message_ids=int(msg_id))
    except Exception as e:
        await query.answer("Original media message not found.", show_alert=True)
        return

    await query.answer("Starting compression in background...")
    await query.message.edit_text("🚀 **Queuing compression task...**")

    # Generate isolated workspace for this specific job
    task_id = task_manager.generate_task_id(user_id)
    work_dir = task_manager.create_workspace(user_id, task_id)

    # Spawn asynchronous background task
    asyncio.create_task(
        run_compression_pipeline(
            client=client,
            media_message=media_message,
            status_message=query.message,
            crf=crf,
            preset=preset,
            user_id=user_id,
            task_id=task_id,
            work_dir=work_dir,
        )
    )


async def run_compression_pipeline(
    client: Client,
    media_message: Message,
    status_message: Message,
    crf: int,
    preset: str,
    user_id: int,
    task_id: str,
    work_dir: str,
):
    """Executes download, stream inspection, FFmpeg encoding, and upload."""
    await task_manager.register_task(
        task_id=task_id,
        user_id=user_id,
        task_type="compress",
        work_dir=work_dir,
    )

    try:
        media = media_message.video or media_message.document
        orig_name = getattr(media, "file_name", None) or f"input_{media_message.id}.mp4"
        input_file_path = os.path.join(work_dir, orig_name)

        # 1. Download media
        dl_start = time.time()
        dl_result = await client.download_media(
            message=media_message,
            file_name=input_file_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 **Downloading for compression...**", status_message, dl_start),
        )

        # Sanitize path to prevent tuple errors
        clean_input = sanitize_path(dl_result)

        # 2. Prepare output path
        output_file_name = f"compressed_{orig_name}"
        if not output_file_name.lower().endswith(".mp4"):
            output_file_name += ".mp4"
        clean_output = sanitize_path(os.path.join(work_dir, output_file_name))

        await status_message.edit_text("⚙️ **FFmpeg is compressing video... Please wait.**")

        last_update_time = [0.0]

        async def update_compression_ui(percent: float):
            now = time.time()
            if now - last_update_time[0] > 4.0:
                last_update_time[0] = now
                try:
                    await status_message.edit_text(f"🗜️ **Compressing:** `{percent:.1f}%` completed")
                except Exception:
                    pass

        compressed_path = await ffmpeg_service.compress_video(
            input_path=clean_input,
            output_path=clean_output,
            crf=crf,
            preset=preset,
            task_id=task_id,
            progress_callback=update_compression_ui,
        )

        await status_message.edit_text("📤 **Uploading compressed video...**")
        ul_start = time.time()

        orig_size = os.path.getsize(clean_input)
        new_size = os.path.getsize(compressed_path)
        saved_percent = max(0.0, ((orig_size - new_size) / orig_size) * 100.0) if orig_size > 0 else 0

        caption = (
            f"🎬 **Compressed Video**\n"
            f"📉 **Original:** `{orig_size / (1024*1024):.2f} MB`\n"
            f"📦 **Compressed:** `{new_size / (1024*1024):.2f} MB`\n"
            f"✨ **Saved:** `{saved_percent:.1f}%`"
        )

        await client.send_video(
            chat_id=user_id,
            video=compressed_path,
            caption=caption,
            progress=progress_for_pyrogram,
            progress_args=("📤 **Uploading Compressed Video...**", status_message, ul_start),
        )

        await status_message.delete()

    except Exception as exc:
        logger.exception(f"Compression failed for task {task_id}: {exc}")
        header = to_small_caps("ffmpeg compression failed")
        error_msg = str(exc)
        await status_message.edit_text(f"❌ {header}\n\n`{error_msg}`")

    finally:
        # Clean up isolated task directory
        await task_manager.cleanup_task(task_id)


@Client.on_callback_query(filters.regex(r"^cmp_cancel_(\d+)$"))
async def cancel_compression_callback(client: Client, query: CallbackQuery):
    """Dismisses the compression dialog."""
    await query.answer("Compression cancelled.")
    await query.message.delete()
