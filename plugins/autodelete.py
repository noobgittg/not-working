from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from plugins.core_db import user_repo
from plugins.core_utils import to_smallcaps, format_watermark

@Client.on_message(filters.command(["autodelete", "set_timer", "timer"]))
async def autodelete_command_handler(client: Client, message: Message):
    if len(message.command) > 1 and message.command[1].isdigit():
        seconds = int(message.command[1])
        await user_repo.update_user(message.from_user.id, {"auto_delete_time": seconds})
        return await message.reply_text(
            f"✦ **{to_smallcaps('auto-delete timer updated')}** ✦\n\n"
            f"⏱️ **{to_smallcaps('timer set to')}** : `{seconds}s`\n\n"
            f"💡 {to_smallcaps('all new files sent by the bot will automatically be purged after this delay.')}"
            f"{format_watermark()}"
        )

    btn = [
        [
            InlineKeyboardButton(f"⏱️ 5 {to_smallcaps('min')}", callback_data="autodel_300"),
            InlineKeyboardButton(f"⏱️ 15 {to_smallcaps('min')}", callback_data="autodel_900"),
            InlineKeyboardButton(f"⏱️ 30 {to_smallcaps('min')}", callback_data="autodel_1800")
        ],
        [
            InlineKeyboardButton(f"⏱️ 1 {to_smallcaps('hour')}", callback_data="autodel_3600"),
            InlineKeyboardButton(f"⏱️ 6 {to_smallcaps('hours')}", callback_data="autodel_21600"),
            InlineKeyboardButton(f"⏱️ 12 {to_smallcaps('hours')}", callback_data="autodel_43200")
        ],
        [
            InlineKeyboardButton(f"⏱️ 24 {to_smallcaps('hours')}", callback_data="autodel_86400"),
            InlineKeyboardButton(f"⏱️ 48 {to_smallcaps('hours')}", callback_data="autodel_172800"),
            InlineKeyboardButton(f"❌ {to_smallcaps('disable')}", callback_data="autodel_0")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to settings')}", callback_data="nav_settings")
        ]
    ]

    await message.reply_text(
        f"✦ **{to_smallcaps('auto-delete timer scheduler')}** ✦\n\n"
        f"• ⏱️ **{to_smallcaps('what is auto-delete?')}**\n"
        f"  {to_smallcaps('to protect your content, the bot can automatically delete its renamed or compressed output messages after a pre-set time.')}\n\n"
        f"💡 **{to_smallcaps('select an interval below:')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^(open_timer_menu|autodel_(\d+))"))
async def timer_callbacks(client: Client, query: CallbackQuery):
    if query.data == "open_timer_menu":
        btn = [
            [
                InlineKeyboardButton(f"⏱️ 5 {to_smallcaps('min')}", callback_data="autodel_300"),
                InlineKeyboardButton(f"⏱️ 15 {to_smallcaps('min')}", callback_data="autodel_900"),
                InlineKeyboardButton(f"⏱️ 30 {to_smallcaps('min')}", callback_data="autodel_1800")
            ],
            [
                InlineKeyboardButton(f"⏱️ 1 {to_smallcaps('hour')}", callback_data="autodel_3600"),
                InlineKeyboardButton(f"⏱️ 6 {to_smallcaps('hours')}", callback_data="autodel_21600"),
                InlineKeyboardButton(f"⏱️ 12 {to_smallcaps('hours')}", callback_data="autodel_43200")
            ],
            [
                InlineKeyboardButton(f"⏱️ 24 {to_smallcaps('hours')}", callback_data="autodel_86400"),
                InlineKeyboardButton(f"⏱️ 48 {to_smallcaps('hours')}", callback_data="autodel_172800"),
                InlineKeyboardButton(f"❌ {to_smallcaps('disable')}", callback_data="autodel_0")
            ],
            [
                InlineKeyboardButton(f"🔙 {to_smallcaps('back to settings')}", callback_data="nav_settings")
            ]
        ]
        return await query.message.edit_text(
            f"✦ **{to_smallcaps('auto-delete timer scheduler')}** ✦\n\n"
            f"💡 **{to_smallcaps('select your desired deletion time interval:')}**"
            f"{format_watermark()}",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    seconds = int(query.matches[0].group(2))
    await user_repo.update_user(query.from_user.id, {"auto_delete_time": seconds})
    txt = (
        f"✦ **{to_smallcaps('auto-delete updated')}** ✦\n\n"
        f"⏱️ **{to_smallcaps('timer set to')}** : `{seconds}s`"
    ) if seconds > 0 else (
        f"✦ **{to_smallcaps('auto-delete updated')}** ✦\n\n"
        f"❌ **{to_smallcaps('auto-delete timer is now disabled!')}**"
    )

    await query.answer(to_smallcaps("timer updated!"), show_alert=False)
    await query.message.edit_text(
        f"{txt}\n\n"
        f"💡 {to_smallcaps('you can change this setting at any time in your settings menu.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {to_smallcaps('back to settings')}", callback_data="nav_settings")]])
    )
