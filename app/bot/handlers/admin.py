import sys
import os
import time
import math
import asyncio
import gc
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import Config
from app.database.repositories.user_repo import user_repo
from app.database.repositories.chat_repo import chat_repo
from app.database.repositories.file_repo import file_repo
from app.database.mongodb import mongo
from app.utils.cache import cache
from app.utils.font import to_smallcaps, format_watermark
from app.utils.helpers import (
    check_admin,
    is_admin,
    humanbytes,
    time_formatter,
    is_devil_mode_active,
    set_devil_mode
)
from app.utils.logger import logger

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
    devil_status = "🔥 ACTIVE" if is_devil_mode_active() else "⚪ DISABLED"

    text = (
        f"✦ **{to_smallcaps('ADMIN CONTROL PANEL')}** ✦\n\n"
        f"👑 **{to_smallcaps('ADMIN MODE ACTIVE')}**\n\n"
        f"• 👥 **{to_smallcaps('TOTAL USERS')}** : `{total_users}`\n"
        f"• 📢 **{to_smallcaps('TOTAL CHATS')}** : `{total_chats}`\n"
        f"• 📁 **{to_smallcaps('STREAM FILES')}** : `{total_files}`\n"
        f"• 🚫 **{to_smallcaps('BANNED USERS')}** : `{banned_count}`\n"
        f"• ⚡ **{to_smallcaps('CACHE KEYS')}** : `{cache_stats['cached_keys']}` (Hit: `{cache_stats['hit_ratio_percent']}%`)\n"
        f"• 😈 **{to_smallcaps('DEVIL MODE')}** : `{devil_status}`\n"
        f"• 💓 **{to_smallcaps('KEEP-ALIVE')}** : `6 Pingers Every 6s (Active)`\n"
        f"• 🚀 **{to_smallcaps('ENGINE')}** : `Production Async Mongo + Pyrofork`\n\n"
        f"💡 **{to_smallcaps('ADMIN QUICK ACTIONS:')}**"
        f"{format_watermark()}"
    )

    buttons = [
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('STATS')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"👥 {to_smallcaps('USER LIST')}", callback_data="admin_users_page_1")
        ],
        [
            InlineKeyboardButton(f"📢 {to_smallcaps('BROADCAST')}", callback_data="admin_broadcast_info"),
            InlineKeyboardButton(f"🍃 {to_smallcaps('DATABASE')}", callback_data="admin_dbstats")
        ],
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('CLEAR CACHE')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"⚙️ {to_smallcaps('CONFIG')}", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('RESTART BOT')}", callback_data="admin_restart"),
            InlineKeyboardButton(f"❌ {to_smallcaps('CLOSE')}", callback_data="admin_close")
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

    import platform
    text = (
        f"✦ **{to_smallcaps('SYSTEM METRICS & STATISTICS')}** ✦\n\n"
        f"• 👥 **{to_smallcaps('TOTAL USERS')}** : `{total_users}`\n"
        f"• 📢 **{to_smallcaps('REGISTERED CHATS')}** : `{total_chats}`\n"
        f"• 📁 **{to_smallcaps('INDEXED FILES')}** : `{total_files}`\n"
        f"• 🚫 **{to_smallcaps('BANNED USERS')}** : `{banned_count}`\n"
        f"• ⏱️ **{to_smallcaps('UPTIME')}** : `{time_formatter(seconds=uptime_sec)}`\n"
        f"• ⚡ **{to_smallcaps('CACHE KEYS')}** : `{cache_stats['cached_keys']}` / `{cache_stats['max_entries']}`\n"
        f"• 🎯 **{to_smallcaps('CACHE HITS / MISSES')}** : `{cache_stats['hits']}` / `{cache_stats['misses']}` (`{cache_stats['hit_ratio_percent']}%`)\n"
        f"• 🐍 **{to_smallcaps('PYTHON')}** : `{platform.python_version()}`\n"
        f"• 👷 **{to_smallcaps('CONCURRENT WORKERS')}** : `{Config.WORKERS}`\n"
        f"• 👑 **{to_smallcaps('AUTHORIZED ADMINS')}** : `{len(Config.ADMINS)}`"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('REFRESH')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"🍃 {to_smallcaps('DATABASE')}", callback_data="admin_dbstats")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")
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

    text = f"✦ **{to_smallcaps('REGISTERED USER DIRECTORY')}** ✦\n\n"
    text += f"• **{to_smallcaps('PAGE')}** : `{page}/{total_pages}` | **{to_smallcaps('TOTAL')}** : `{total_users}`\n\n"

    if not users:
        text += f"_{to_smallcaps('No users found.')}_\n"
    else:
        for idx, u in enumerate(users, start=skip + 1):
            uid = u.get("user_id", 0)
            name = u.get("first_name", "User")
            uname = f"@{u['username']}" if u.get("username") else "No username"
            status = "🚫 BANNED" if u.get("is_banned") else "✅ ACTIVE"
            text += f"`{idx}.` **{name}** (`{uid}`) - {uname} [{status}]\n"

    text += f"\n💡 {to_smallcaps('To inspect a user, send')} `/user <user_id>`"
    text += format_watermark()

    nav_btns = []
    if page > 1:
        nav_btns.append(InlineKeyboardButton("◀️ Previous", callback_data=f"admin_users_page_{page - 1}"))
    nav_btns.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data=f"admin_users_page_{page}"))
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_users_page_{page + 1}"))

    buttons = [nav_btns, [InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")]]

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
            f"📝 **{to_smallcaps('USAGE')}**: `/userinfo <user_id>`\n"
            f"• {to_smallcaps('Example')}: `/userinfo 1892771262`"
        )
    target_id = int(message.command[1])
    await render_userinfo_card(message, target_id)

async def render_userinfo_card(target_msg: Message, target_id: int, is_edit: bool = False):
    u = await user_repo.get_user(target_id)
    if not u:
        msg = f"❌ **{to_smallcaps('USER NOT FOUND IN DATABASE!')}** (`{target_id}`)"
        if is_edit:
            return await target_msg.edit_text(msg)
        return await target_msg.reply_text(msg)

    is_banned = u.get("is_banned", False)
    ban_label = "🚫 BANNED" if is_banned else "✅ ACTIVE"
    has_thumb = "✅ Custom" if u.get("thumb_id") else ("🌐 THAM_URL" if u.get("tham_url") else "❌ None")
    custom_cap = "✅ Set" if u.get("custom_caption") else "❌ Default"
    caps_count = len(u.get("captions_list", []))
    auto_del = time_formatter(seconds=u.get("auto_delete_time", 0)) if u.get("auto_delete_time", 0) > 0 else "Disabled"
    created = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(u.get("created_at", time.time())))

    text = (
        f"✦ **{to_smallcaps('USER INSPECTION CARD')}** ✦\n\n"
        f"• 🆔 **{to_smallcaps('USER ID')}** : `{target_id}`\n"
        f"• 👤 **{to_smallcaps('FIRST NAME')}** : {u.get('first_name', 'N/A')}\n"
        f"• 🏷️ **{to_smallcaps('USERNAME')}** : @{u.get('username') if u.get('username') else to_smallcaps('NONE')}\n"
        f"• 🛡️ **{to_smallcaps('ACCOUNT STATUS')}** : `{ban_label}`\n"
        f"• 🖼️ **{to_smallcaps('THUMBNAIL')}** : `{has_thumb}`\n"
        f"• 📝 **{to_smallcaps('CUSTOM CAPTION')}** : `{custom_cap}` (`{caps_count}` in list)\n"
        f"• 🔤 **{to_smallcaps('PREFIX / SUFFIX')}** : `{u.get('prefix', '') or 'None'}` / `{u.get('suffix', '') or 'None'}`\n"
        f"• ⏱️ **{to_smallcaps('AUTO-DELETE')}** : `{auto_del}`\n"
        f"• 📅 **{to_smallcaps('JOINED')}** : `{created} UTC`"
        f"{format_watermark()}"
    )

    ban_btn_text = f"✅ {to_smallcaps('UNBAN USER')}" if is_banned else f"🚫 {to_smallcaps('BAN USER')}"
    buttons = [
        [
            InlineKeyboardButton(ban_btn_text, callback_data=f"admin_toggle_ban_{target_id}"),
            InlineKeyboardButton(f"👥 {to_smallcaps('USER LIST')}", callback_data="admin_users_page_1")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")
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
        f"✦ **{to_smallcaps('IN-MEMORY CACHE MONITOR')}** ✦\n\n"
        f"• ⚡ **{to_smallcaps('CACHE ENGINE')}** : `FastMemoryCache (In-Memory TTL)`\n"
        f"• 📦 **{to_smallcaps('ACTIVE KEYS')}** : `{stats['cached_keys']}` / `{stats['max_entries']}`\n"
        f"• 🎯 **{to_smallcaps('CACHE HITS')}** : `{stats['hits']}`\n"
        f"• ❌ **{to_smallcaps('CACHE MISSES')}** : `{stats['misses']}`\n"
        f"• 🚀 **{to_smallcaps('HIT RATIO')}** : `{stats['hit_ratio_percent']}%`\n"
        f"• ⏱️ **{to_smallcaps('DEFAULT TTL')}** : `{Config.CACHE_TTL}s`\n\n"
        f"💡 {to_smallcaps('Clearing cache forces immediate fresh database reads on next query.')}"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('CLEAR ALL CACHE')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"🔄 {to_smallcaps('REFRESH')}", callback_data="admin_cache_info")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")
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
    conn_status = "CONNECTED ✅" if mongo.is_connected else "DISCONNECTED ❌"

    t0 = time.time()
    try:
        if mongo.client:
            await mongo.client.admin.command('ping')
            ping_ms = round((time.time() - t0) * 1000, 2)
        else:
            ping_ms = -1
    except Exception:
        ping_ms = -1

    users_cnt = await user_repo.col.count_documents({}) if mongo.is_connected else 0
    chats_cnt = await chat_repo.col.count_documents({}) if mongo.is_connected else 0
    files_cnt = await file_repo.col.count_documents({}) if mongo.is_connected else 0
    autodel_cnt = await chat_repo.auto_del_col.count_documents({}) if mongo.is_connected else 0

    text = (
        f"✦ **{to_smallcaps('MONGODB DATABASE MONITOR')}** ✦\n\n"
        f"• 🍃 **{to_smallcaps('DATABASE NAME')}** : `{db_name}`\n"
        f"• 🔗 **{to_smallcaps('CONNECTION')}** : `{conn_status}`\n"
        f"• ⚡ **{to_smallcaps('DB PING')}** : `{ping_ms} ms`\n\n"
        f"📊 **{to_smallcaps('COLLECTION COUNTS')}** :\n"
        f"• 👤 `users` : `{users_cnt}` documents\n"
        f"• 💬 `chats` : `{chats_cnt}` documents\n"
        f"• 📁 `files` : `{files_cnt}` documents\n"
        f"• ⏱️ `auto_delete` : `{autodel_cnt}` queue items\n\n"
        f"⚡ {to_smallcaps('Indexes on user_id, chat_id, file_id, delete_at are active.')}"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('REFRESH')}", callback_data="admin_dbstats"),
            InlineKeyboardButton(f"🧹 {to_smallcaps('CLEAR CACHE')}", callback_data="admin_clear_cache")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")
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
    from app.utils.logger import MEMORY_LOGS
    lines = MEMORY_LOGS[-20:] if MEMORY_LOGS else ["No logs recorded yet."]
    log_content = "\n".join(lines)
    if len(log_content) > 3500:
        log_content = log_content[-3500:]

    text = (
        f"✦ **{to_smallcaps('APPLICATION RUNTIME LOGS')}** ✦\n\n"
        f"```\n{log_content}\n```"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('REFRESH')}", callback_data="admin_logs"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('BACK TO PANEL')}", callback_data="admin_panel_back")
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
        # Toggle
        set_devil_mode(not is_devil_mode_active())

    status = "🔥 **ENABLED**" if is_devil_mode_active() else "⚪ **DISABLED**"
    await message.reply_text(
        f"😈 **{to_smallcaps('DEVIL / DEVELOPER MODE')}** : {status}\n\n"
        f"• {to_smallcaps('Detailed execution diagnostics, memory stats, and task inspector are active.')}\n"
        f"• {to_smallcaps('Use')} `/dev` {to_smallcaps('to access the full developer control console.')}"
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
    devil_status = "🔥 ACTIVE (ON)" if is_devil_mode_active() else "⚪ INACTIVE (OFF)"

    dev_text = (
        f"🛠️ **{to_smallcaps('MMW PRO ENGINE DEV CONSOLE & DIAGNOSTICS')}**\n\n"
        f"• 😈 **{to_smallcaps('DEVIL MODE')}** : `{devil_status}`\n"
        f"• 🐍 **{to_smallcaps('PYTHON VERSION')}** : `{sys.version.split()[0]}`\n"
        f"• ⚡ **{to_smallcaps('BOT FRAMEWORK')}** : `Pyrofork Async Bot API`\n"
        f"• 🍃 **{to_smallcaps('DATABASE')}** : `MongoDB Motor Async Driver`\n"
        f"• 🚀 **{to_smallcaps('CACHE LAYER')}** : `FastMemoryCache (Active)`\n"
        f"  - {to_smallcaps('Active Cache Keys')} : `{cache_stats['cached_keys']}` / `{cache_stats['max_entries']}`\n"
        f"  - {to_smallcaps('Cache Hit Ratio')} : `{cache_stats['hit_ratio_percent']}%`\n"
        f"• 🔄 **{to_smallcaps('ACTIVE ASYNCIO TASKS')}** : `{active_tasks}`\n"
        f"• 🧹 **{to_smallcaps('TRACKED GC OBJECTS')}** : `{gc_objects}`\n"
        f"• ⏱️ **{to_smallcaps('SYSTEM UPTIME')}** : `{time_formatter(seconds=uptime_sec)}`\n"
        f"• 👥 **{to_smallcaps('USERS')}** / 📢 **{to_smallcaps('CHATS')}** / 📁 **{to_smallcaps('FILES')}** : `{users_count}` / `{chats_count}` / `{files_count}`\n"
        f"• 👷 **{to_smallcaps('WORKERS')}** : `{Config.WORKERS}` | 👑 **{to_smallcaps('ADMINS')}** : `{len(Config.ADMINS)}`\n\n"
        f"⚡ **{to_smallcaps('POWERED BY')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
    )

    toggle_btn_text = "⚪ Disable DevilMod" if is_devil_mode_active() else "🔥 Enable DevilMod"
    buttons = [
        [
            InlineKeyboardButton(toggle_btn_text, callback_data="dev_toggle"),
            InlineKeyboardButton(f"🧹 {to_smallcaps('FORCE GC')}", callback_data="dev_gc")
        ],
        [
            InlineKeyboardButton(f"📊 {to_smallcaps('ADMIN STATS')}", callback_data="admin_stats"),
            InlineKeyboardButton(f"⚙️ {to_smallcaps('CONFIG')}", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(f"🧹 {to_smallcaps('CLEAR CACHE')}", callback_data="admin_clear_cache"),
            InlineKeyboardButton(f"🔄 {to_smallcaps('RESTART BOT')}", callback_data="admin_restart")
        ],
        [
            InlineKeyboardButton(f"❌ {to_smallcaps('CLOSE')}", callback_data="dev_close")
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
        return await query.answer(to_smallcaps("ACCESS DENIED!"), show_alert=True)
    text = (
        f"✦ **{to_smallcaps('BROADCAST INSTRUCTIONS')}** ✦\n\n"
        f"• 📢 **{to_smallcaps('USAGE')}** :\n"
        f"  {to_smallcaps('Reply to any message, photo, video or document with')} `/broadcast`\n\n"
        f"• 🚀 **{to_smallcaps('MECHANISM')}** :\n"
        f"  {to_smallcaps('The bot will forward/copy the message to all registered users with FloodWait protection.')}"
        f"{format_watermark()}"
    )
    buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('BACK')}", callback_data="admin_panel_back")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.private & filters.command("broadcast"))
async def broadcast_command_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if not message.reply_to_message:
        return await message.reply_text(
            f"⚠️ **{to_smallcaps('PLEASE REPLY TO THE MESSAGE YOU WANT TO BROADCAST.')}**\n\n"
            f"• **{to_smallcaps('USAGE')}**: {to_smallcaps('Reply to message with')} `/broadcast`"
        )

    users = await user_repo.get_all_users()
    status = await message.reply_text(f"📢 **{to_smallcaps(f'STARTING BROADCAST TO {len(users)} USERS...')}**")

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
        f"✦ **{to_smallcaps('BROADCAST COMPLETED')}** ✦\n\n"
        f"• ✅ **{to_smallcaps('SUCCESSFUL')}** : `{success}`\n"
        f"• 🚫 **{to_smallcaps('BLOCKED / DEACTIVATED')}** : `{blocked}`\n"
        f"• ❌ **{to_smallcaps('FAILED')}** : `{failed}`\n"
        f"• 👥 **{to_smallcaps('TOTAL TARGETS')}** : `{len(users)}`"
        f"{format_watermark()}"
    )

@Client.on_message(filters.private & filters.command("ban"))
async def ban_user_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('USAGE')}**: `/ban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.ban_user(target_id)
    await message.reply_text(f"🚫 **{to_smallcaps(f'USER {target_id} HAS BEEN BANNED!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("unban"))
async def unban_user_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"📝 **{to_smallcaps('USAGE')}**: `/unban <user_id>`")

    target_id = int(message.command[1])
    await user_repo.unban_user(target_id)
    await message.reply_text(f"✅ **{to_smallcaps(f'USER {target_id} HAS BEEN UNBANNED!')}**{format_watermark()}")

@Client.on_message(filters.private & filters.command("restart"))
async def restart_command_handler(client: Client, message: Message):
    if not await check_admin(client, message):
        return
    await message.reply_text(f"🔄 **{to_smallcaps('BOT IS RESTARTING NOW...')}**")
    from app.services.keepalive_service import RESTART_MARKER_FILE
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
        return await query.answer(to_smallcaps("ACCESS DENIED!"), show_alert=True)

    action = query.matches[0].group(1)

    if action == "panel_back":
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "stats":
        await render_stats_card(query.message, is_edit=True)
    elif action in ["clear_cache", "clean"]:
        await cache.clear()
        await query.answer(to_smallcaps("IN-MEMORY CACHE CLEARED!"), show_alert=True)
        await render_admin_dashboard(query.message, is_edit=True)
    elif action == "cache_info":
        await render_cache_card(query.message, is_edit=True)
    elif action == "dbstats":
        await render_database_card(query.message, is_edit=True)
    elif action == "logs":
        await render_logs_card(query.message, is_edit=True)
    elif action == "settings":
        conf_text = (
            f"✦ **{to_smallcaps('ACTIVE ENGINE CONFIGURATION')}** ✦\n\n"
            f"• 👑 **{to_smallcaps('OWNER ID')}** : `{Config.OWNER_ID}`\n"
            f"• 👥 **{to_smallcaps('ADMINS')}** : `{len(Config.ADMINS)} registered`\n"
            f"• 📢 **{to_smallcaps('BIN CHANNEL')}** : `{Config.BIN_CHANNEL}`\n"
            f"• 🌐 **{to_smallcaps('BASE URL')}** : `{Config.BASE_URL}`\n"
            f"• 🌐 **{to_smallcaps('PORT')}** : `{Config.PORT}`\n"
            f"• ⚡ **{to_smallcaps('CACHE TTL')}** : `{Config.CACHE_TTL}s`\n"
            f"• 👷 **{to_smallcaps('WORKERS')}** : `{Config.WORKERS}`\n"
            f"• 🏷️ **{to_smallcaps('WATERMARK')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
            f"{format_watermark()}"
        )
        btns = [[InlineKeyboardButton(f"🔙 {to_smallcaps('BACK')}", callback_data="admin_panel_back")]]
        await query.message.edit_text(conf_text, reply_markup=InlineKeyboardMarkup(btns), disable_web_page_preview=True)
    elif action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
    elif action == "restart":
        await query.answer(to_smallcaps("INITIATING BOT RESTART..."), show_alert=True)
        await query.message.edit_text(f"🔄 **{to_smallcaps('BOT IS RESTARTING NOW...')}**")
        from app.services.keepalive_service import RESTART_MARKER_FILE
        try:
            with open(RESTART_MARKER_FILE, "w") as f:
                f.write(f"{float(time.time())}")
        except Exception:
            pass
        os.execl(sys.executable, sys.executable, "main.py")

@Client.on_callback_query(filters.regex(r"^admin_users_page_(\d+)$"))
async def admin_users_pagination_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("ACCESS DENIED!"), show_alert=True)
    page = int(query.matches[0].group(1))
    await render_users_page(query.message, page=page, is_edit=True)

@Client.on_callback_query(filters.regex(r"^admin_toggle_ban_(\d+)$"))
async def admin_toggle_ban_callback(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("ACCESS DENIED!"), show_alert=True)
    target_id = int(query.matches[0].group(1))
    u = await user_repo.get_user(target_id)
    if u and u.get("is_banned"):
        await user_repo.unban_user(target_id)
        await query.answer(to_smallcaps("USER UNBANNED!"), show_alert=True)
    else:
        await user_repo.ban_user(target_id)
        await query.answer(to_smallcaps("USER BANNED!"), show_alert=True)
    await render_userinfo_card(query.message, target_id, is_edit=True)

# ----------------- DEVIL / DEV CALLBACKS ----------------- #

@Client.on_callback_query(filters.regex(r"^dev_(toggle|close|gc)$"))
async def dev_callbacks(client: Client, query: CallbackQuery):
    if not await is_admin(client, query.from_user.id):
        return await query.answer(to_smallcaps("ACCESS DENIED!"), show_alert=True)

    action = query.matches[0].group(1)
    if action == "toggle":
        set_devil_mode(not is_devil_mode_active())
        await query.answer(to_smallcaps(f"DEVIL MODE {'ENABLED' if is_devil_mode_active() else 'DISABLED'}!"))
        await render_dev_console(query.message, is_edit=True)
    elif action == "gc":
        collected = gc.collect()
        await query.answer(to_smallcaps(f"GC COMPLETE: {collected} OBJECTS FREED!"), show_alert=True)
        await render_dev_console(query.message, is_edit=True)
    elif action == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
