from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from plugins.core_db import user_repo
from plugins.core_utils import to_smallcaps, format_watermark

@Client.on_message(filters.private & filters.command(["setcaption", "set_caption"]))
async def set_caption_handler(client: Client, message: Message):
    if len(message.command) < 2:
        help_text = (
            f"✦ **{to_smallcaps('dynamic caption templating guide')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('usage')}** : `/setcaption <template>`\n\n"
            f"• 🏷️ **{to_smallcaps('supported dynamic variables')}** :\n"
            f"  • `{'{filename}'}` : {to_smallcaps('file name (e.g. movie.mkv)')}\n"
            f"  • `{'{filesize}'}` : {to_smallcaps('human-readable size (e.g. 1.25 GB)')}\n"
            f"  • `{'{duration}'}` : {to_smallcaps('video length (e.g. 02:15:30)')}\n"
            f"  • `{'{language}'}` : {to_smallcaps('audio languages')}\n"
            f"  • `{'{audio_track}'}` : {to_smallcaps('audio codec & channels')}\n"
            f"  • `{'{ext}'}` : {to_smallcaps('file extension (e.g. mp4, mkv)')}\n"
            f"  • `{'{original_caption}'}` : {to_smallcaps('original media caption')}\n"
            f"  • `{'{date}'}` : {to_smallcaps('current utc timestamp')}\n\n"
            f"• 💡 **{to_smallcaps('example template')}** :\n"
            f"`📁 {to_smallcaps('file')}: {{filename}}\\n📦 {to_smallcaps('size')}: {{filesize}}\\n⏱️ {to_smallcaps('time')}: {{duration}}`"
            f"{format_watermark()}"
        )
        return await message.reply_text(help_text)

    caption = message.text.split(None, 1)[1].strip()
    if not caption:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('caption template cannot be empty.')}**{format_watermark()}"
        )
    if len(caption) > 900:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('caption template is too long (maximum 900 characters).')}**{format_watermark()}"
        )
    await user_repo.update_user(message.from_user.id, {"custom_caption": caption})
    await message.reply_text(
        f"✦ **{to_smallcaps('custom caption saved')}** ✦\n\n"
        f"✅ **{to_smallcaps('your template has been saved successfully!')}**\n\n"
        f"• 📝 **{to_smallcaps('preview')}** :\n`{caption}`\n\n"
        f"💡 {to_smallcaps('this caption will be automatically applied to all renamed & compressed files.')}"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["addcaption", "add_caption"]))
async def add_caption_to_list(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            f"✦ **{to_smallcaps('add to cap[] queue')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('usage')}** : `/addcaption <template>`\n\n"
            f"💡 {to_smallcaps('adds a new template to your dynamic captions list.')}"
            f"{format_watermark()}"
        )
    caption = message.text.split(None, 1)[1]
    await user_repo.add_caption(message.from_user.id, caption)
    await message.reply_text(
        f"✦ **{to_smallcaps('caption added')}** ✦\n\n"
        f"✅ **{to_smallcaps('added to your dynamic captions list (cap[])!')}**\n\n"
        f"• 📝 **{to_smallcaps('template')}** :\n`{caption}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["caption", "captions", "see_caption"]))
async def view_caption_handler(client: Client, message: Message):
    u = await user_repo.get_user(message.from_user.id)
    c = u.get("custom_caption") if u else None
    cap_list = u.get("captions_list", []) if u else []

    text = f"✦ **{to_smallcaps('your caption settings')}** ✦\n\n"
    if c:
        text += f"• 📝 **{to_smallcaps('active caption template')}** :\n`{c}`\n\n"
    else:
        text += f"• 📝 **{to_smallcaps('active caption template')}** : `{to_smallcaps('default (fallback to file caption)')}`\n\n"

    if cap_list:
        text += f"📚 **{to_smallcaps('saved dynamic captions (cap[])')}** :\n"
        for i, cap in enumerate(cap_list, 1):
            text += f"  {i}. `{cap}`\n"
        text += "\n"

    text += f"💡 {to_smallcaps('use')} `/setcaption <template>` {to_smallcaps('to update or')} `/delcaption` {to_smallcaps('to reset.')}"
    text += format_watermark()

    buttons = [
        [
            InlineKeyboardButton(f"🗑️ {to_smallcaps('reset captions')}", callback_data="caption_reset_cb"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data="nav_settings")
        ]
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["delcaption", "del_caption"]))
async def del_caption_handler(client: Client, message: Message):
    await user_repo.update_user(message.from_user.id, {"custom_caption": None, "captions_list": []})
    await message.reply_text(
        f"✦ **{to_smallcaps('captions reset')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('all custom captions have been reset to default!')}**"
        f"{format_watermark()}"
    )

@Client.on_callback_query(filters.regex(r"^caption_reset_cb$"))
async def caption_reset_callback(client: Client, query: CallbackQuery):
    await user_repo.update_user(query.from_user.id, {"custom_caption": None, "captions_list": []})
    await query.answer(to_smallcaps("captions reset!"), show_alert=True)
    await query.message.edit_text(
        f"✦ **{to_smallcaps('captions reset')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('all your custom captions have been reset to default.')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {to_smallcaps('back to settings')}", callback_data="nav_settings")]])
    )
