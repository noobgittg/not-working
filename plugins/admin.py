import sys
import os
import time
import math
import asyncio
import gc
import platform
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import Config
from plugins.core_db import user_repo, chat_repo, file_repo, mongo
from plugins.core_utils import (
    cache,
    to_smallcaps,
    format_watermark,
    check_admin,
    is_admin,
    humanbytes,
    time_formatter,
    is_devil_mode_active,
    set_devil_mode,
    logger,
    MEMORY_LOGS
)
from plugins.core_services import RESTART_MARKER_FILE

START_TIME = time.time()

# ----------------- ADMIN DASHBOARD ----------------- #

@Client.on_message(filters.private & filters.command("admin"))
async def admin_panel_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_admin_dashboard(message)

async def render_admin_dashboard(target_msg: Message, is_edit: bool = False):
    total_users = await user_repo.get_total_users()
    total_chats = await chat_repo.get_total_chats()
    total_files = await file_repo.get_total_files()
    banned_count = await user_repo.get_banned_users_count()
    cache_stats = await cache.get_stats()
    devil_status = "🔥 ᴀᴄᴛɪᴠᴇ" if is_devil_mode_active() else "⚪ ᴅɪsᴀʙʟᴇᴅ"

    text = (
        f"✦ **{to_smallcaps('admin control panel')}** ✦\n\n"
        f"👑 **{to_smallcaps('admin mode active')}**\n\n"
        f"• 👥 **{to_smallcaps('total users')}** : `{total_users}`\n"
        f"• 📢 **{to_smallcaps('total chats')}** : `{total_chats}`\n"
        f"• 📁 **{to_smallcaps('stream files')}** : `{total_files}`\n"
        f"• 🚫 **{to_smallcaps('banned users')}** : `{banned_count}`\n"
        f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s (4 External Players)`\n"
        f"• 🧠 **{to_smallcaps('cache keys')}** : `{cache_stats['cached_keys']}` (Hit: `{cache_stats['hit_ratio_percent']}%`)\n"
        f"• 🍃 **{to_smallcaps('database')}** : `Single Unified MongoDB`\n"
        f"• 😈 **{to_smallcaps('devil mode')}** : `{devil_status}`\n\n"
        f"💡 **{to_smallcaps('admin quick actions:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('stats')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"👥 {to_smallcaps('user list')}", callback_data="admin_users_page_1")
        ],
        [
            InlineKeyboardButton(f"📢 {to_smallcaps('broadcast')}", callback_data="admin_broadcast_info"),
            InlineKeyboardButton(f"🍃 {to_smallcaps('database')}", callback_data="admin_dbstats")
        ],
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('clear cache')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"⚙️ {to_smallcaps('config')}", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('restart bot')}", callback_data="admin_restart"),
            InlineKeyboardButton(f"❌ {to_smallcaps('close')}", callback_data="admin_close")
        ]
    ]

    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# ----------------- ADMIN COMMANDS ----------------- #

@Client.on_message(filters.private & filters.command("stats"))
async def admin_stats_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_stats_card(message)

async def render_stats_card(target_msg: Message, is_edit: bool = False):
    total_users = await user_repo.get_total_users()
    total_chats = await chat_repo.get_total_chats()
    total_files = await file_repo.get_total_files()
    banned_count = await user_repo.get_banned_users_count()
    cache_stats = await cache.get_stats()
    uptime_sec = round(float(time.time()) - START_TIME)

    text = (
        f"✦ **{to_smallcaps('system metrics & statistics')}** ✦\n\n"
        f"• 👥 **{to_smallcaps('total users')}** : `{total_users}`\n"
        f"• 📢 **{to_smallcaps('registered chats')}** : `{total_chats}`\n"
        f"• 📁 **{to_smallcaps('indexed files')}** : `{total_files}`\n"
        f"• 🚫 **{to_smallcaps('banned users')}** : `{banned_count}`\n"
        f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s Turbo`\n"
        f"• 📱 **{to_smallcaps('external players')}** : `PLAYit, MX, VLC, S Player`\n"
        f"• ⏱️ **{to_smallcaps('uptime')}** : `{time_formatter(seconds=uptime_sec)}`\n"
        f"• 🧠 **{to_smallcaps('cache keys')}** : `{cache_stats['cached_keys']}` / `{cache_stats['max_entries']}`\n"
        f"• 🎯 **{to_smallcaps('cache hit ratio')}** : `{cache_stats['hit_ratio_percent']}%`\n"
        f"• 🐍 **{to_smallcaps('python')}** : `{platform.python_version()}`"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"🍃 {to_smallcaps('database')}", callback_data="admin_dbstats")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")
        ]
    ]
    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("users"))
async def admin_users_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_users_page(message, page=1)

async def render_users_page(target_msg: Message, page: int = 1, is_edit: bool = False):
    total_users = await user_repo.get_total_users()
    limit = 10
    total_pages = max(1, math.ceil(total_users / limit))
    page = max(1, min(page, total_pages))
    skip = (page - 1) * limit

    users = await user_repo.get_users_paginated(skip=skip, limit=limit)

    text = f"✦ **{to_smallcaps('registered user directory')}** ✦\n\n"
    text += f"• **{to_smallcaps('page')}** : `{page}/{total_pages}` | **{to_smallcaps('total')}** : `{total_users}`\n\n"

    if not users:
        text += f"_{to_smallcaps('no users found.')}_\n"
    else:
        for idx, u in enumerate(users, start=skip + 1):
            uid = u.get("user_id", 0)
            name = u.get("first_name", "User")
            uname = f"@{u['username']}" if u.get("username") else "No username"
            status = "🚫 ʙᴀɴɴᴇᴅ" if u.get("is_banned") else "✅ ᴀᴄᴛɪᴠᴇ"
            text += f"`{idx}.` **{name}** (`{uid}`) - {uname} [{status}]\n"

    text += f"\n💡 {to_smallcaps('to inspect a user, send')} `/user <user_id>`"
    text += format_watermark()

    nav_btns = []
    if page > 1:
        nav_btns.append(InlineKeyboardButton("◀️ ᴘʀᴇᴠ", callback_data=f"admin_users_page_{page - 1}"))
    nav_btns.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data=f"admin_users_page_{page}"))
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("ɴᴇxᴛ ▶️", callback_data=f"admin_users_page_{page + 1}"))

    buttons = [nav_btns, [InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")]]

    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command(["user", "userinfo"]))
async def admin_userinfo_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if len(message.command) < 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text(
            f"📝 **{to_smallcaps('usage')}** : `/userinfo <user_id>`\n"
            f"• {to_smallcaps('example')}: `/userinfo 1892771262`"
        )
    target_id = int(message.command[1])
    await render_userinfo_card(message, target_id)

async def render_userinfo_card(target_msg: Message, target_id: int, is_edit: bool = False):
    u = await user_repo.get_user(target_id)
    if not u:
        msg = f"❌ **{to_smallcaps('user not found in database!')}** (`{target_id}`)"
        if is_edit:
            return await target_msg.edit_text(msg)
        return await target_msg.reply_text(msg)

    is_banned = u.get("is_banned", False)
    ban_label = "🚫 ʙᴀɴɴᴇᴅ" if is_banned else "✅ ᴀᴄᴛɪᴠᴇ"
    has_thumb = "✅ ᴄᴜsᴛᴏᴍ" if u.get("thumb_id") else ("🌐 ᴛʜᴀᴍ_ᴜʀʟ" if u.get("tham_url") else "❌ ɴᴏɴᴇ")
    custom_cap = "✅ sᴇᴛ" if u.get("custom_caption") else "❌ ᴅᴇғᴀᴜʟᴛ"
    caps_count = len(u.get("captions_list", []))
    auto_del = time_formatter(seconds=u.get("auto_delete_time", 0)) if u.get("auto_delete_time", 0) > 0 else "Disabled"
    created = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(u.get("created_at", time.time())))

    text = (
        f"✦ **{to_smallcaps('user inspection card')}** ✦\n\n"
        f"• 🆔 **{to_smallcaps('user id')}** : `{target_id}`\n"
        f"• 👤 **{to_smallcaps('first name')}** : {u.get('first_name', 'N/A')}\n"
        f"• 🏷️ **{to_smallcaps('username')}** : @{u.get('username') if u.get('username') else to_smallcaps('none')}\n"
        f"• 🛡️ **{to_smallcaps('account status')}** : `{ban_label}`\n"
        f"• 🖼️ **{to_smallcaps('thumbnail')}** : `{has_thumb}`\n"
        f"• 📝 **{to_smallcaps('custom caption')}** : `{custom_cap}` (`{caps_count}` in list)\n"
        f"• 🔤 **{to_smallcaps('prefix / suffix')}** : `{u.get('prefix', '') or 'None'}` / `{u.get('suffix', '') or 'None'}`\n"
        f"• ⏱️ **{to_smallcaps('auto-delete')}** : `{auto_del}`\n"
        f"• 📅 **{to_smallcaps('joined')}** : `{created} UTC`"
        f"{format_watermark()}"
    )

    ban_btn_text = f"✅ {to_smallcaps('unban user')}" if is_banned else f"🚫 {to_smallcaps('ban user')}"
    buttons = [
        [
            InlineKeyboardButton(ban_btn_text, callback_data=f"admin_toggle_ban_{target_id}"),
            InlineKeyboardButton(f"👥 {to_smallcaps('user list')}", callback_data="admin_users_page_1")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")
        ]
    ]

    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("cache"))
async def admin_cache_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_cache_card(message)

async def render_cache_card(target_msg: Message, is_edit: bool = False):
    stats = await cache.get_stats()
    text = (
        f"✦ **{to_smallcaps('in-memory o(1) cache monitor')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('cache engine')}** : `FastMemoryCache (O(1) LRU + TTL)`\n"
        f"• 📦 **{to_smallcaps('active keys')}** : `{stats['cached_keys']}` / `{stats['max_entries']}`\n"
        f"• 🎯 **{to_smallcaps('cache hits')}** : `{stats['hits']}`\n"
        f"• ❌ **{to_smallcaps('cache misses')}** : `{stats['misses']}`\n"
        f"• 🚀 **{to_smallcaps('hit ratio')}** : `{stats['hit_ratio_percent']}%`\n"
        f"• ⏱️ **{to_smallcaps('default ttl')}** : `{Config.CACHE_TTL}s`"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('clear all cache')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="admin_cache_info")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")
        ]
    ]
    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command(["database", "dbstats"]))
async def admin_database_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_database_card(message)

async def render_database_card(target_msg: Message, is_edit: bool = False):
    db_name = Config.DATABASE_NAME
    conn_status = "CONNECTED (MONGODB) ✅" if mongo.is_connected else "UNIFIED IN-MEMORY DB ⚡"

    t0 = time.time()
    try:
        if mongo.is_connected and mongo.client:
            await mongo.client.admin.command('ping')
            ping_ms = round((time.time() - t0) * 1000, 2)
        else:
            ping_ms = 0.05
    except Exception:
        ping_ms = 0.1

    users_cnt = await user_repo.col.count_documents({})
    chats_cnt = await chat_repo.col.count_documents({})
    files_cnt = await file_repo.col.count_documents({})
    autodel_cnt = await chat_repo.auto_del_col.count_documents({})

    text = (
        f"✦ **{to_smallcaps('single unified database monitor')}** ✦\n\n"
        f"• 🍃 **{to_smallcaps('database name')}** : `{db_name}`\n"
        f"• 🔗 **{to_smallcaps('engine mode')}** : `{conn_status}`\n"
        f"• ⚡ **{to_smallcaps('db latency')}** : `{ping_ms} ms`\n\n"
        f"📊 **{to_smallcaps('collection counts')}** :\n"
        f"• 👤 `users` : `{users_cnt}` documents\n"
        f"• 💬 `chats` : `{chats_cnt}` documents\n"
        f"• 📁 `files` : `{files_cnt}` documents\n"
        f"• ⏱️ `auto_delete` : `{autodel_cnt}` queue items"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="admin_dbstats"),
            InlineKeyboardButton(f"🧹 {to_smallcaps('clear cache')}", callback_data="admin_clear_cache")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")
        ]
    ]
    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("logs"))
async def admin_logs_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_logs_card(message)

async def render_logs_card(target_msg: Message, is_edit: bool = False):
    lines = MEMORY_LOGS[-20:] if MEMORY_LOGS else ["No logs recorded yet."]
    log_content = "\n".join(lines)
    if len(log_content) > 3500:
        log_content = log_content[-3500:]

    text = (
        f"✦ **{to_smallcaps('application runtime logs')}** ✦\n\n"
        f"```\n{log_content}\n```"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="admin_logs"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to panel')}", callback_data="admin_panel_back")
        ]
    ]
    if is_edit:
        await target_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await target_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command(["devilmod", "devmode"]))
async def devil_mod_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return

    arg = message.command[1].lower() if len(message.command) > 1 else ""
    if arg in ["on", "enable", "1", "true"]:
        set_devil_mode(True)
    elif arg in ["off", "disable", "0", "false"]:
        set_devil_mode(False)
    else:
        set_devil_mode(not is_devil_mode_active())

    status = "🔥 **ᴇɴᴀʙʟᴇᴅ**" if is_devil_mode_active() else "⚪ **ᴅɪsᴀʙʟᴇᴅ**"
    await message.reply_text(
        f"😈 **{to_smallcaps('devil / developer mode')}** : {status}\n\n"
        f"• {to_smallcaps('use')} `/dev` {to_smallcaps('to access the full developer control console.')}"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command(["dev", "developer"]))
async def dev_console_command(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await render_dev_console(message)

async def render_dev_console(target_msg: Message, is_edit: bool = False):
    users_count = await user_repo.get_total_users()
    chats_count = await chat_repo.get_total_chats()
    files_count = await file_repo.get_total_files()
    cache_stats = await cache.get_stats()
    uptime_sec = round(float(time.time()) - START_TIME)
    active_tasks = len(asyncio.all_tasks())
    gc_objects = len(gc.get_objects())
    devil_status = "🔥 ᴀᴄᴛɪᴠᴇ (ᴏɴ)" if is_devil_mode_active() else "⚪ ɪɴᴀᴄᴛɪᴠᴇ (ᴏғғ)"

    dev_text = (
        f"🛠️ **{to_smallcaps('mmw pro engine dev console & diagnostics')}**\n\n"
        f"• 😈 **{to_smallcaps('devil mode')}** : `{devil_status}`\n"
        f"• 🐍 **{to_smallcaps('python version')}** : `{sys.version.split()[0]}`\n"
        f"• ⚡ **{to_smallcaps('stream engine')}** : `12 MB/s ByteStreamer + 4 Players`\n"
        f"• 🍃 **{to_smallcaps('database')}** : `Single Unified DB + O(1) Cache`\n"
        f"  - {to_smallcaps('active cache keys')} : `{cache_stats['cached_keys']}` / `{cache_stats['max_entries']}`\n"
        f"  - {to_smallcaps('cache hit ratio')} : `{cache_stats['hit_ratio_percent']}%`\n"
        f"• 🔄 **{to_smallcaps('active asyncio tasks')}** : `{active_tasks}`\n"
        f"• 🧹 **{to_smallcaps('tracked gc objects')}** : `{gc_objects}`\n"
        f"• ⏱️ **{to_smallcaps('system uptime')}** : `{time_formatter(seconds=uptime_sec)}`\n"
        f"• 👥 **{to_smallcaps('users / chats / files')}** : `{users_count}` / `{chats_count}` / `{files_count}`"
        f"{format_watermark()}"
    )

    toggle_btn_text = f"⚪ {to_smallcaps('disable devilmod')}" if is_devil_mode_active() else f"🔥 {to_smallcaps('enable devilmod')}"
    buttons = [
        [
            InlineKeyboardButton(toggle_btn_text, callback_data="dev_toggle"),
            InlineKeyboardButton(f"🧹 {to_smallcaps('force gc')}", callback_data="dev_gc")
        ],
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('admin stats')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"⚙️ {to_smallcaps('config')}", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('clear cache')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"🔄 {to_smallcaps('restart bot')}", callback_data="admin_restart")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('close')}", callback_data="dev_close")
        ]
    ]

    if is_edit:
        await target_msg.edit_text(dev_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await target_msg.reply_text(dev_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# ----------------- BROADCAST / BAN / RESTART ----------------- #

@Client.on_callback_query(filters.regex(r"^admin_broadcast_info$"))
async def admin_broadcast_guide(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("access denied!"), show_alert=True)
    text = (
        f"✦ **{to_smallcaps('broadcast instructions')}** ✦\n\n"
        f"• 📢 **{to_smallcaps('usage')}** :\n"
        f"  {to_smallcaps('reply to any message, photo, video or document with')} `/broadcast`\n\n"
        f"• 🚀 **{to_smallcaps('mechanism')}** :\n"
        f"  {to_smallcaps('the bot will copy the message to all registered users with floodwait protection.')}"
        f"{format_watermark()}"
    )
    buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data="admin_panel_back")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("broadcast"))
async def broadcast_command_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if not message.reply_to_message:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('please reply to the message you want to broadcast.')}**\n\n"
            f"• **{to_smallcaps('usage')}** : {to_smallcaps('reply to message with')} `/broadcast`"
        )

    users = await user_repo.get_all_users()
    status = await message.reply_text(f"📢 **{to_smallcaps(f'starting broadcast to {len(users)} users...')}**")

    success = 0
    failed = 0
    blocked = 0

    for u in users:
        uid = u["user_id"]
        try:
            await message.reply_to_message.copy(uid)
            success += 1
            await asyncio.sleep(0.04)
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            try:
                await message.reply_to_message.copy(uid)
                success += 1
            except Exception:
                failed += 1
        except (UserIsBlocked, InputUserDeactivated):
            blocked += 1
        except Exception:
            failed += 1

    await status.edit_text(
        f"✦ **{to_smallcaps('broadcast completed')}** ✦\n\n"
        f"• ✅ **{to_smallcaps('successful')}** : `{success}`\n"
        f"• 🚫 **{to_smallcaps('blocked / deactivated')}** : `{blocked}`\n"
        f"• ❌ **{to_smallcaps('failed')}** : `{failed}`\n"
        f"• 👥 **{to_smallcaps('total targets')}** : `{len(users)}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command("ban"))
async def ban_user_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('usage')}** : `/ban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.ban_user(target_id)
    await message.reply_text(f"🚫 **{to_smallcaps(f'user {target_id} has been banned!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("unban"))
async def unban_user_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('usage')}** : `/unban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.unban_user(target_id)
    await message.reply_text(f"✅ **{to_smallcaps(f'user {target_id} has been unbanned!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("restart"))
async def restart_command_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await message.reply_text(f"🔄 **{to_smallcaps('bot is restarting now...')}**")
    try:
        with open(RESTART_MARKER_FILE, "w") as f:
            f.write(f"{float(time.time())}")
    except Exception:
        pass
    os.execl(sys.executable, sys.executable, "main.py")

# ----------------- ADMIN CALLBACKS ----------------- #

@Client.on_callback_query(filters.regex(r"^admin_(panel_back|stats|clear_cache|clean|restart|close|settings|dbstats|cache_info|logs)$"))
async def admin_control_callbacks(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("access denied!"), show_alert=True)

    action = query.matches[0].group(1)

    if action == "panel_back":
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "stats":
        await render_stats_card(query.message, is_edit=True)
    elif action in ["clear_cache", "clean"]:
        await cache.clear()
        await query.answer(to_smallcaps("in-memory cache cleared!"), show_alert=True)
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "cache_info":
        await render_cache_card(query.message, is_edit=True)
    elif action == "dbstats":
        await render_database_card(query.message, is_edit=True)
    elif action == "logs":
        await render_logs_card(query.message, is_edit=True)
    elif action == "settings":
        conf_text = (
            f"✦ **{to_smallcaps('active engine configuration')}** ✦\n\n"
            f"• 👑 **{to_smallcaps('owner id')}** : `{Config.OWNER_ID}`\n"
            f"• 👥 **{to_smallcaps('admins')}** : `{len(Config.ADMINS)} registered`\n"
            f"• 📢 **{to_smallcaps('bin channel')}** : `{Config.BIN_CHANNEL}`\n"
            f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s`\n"
            f"• 📱 **{to_smallcaps('4 external players')}** : `PLAYit, MX, VLC, S Player`\n"
            f"• 🌐 **{to_smallcaps('base url')}** : `{Config.BASE_URL}`\n"
            f"• 🌐 **{to_smallcaps('port')}** : `{Config.PORT}`\n"
            f"• 🧠 **{to_smallcaps('cache ttl')}** : `{Config.CACHE_TTL}s`\n"
            f"• 👷 **{to_smallcaps('workers')}** : `{Config.WORKERS}`"
            f"{format_watermark()}"
        )
        btns = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back')}", callback_data="admin_panel_back")]]
        await query.message.edit_text(conf_text, reply_markup=InlineKeyboardMarkup(btns), disable_web_page_preview=True)
    elif action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
    elif action == "restart":
        await query.answer(to_smallcaps("initiating bot restart..."), show_alert=True)
        await query.message.edit_text(f"🔄 **{to_smallcaps('bot is restarting now...')}**")
        try:
            with open(RESTART_MARKER_FILE, "w") as f:
                f.write(f"{float(time.time())}")
        except Exception:
            pass
        os.execl(sys.executable, sys.executable, "main.py")

@Client.on_callback_query(filters.regex(r"^admin_users_page_(\d+)$"))
async def admin_users_pagination_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("access denied!"), show_alert=True)
    page = int(query.matches[0].group(1))
    await render_users_page(query.message, page=page, is_edit=True)

@Client.on_callback_query(filters.regex(r"^admin_toggle_ban_(\d+)$"))
async def admin_toggle_ban_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("access denied!"), show_alert=True)
    target_id = int(query.matches[0].group(1))
    u = await user_repo.get_user(target_id)
    if u and u.get("is_banned"):
        await user_repo.unban_user(target_id)
        await query.answer(to_smallcaps("user unbanned!"), show_alert=True)
    else:
        await user_repo.ban_user(target_id)
        await query.answer(to_smallcaps("user banned!"), show_alert=True)
    await render_userinfo_card(query.message, target_id, is_edit=True)

@Client.on_callback_query(filters.regex(r"^dev_(toggle|close|gc)$"))
async def dev_callbacks(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("access denied!"), show_alert=True)

    action = query.matches[0].group(1)
    if action == "toggle":
        set_devil_mode(not is_devil_mode_active())
        await query.answer(to_smallcaps(f"devil mode {'enabled' if is_devil_mode_active() else 'disabled'}!"))
        await render_dev_console(query.message, is_edit=True)
    elif action == "gc":
        collected = gc.collect()
        await query.answer(to_smallcaps(f"gc complete: {collected} objects freed!"), show_alert=True)
        await render_dev_console(query.message, is_edit=True)
    elif action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
