from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from plugins.core_db import user_repo
from plugins.core_utils import to_smallcaps, format_watermark, is_valid_url

@Client.on_message(filters.private & filters.photo)
async def auto_save_photo_as_thumb(client: Client, message: Message):
    """Automatically saves any photo sent in private chat as the user's custom thumbnail."""
    user_id = message.from_user.id
    thumb_id = message.photo.file_id
    await user_repo.update_user(user_id, {"thumb_id": thumb_id})
    buttons = [
        [
            InlineKeyboardButton(f"👁️ {to_smallcaps('view thumb')}", callback_data="settings_view_thumb"),
            InlineKeyboardButton(f"🗑️ {to_smallcaps('delete thumb')}", callback_data="thumb_del_cb")
        ]
    ]
    await message.reply_text(
        f"✦ **{to_smallcaps('auto thumbnail saved')}** ✦\n\n"
        f"✅ **{to_smallcaps('your photo has been automatically saved as your custom thumbnail!')}**\n\n"
        f"💡 {to_smallcaps('it will be applied to all your renamed and compressed videos.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )

@Client.on_message(filters.private & filters.command(["setthumb", "set_thumb"]))
async def set_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.photo:
        thumb_id = message.reply_to_message.photo.file_id
        await user_repo.update_user(user_id, {"thumb_id": thumb_id})
        return await message.reply_text(
            f"✦ **{to_smallcaps('thumbnail updated')}** ✦\n\n"
            f"✅ **{to_smallcaps('custom thumbnail saved successfully!')}**\n\n"
            f"💡 {to_smallcaps('this thumbnail will be automatically applied to all your renamed and compressed videos.')}"
            f"{format_watermark()}"
        )

    if len(message.command) > 1:
        url = message.text.split(None, 1)[1].strip()
        if not is_valid_url(url):
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('invalid image url provided!')}**\n\n"
                f"• {to_smallcaps('please provide a valid http/https direct image link.')}"
                f"{format_watermark()}"
            )
        await user_repo.update_user(user_id, {"tham_url": url})
        return await message.reply_text(
            f"✦ **{to_smallcaps('tham_url updated')}** ✦\n\n"
            f"✅ **{to_smallcaps('automatic tham_url updated successfully!')}**\n\n"
            f"• 🔗 **{to_smallcaps('cached url')}** : `{url}`"
            f"{format_watermark()}"
        )

    await message.reply_text(
        f"✦ **{to_smallcaps('thumbnail manager guide')}** ✦\n\n"
        f"• 🖼️ **{to_smallcaps('auto photo')}** : {to_smallcaps('just send any photo directly to set it as your thumbnail!')}\n"
        f"• 🖼️ **{to_smallcaps('reply photo')}** : {to_smallcaps('reply to any photo with')} `/setthumb`.\n"
        f"• 🔗 **{to_smallcaps('via url')}** : `/setthumb <image_direct_url>`\n"
        f"• 👁️ **{to_smallcaps('view active thumbnail')}** : `/thumb`\n"
        f"• 🗑️ **{to_smallcaps('delete custom thumbnail')}** : `/delthumb`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["thumb", "viewthumb", "view_thumb"]))
async def view_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    u = await user_repo.get_user(user_id)
    thumb_id = u.get("thumb_id") if u else None

    if thumb_id:
        buttons = [
            [
                InlineKeyboardButton(f"🗑️ {to_smallcaps('delete thumbnail')}", callback_data="thumb_del_cb"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data="nav_settings")
            ]
        ]
        await message.reply_photo(
            photo=thumb_id,
            caption=(
                f"✦ **{to_smallcaps('your active custom thumbnail')}** ✦\n\n"
                f"• 🖼️ **{to_smallcaps('status')}** : `{to_smallcaps('custom photo active')}`\n"
                f"• 📦 **{to_smallcaps('auto-apply')}** : `{to_smallcaps('enabled for rename & compress')}`"
                f"{format_watermark()}"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        tham_url = (u.get("tham_url") if u else None) or Config.THAM_URL
        buttons = [
            [
                InlineKeyboardButton(f"⚙️ {to_smallcaps('settings')}", callback_data="nav_settings"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data="nav_home")
            ]
        ]
        await message.reply_text(
            f"✦ **{to_smallcaps('your thumbnail status')}** ✦\n\n"
            f"ℹ️ **{to_smallcaps('no custom photo thumbnail set.')}**\n\n"
            f"• 🔗 **{to_smallcaps('automatic tham_url fallback')}** :\n`{tham_url}`\n\n"
            f"💡 {to_smallcaps('simply send any photo to set a custom thumbnail!')}"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

@Client.on_message(filters.private & filters.command(["delthumb", "del_thumb"]))
async def del_thumb_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await user_repo.update_user(user_id, {"thumb_id": None})
    await message.reply_text(
        f"✦ **{to_smallcaps('thumbnail deleted')}** ✦\n\n"
        f"🗑️ **{to_smallcaps('your custom thumbnail has been deleted.')}**"
        f"{format_watermark()}"
    )

@Client.on_callback_query(filters.regex(r"^thumb_del_cb$"))
async def thumb_del_callback(client: Client, query: CallbackQuery):
    await user_repo.update_user(query.from_user.id, {"thumb_id": None})
    await query.answer(to_smallcaps("thumbnail deleted!"), show_alert=True)
    await query.message.delete()
