import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from app.database.repositories.user_repo import user_repo
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import humanbytes, time_formatter, clean_temp_files, sanitize_filename
from app.utils.progress import progress_for_pyrogram
from app.services.ffmpeg_service import get_media_attributes, compress_media
from app.services.thumb_service import resolve_thumbnail
from app.services.caption_service import format_caption
from app.services.autodel_service import schedule_deletion

@Client.on_message(filters.private & filters.command("compress"))
async def compress_command_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not (target.video or target.document):
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ᴄᴏᴍᴘʀᴇss.')}**\n\n"
            f"• **{to_smallcaps('ᴜsᴀɢᴇ')}**: {to_smallcaps('ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴠɪᴅᴇᴏ ᴡɪᴛʜ')} `/compress`"
            f"{format_watermark()}"
        )
    await show_compression_menu(target, message)

@Client.on_callback_query(filters.regex(r"^compress_menu_(\d+)"))
async def compress_menu_callback(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
    await show_compression_menu(original_msg, query.message, is_callback=True)

async def show_compression_menu(media_msg: Message, target_msg: Message, is_callback: bool = False):
    msg_id = media_msg.id
    media = media_msg.video or media_msg.document
    file_name = getattr(media, "file_name", "video.mp4")
    file_size = humanbytes(media.file_size)

    btn = [
        [
            InlineKeyboardButton(f"⚡ 720ᴘ ʜᴅ (sᴜᴘᴇʀ ғᴀsᴛ)", callback_data=f"do_comp_{msg_id}_720_28_superfast"),
            InlineKeyboardButton(f"🚀 480ᴘ sᴅ (ᴜʟᴛʀᴀ ғᴀsᴛ)", callback_data=f"do_comp_{msg_id}_480_30_ultrafast")
        ],
        [
            InlineKeyboardButton(f"📦 360ᴘ (ᴍᴀx sᴀᴠɪɴɢ)", callback_data=f"do_comp_{msg_id}_360_32_ultrafast"),
            InlineKeyboardButton(f"🎚️ 1080ᴘ (ғᴜʟʟ ʜᴅ)", callback_data=f"do_comp_{msg_id}_1080_24_veryfast")
        ],
        [
            InlineKeyboardButton(f"⚖️ ᴄʀғ 24 (ʙᴀʟᴀɴᴄᴇᴅ)", callback_data=f"do_comp_{msg_id}_0_24_fast"),
            InlineKeyboardButton(f"💎 ᴄʀғ 20 (ʜɪɢʜ ǫᴜᴀʟɪᴛʏ)", callback_data=f"do_comp_{msg_id}_0_20_fast")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('ᴄᴀɴᴄᴇʟ')}", callback_data="cancel_op")
        ]
    ]

    text = (
        f"✦ **{to_smallcaps('ғғᴍᴘᴇɢ ᴠɪᴅᴇᴏ ᴄᴏᴍᴘʀᴇssᴏʀ')}** ✦\n\n"
        f"• 📁 **{to_smallcaps('ғɪʟᴇ ɴᴀᴍᴇ')}** : `{file_name}`\n"
        f"• 📦 **{to_smallcaps('ᴄᴜʀʀᴇɴᴛ sɪᴢᴇ')}** : `{file_size}`\n\n"
        f"💡 **{to_smallcaps('sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴅᴇsɪʀᴇᴅ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴘʀᴇsᴇᴛ:')}**\n"
        f"• 720ᴘ ʜᴅ : {to_smallcaps('ʙᴇsᴛ ʙᴀʟᴀɴᴄᴇ ᴏғ ǫᴜᴀʟɪᴛʏ ᴀɴᴅ sɪᴢᴇ')}\n"
        f"• 480ᴘ sᴅ : {to_smallcaps('sᴜᴘᴇʀ sᴏɴɪᴄ ғᴀsᴛ & ʟᴏᴡ sɪᴢᴇ')}\n"
        f"• 360ᴘ : {to_smallcaps('ᴍᴀxɪᴍᴜᴍ sɪᴢᴇ ʀᴇᴅᴜᴄᴛɪᴏɴ')}\n"
        f"• 1080ᴘ : {to_smallcaps('ғᴜʟʟ ʜᴅ ǫᴜᴀʟɪᴛʏ ᴘʀᴇsᴇʀᴠᴀᴛɪᴏɴ')}"
        f"{format_watermark()}"
    )
    if is_callback:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^do_comp_(\d+)_(\d+)_(\d+)_([a-z]+)"))
async def execute_compression(client: Client, query: CallbackQuery):
    msg_id = int(query.matches[0].group(1))
    scale_h = int(query.matches[0].group(2))
    crf = int(query.matches[0].group(3))
    preset = query.matches[0].group(4)
    user_id = query.from_user.id

    original_msg = await client.get_messages(query.message.chat.id, msg_id)
    if not original_msg or not original_msg.media:
        return await query.answer(to_smallcaps("ᴏʀɪɢɪɴᴀʟ ᴍᴇᴅɪᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)

    status = await query.message.edit_text(f"⏳ **{to_smallcaps('ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ᴡᴏʀᴋғʟᴏᴡ...')}**")

    media = original_msg.video or original_msg.document
    raw_name = getattr(media, "file_name", None) or f"video_{msg_id}.mp4"
    clean_name = sanitize_filename(raw_name)

    download_dir = f"downloads/{user_id}_comp_{int(time.time())}"
    os.makedirs(download_dir, exist_ok=True)
    input_path = os.path.join(download_dir, clean_name)
    output_path = os.path.join(download_dir, f"compressed_{clean_name}")

    start_dl = time.time()
    try:
        await original_msg.download(
            file_name=input_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, start_dl)
        )
    except Exception as e:
        clean_temp_files(input_path, output_path)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    if not os.path.exists(input_path):
        return await status.edit_text(f"❌ **{to_smallcaps('ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴀғᴛᴇʀ ᴅᴏᴡɴʟᴏᴀᴅ!')}**")

    orig_size = os.path.getsize(input_path)
    await status.edit_text(f"🗜️ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ɪɴ ᴘʀᴏɢʀᴇss (ʏᴜᴠ𝟺𝟸𝟶ᴘ)...')}**")

    comp_start = time.time()
    success = await compress_media(input_path, output_path, crf=crf, preset=preset, scale_height=scale_h)
    comp_duration = time.time() - comp_start

    if not success or not os.path.exists(output_path):
        clean_temp_files(input_path, output_path)
        return await status.edit_text(f"❌ **{to_smallcaps('ғғᴍᴘᴇɢ ᴄᴏᴍᴘʀᴇssɪᴏɴ ғᴀɪʟᴇᴅ!')}**")

    comp_size = os.path.getsize(output_path)
    savings = round(((orig_size - comp_size) / orig_size) * 100, 2) if orig_size > 0 else 0

    thumb_path = await resolve_thumbnail(client, user_id, output_path)
    attrs = await get_media_attributes(output_path)

    # Format caption with compression metrics
    orig_caption = original_msg.caption or ""
    base_caption = await format_caption(
        user_id=user_id,
        file_name=f"compressed_{clean_name}",
        file_size_str=humanbytes(comp_size),
        duration_str=time_formatter(seconds=attrs["duration"]),
        ext="mp4",
        file_caption=orig_caption
    )

    stats_summary = (
        f"\n\n📊 **{to_smallcaps('ᴄᴏᴍᴘʀᴇssɪᴏɴ sᴛᴀᴛɪsᴛɪᴄs')}** :\n"
        f"• 📦 **{to_smallcaps('ᴏʀɪɢɪɴᴀʟ sɪᴢᴇ')}** : `{humanbytes(orig_size)}`\n"
        f"• 📦 **{to_smallcaps('ᴄᴏᴍᴘʀᴇssᴇᴅ sɪᴢᴇ')}** : `{humanbytes(comp_size)}`\n"
        f"• 📉 **{to_smallcaps('sᴘᴀᴄᴇ sᴀᴠᴇᴅ')}** : `{savings}%`\n"
        f"• ⏱️ **{to_smallcaps('ᴇɴᴄᴏᴅɪɴɢ ᴛɪᴍᴇ')}** : `{time_formatter(seconds=round(comp_duration))}`"
    )
    final_caption = base_caption + stats_summary

    upload_start = time.time()
    await status.edit_text(f"📤 **{to_smallcaps('ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴏᴍᴘʀᴇssᴇᴅ ᴠɪᴅᴇᴏ...')}**")

    try:
        sent_video = await client.send_video(
            chat_id=query.message.chat.id,
            video=output_path,
            caption=final_caption,
            duration=attrs["duration"],
            width=attrs["width"],
            height=attrs["height"],
            thumb=thumb_path,
            supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ", status, upload_start)
        )
    except Exception as e:
        clean_temp_files(input_path, output_path, thumb_path)
        return await status.edit_text(f"❌ **{to_smallcaps('ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ')}**: `{e}`")

    clean_temp_files(input_path, output_path, thumb_path)
    await status.delete()

    # Schedule deletion if user has configured timer
    u = await user_repo.get_user(user_id)
    del_time = u.get("auto_delete_time", 0) if u else 0
    if del_time > 0 and sent_video:
        await schedule_deletion(sent_video.chat.id, sent_video.id, del_time)
