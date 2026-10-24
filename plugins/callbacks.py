from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from plugins.core_db import user_repo, chat_repo, file_repo
from plugins.core_utils import to_smallcaps, format_watermark

async def render_help_menu(target_msg: Message, user, is_admin: bool, is_edit: bool = True):
    help_text = (
        f"✦ **{to_smallcaps('smart help center')}** ✦\n\n"
        f"👋 **{to_smallcaps('hello')} {user.mention}** !\n"
        f"{to_smallcaps('explore our categorized guides below for all auto & pro features:')}\n\n"
        f"• ✏️ **{to_smallcaps('auto & pro renamer')}** : {to_smallcaps('rename, auto-rename, prefix & suffix')}\n"
        f"• 🗜️ **{to_smallcaps('auto & pro compressor')}** : {to_smallcaps('h.264 presets, auto-compress & target mb')}\n"
        f"• ⚡ **{to_smallcaps('12 mb/s streamer')}** : {to_smallcaps('4 external players (playit, mx, vlc, s player)')}\n"
        f"• 📝 **{to_smallcaps('auto captions')}** : {to_smallcaps('dynamic templates & cap[] queue manager')}\n"
        f"• 🤝 **{to_smallcaps('auto accept')}** : {to_smallcaps('auto-approve channel & group join requests')}\n"
        f"• 🖼️ **{to_smallcaps('thumbnail')}** : {to_smallcaps('custom photo & tham_url caching')}\n"
        f"• ⏱️ **{to_smallcaps('auto-delete')}** : {to_smallcaps('timed message sweeper')}\n"
        f"• 🎛️ **{to_smallcaps('file pro studio')}** : {to_smallcaps('extract/add audio & subs, trim, mediainfo')}\n"
        f"• 🔑 **{to_smallcaps('session')}** : {to_smallcaps('pyrogram & telethon string session generator')}\n"
    )
    if is_admin:
        help_text += f"• 👑 **{to_smallcaps('admin')}** : {to_smallcaps('broadcast, ban/unban, single db & cache')}\n"
    help_text += format_watermark()

    buttons = [
        [
            InlineKeyboardButton(f"✏️ {to_smallcaps('renamer')}", callback_data="help_renamer"),
            InlineKeyboardButton(f"🗜️ {to_smallcaps('compressor')}", callback_data="help_compressor")
        ],
        [
            InlineKeyboardButton(f"⚡ {to_smallcaps('12mb/s stream')}", callback_data="help_streamer"),
            InlineKeyboardButton(f"📝 {to_smallcaps('captions')}", callback_data="help_caption")
        ],
        [
            InlineKeyboardButton(f"🤝 {to_smallcaps('auto accept')}", callback_data="help_accept"),
            InlineKeyboardButton(f"🖼️ {to_smallcaps('thumbnail')}", callback_data="help_thumbnail")
        ],
        [
            InlineKeyboardButton(f"⏱️ {to_smallcaps('auto-delete')}", callback_data="help_autodelete"),
            InlineKeyboardButton(f"🎛️ {to_smallcaps('file pro')}", callback_data="help_filepro")
        ],
        [
            InlineKeyboardButton(f"🔑 {to_smallcaps('session')}", callback_data="help_session"),
            InlineKeyboardButton(f"🛠️ {to_smallcaps('tools & cleaner')}", callback_data="help_tools")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(f"👑 {to_smallcaps('admin control')}", callback_data="help_admin")])
    buttons.append([InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")])

    if is_edit:
        await target_msg.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await target_msg.reply_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


async def render_settings_menu(target_msg: Message, user, is_edit: bool = True):
    u = await user_repo.get_or_create(user.id, user.first_name, user.username)
    has_thumb = "✅" if u.get("thumb_id") else "🌐 ᴛʜᴀᴍ_ᴜʀʟ"
    has_caption = "✅" if (u.get("custom_caption") or u.get("captions_list")) else "📄 ᴀᴜᴛᴏ"
    timer = u.get("auto_delete_time", 0)
    timer_str = f"{timer}s" if timer > 0 else to_smallcaps("disabled")
    prefix_str = u.get("prefix") or to_smallcaps("none")
    suffix_str = u.get("suffix") or to_smallcaps("none")
    auto_ren = "🟢 ᴏɴ" if u.get("auto_rename") else "⚪ ᴏғғ"
    auto_comp = "🟢 ᴏɴ" if u.get("auto_compress") else "⚪ ᴏғғ"
    up_mode = "🎬 ᴠɪᴅᴇᴏ" if u.get("upload_mode", "video") == "video" else "📁 ᴅᴏᴄ"

    settings_text = (
        f"✦ **{to_smallcaps('smart settings & auto dashboard')}** ✦\n\n"
        f"👤 **{to_smallcaps('user')}** : {user.mention} (`{user.id}`)\n\n"
        f"• 🤖 **{to_smallcaps('auto rename')}** : `{auto_ren}`\n"
        f"• 🗜️ **{to_smallcaps('auto compress')}** : `{auto_comp}`\n"
        f"• 📤 **{to_smallcaps('upload mode')}** : `{up_mode}`\n"
        f"• 🖼️ **{to_smallcaps('custom thumbnail')}** : `{has_thumb}`\n"
        f"• 📝 **{to_smallcaps('custom caption')}** : `{has_caption}`\n"
        f"• 🏷️ **{to_smallcaps('file prefix')}** : `{prefix_str}`\n"
        f"• 🏷️ **{to_smallcaps('file suffix')}** : `{suffix_str}`\n"
        f"• ⏱️ **{to_smallcaps('auto-delete timer')}** : `{timer_str}`\n\n"
        f"💡 **{to_smallcaps('click any button below to toggle or configure:')}**"
        f"{format_watermark()}"
    )
    buttons = [
        [
            InlineKeyboardButton(f"🤖 {to_smallcaps('auto rename')}: {auto_ren}", callback_data="settings_toggle_autoren"),
            InlineKeyboardButton(f"🗜️ {to_smallcaps('auto compress')}: {auto_comp}", callback_data="settings_toggle_autocomp")
        ],
        [
            InlineKeyboardButton(f"📤 {to_smallcaps('mode')}: {up_mode}", callback_data="settings_toggle_upmode"),
            InlineKeyboardButton(f"⏱️ {to_smallcaps('timer settings')}", callback_data="open_timer_menu")
        ],
        [
            InlineKeyboardButton(f"🖼️ {to_smallcaps('view thumb')}", callback_data="settings_view_thumb"),
            InlineKeyboardButton(f"📝 {to_smallcaps('view caption')}", callback_data="settings_view_caption")
        ],
        [
            InlineKeyboardButton(f"🔄 {to_smallcaps('reset all')}", callback_data="settings_reset_all"),
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")
        ]
    ]
    if is_edit:
        await target_msg.edit_text(settings_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await target_msg.reply_text(settings_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^nav_(home|help|about|status|settings)"))
async def navigation_callbacks(client: Client, query: CallbackQuery):
    action = query.matches[0].group(1)
    user = query.from_user
    is_admin = user.id in Config.ADMINS

    if action == "home":
        text = (
            f"✦ **{to_smallcaps('mmw all-in-one pro')}** ✦\n\n"
            f"👋 **{to_smallcaps('hello')} {user.mention}** !\n\n"
            f"🚀 **{to_smallcaps('welcome to your ultra-fast multi-purpose pro bot!')}**\n\n"
            f"💎 **{to_smallcaps('all auto & pro features')}** :\n"
            f"• ✏️ **{to_smallcaps('auto & pro renamer')}** : {to_smallcaps('rename with custom prefix, suffix & thumb')}\n"
            f"• 🗜️ **{to_smallcaps('auto & pro compressor')}** : {to_smallcaps('ffmpeg h.264 presets & target size')}\n"
            f"• ⚡ **{to_smallcaps('12 mb/s fast streamer')}** : {to_smallcaps('http 206 range + 4 external players only (playit, mx, vlc, s player)')}\n"
            f"• 📝 **{to_smallcaps('auto dynamic captions')}** : {to_smallcaps('full templating ({filename}, {filesize}, cap[])')}\n"
            f"• 🤝 **{to_smallcaps('auto accept joins')}** : {to_smallcaps('instantly accept channel & group requests')}\n"
            f"• 🖼️ **{to_smallcaps('smart thumbnails')}** : {to_smallcaps('custom photo + tham_url auto-fallback')}\n"
            f"• ⏱️ **{to_smallcaps('auto-delete timer')}** : {to_smallcaps('scheduled batch message sweeper')}\n"
            f"• 🎛️ **{to_smallcaps('file pro studio')}** : {to_smallcaps('mediainfo, extract/add audio & subs, trim')}\n"
            f"• 🔑 **{to_smallcaps('string session')}** : {to_smallcaps('in-memory pyrogram & telethon generator')}\n"
            f"• 👑 **{to_smallcaps('admin control')}** : {to_smallcaps('single db, fast cache, broadcast & stats')}\n\n"
            f"💡 **{to_smallcaps('quick start')}** : {to_smallcaps('send or forward any file or video to start!')}"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"📖 {to_smallcaps('help guide')}", callback_data="nav_help"),
                InlineKeyboardButton(f"⚙️ {to_smallcaps('settings & auto')}", callback_data="nav_settings")
            ],
            [
                InlineKeyboardButton(f"📊 {to_smallcaps('system status')}", callback_data="nav_status"),
                InlineKeyboardButton(f"ℹ️ {to_smallcaps('about bot')}", callback_data="nav_about")
            ]
        ]
        if is_admin:
            buttons.append([InlineKeyboardButton(f"👑 {to_smallcaps('admin control panel')}", callback_data="admin_panel_back")])
        buttons.append([
            InlineKeyboardButton(f"📢 {to_smallcaps('official channel')}", url=Config.WATERMARK_URL)
        ])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "help":
        await render_help_menu(query.message, user, is_admin, is_edit=True)

    elif action == "about":
        about_text = (
            f"✦ **{to_smallcaps('about mmw all-in-one pro')}** ✦\n\n"
            f"• 🤖 **{to_smallcaps('bot name')}** : `MMW All-In-One Pro`\n"
            f"• 💎 **{to_smallcaps('edition')}** : `v3.0.0 Unified Plugin Architecture`\n"
            f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s ByteStreamer (HTTP 206 Range)`\n"
            f"• 📱 **{to_smallcaps('external players')}** : `PLAYit, MX Player, VLC, S Player (4 Only)`\n"
            f"• 🍃 **{to_smallcaps('database')}** : `Single Unified MongoDB + O(1) Memory Cache`\n"
            f"• 🗜️ **{to_smallcaps('compressor')}** : `FFmpeg YUV420p Even-Dimension Engine`\n"
            f"• 💓 **{to_smallcaps('keep-alive')}** : `6 Concurrent Pingers (6s Cycle)`"
            f"{format_watermark()}"
        )
        buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")]]
        await query.message.edit_text(about_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "status":
        users_count = await user_repo.get_total_users()
        chats_count = await chat_repo.get_total_chats()
        files_count = await file_repo.get_total_files()
        status_text = (
            f"✦ **{to_smallcaps('system & bot status')}** ✦\n\n"
            f"• 👥 **{to_smallcaps('total users')}** : `{users_count}`\n"
            f"• 📢 **{to_smallcaps('total chats')}** : `{chats_count}`\n"
            f"• 📁 **{to_smallcaps('indexed files')}** : `{files_count}`\n"
            f"• ⚡ **{to_smallcaps('stream speed')}** : `12 MB/s Turbo`\n"
            f"• 📱 **{to_smallcaps('4 external players')}** : `PLAYit • MX • VLC • S Player`\n"
            f"• 🧠 **{to_smallcaps('caching')}** : `O(1) FastMemoryCache Active`\n"
            f"• 🚀 **{to_smallcaps('server status')}** : `Online & Ultra-Fast`"
            f"{format_watermark()}"
        )
        buttons = [
            [
                InlineKeyboardButton(f"🔄 {to_smallcaps('refresh')}", callback_data="nav_status"),
                InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")
            ]
        ]
        await query.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "settings":
        await render_settings_menu(query.message, user, is_edit=True)


@Client.on_callback_query(filters.regex(r"^help_(renamer|compressor|streamer|thumbnail|caption|autodelete|session|cleaner|admin|tools|filepro|accept)"))
async def help_subpages(client: Client, query: CallbackQuery):
    cat = query.matches[0].group(1)
    buttons = [
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to help')}", callback_data="nav_help"),
            InlineKeyboardButton(f"🏠 {to_smallcaps('home')}", callback_data="nav_home")
        ]
    ]

    text = ""
    if cat == "renamer":
        text = (
            f"✦ **{to_smallcaps('auto & pro renamer — guide')}** ✦\n\n"
            f"• ✏️ **{to_smallcaps('manual rename')}** :\n"
            f"  1. {to_smallcaps('send any file or video and click')} `[✏️ {to_smallcaps('rename')}]`.\n"
            f"  2. {to_smallcaps('or reply to a file with')} `/rename new_name.mp4`.\n\n"
            f"• 🤖 **{to_smallcaps('auto-rename mode')}** :\n"
            f"  • `/autorename` : {to_smallcaps('toggle automatic renaming on/off.')}\n"
            f"  • `/setprefix <text>` : {to_smallcaps('set prefix for all files.')}\n"
            f"  • `/setsuffix <text>` : {to_smallcaps('set suffix before extension.')}\n"
            f"  • `/delprefix` & `/delsuffix` : {to_smallcaps('remove saved prefix/suffix.')}"
            f"{format_watermark()}"
        )
    elif cat == "compressor":
        text = (
            f"✦ **{to_smallcaps('auto & pro compressor — guide')}** ✦\n\n"
            f"• 🗜️ **{to_smallcaps('manual compression')}** :\n"
            f"  • {to_smallcaps('send a video or reply with')} `/compress` {to_smallcaps('or')} `/compress 100MB`.\n"
            f"  • {to_smallcaps('choose 720p, 480p, 360p, 1080p, crf 24, crf 20, or target size.')}\n\n"
            f"• 🤖 **{to_smallcaps('auto-compress mode')}** :\n"
            f"  • `/autocompress` : {to_smallcaps('toggle automatic 720p hd superfast compression.')}"
            f"{format_watermark()}"
        )
    elif cat == "streamer":
        text = (
            f"✦ **{to_smallcaps('12 mb/s streamer & 4 players — guide')}** ✦\n\n"
            f"• ⚡ **{to_smallcaps('12 mb/s stream response')}** :\n"
            f"  • {to_smallcaps('every file gets an instant 12 mb/s http 206 range stream & download link.')}\n"
            f"  • {to_smallcaps('or reply to any file with')} `/stream`.\n\n"
            f"• 📱 **{to_smallcaps('4 external players supported only')}** :\n"
            f"  `1.` ▶️ **PLAYit**\n"
            f"  `2.` 🎬 **MX Player**\n"
            f"  `3.` 🔊 **VLC Player**\n"
            f"  `4.` 🚀 **S Player**\n\n"
            f"• 📥 `/getfile <id>` : {to_smallcaps('retrieve file in telegram.')}\n"
            f"• 🗑️ `/revoke <id>` : {to_smallcaps('disable stream link anytime.')}"
            f"{format_watermark()}"
        )
    elif cat == "accept":
        text = (
            f"✦ **{to_smallcaps('auto-accept join requests — guide')}** ✦\n\n"
            f"• 🤝 **{to_smallcaps('automatic join approval')}** :\n"
            f"  • {to_smallcaps('add the bot as admin to your channel or group with invite users permission.')}\n"
            f"  • {to_smallcaps('the bot automatically accepts all incoming join requests and sends a stylish welcome message!')}\n\n"
            f"• ⚙️ **{to_smallcaps('commands')}** :\n"
            f"  • `/accept` {to_smallcaps('or')} `/autoapprove` : {to_smallcaps('toggle auto-accept on/off.')}"
            f"{format_watermark()}"
        )
    elif cat == "thumbnail":
        text = (
            f"✦ **{to_smallcaps('smart thumbnail — guide')}** ✦\n\n"
            f"• 🖼️ **{to_smallcaps('commands')}** :\n"
            f"  • {to_smallcaps('send any photo or reply to a photo with')} `/setthumb`.\n"
            f"  • `/setthumb <url>` : {to_smallcaps('set direct image url fallback.')}\n"
            f"  • `/thumb` : {to_smallcaps('view active thumbnail.')}\n"
            f"  • `/delthumb` : {to_smallcaps('delete custom thumbnail.')}"
            f"{format_watermark()}"
        )
    elif cat == "caption":
        text = (
            f"✦ **{to_smallcaps('auto dynamic captions — guide')}** ✦\n\n"
            f"• 📝 **{to_smallcaps('commands')}** :\n"
            f"  • `/setcaption <template>` : {to_smallcaps('set custom caption template.')}\n"
            f"  • `/addcaption <template>` : {to_smallcaps('add to cap[] queue.')}\n"
            f"  • `/caption` : {to_smallcaps('view active caption & queue.')}\n"
            f"  • `/delcaption` : {to_smallcaps('reset to default.')}\n\n"
            f"• 🏷️ **{to_smallcaps('variables')}** : `{filename}`, `{filesize}`, `{duration}`, `{language}`, `{audio_track}`, `{ext}`"
            f"{format_watermark()}"
        )
    elif cat == "autodelete":
        text = (
            f"✦ **{to_smallcaps('auto-delete timer — guide')}** ✦\n\n"
            f"• ⏱️ `/autodelete` : {to_smallcaps('open interactive timer menu.')}\n"
            f"• ⏱️ `/autodelete <seconds>` : {to_smallcaps('set custom auto-delete delay.')}"
            f"{format_watermark()}"
        )
    elif cat == "session":
        text = (
            f"✦ **{to_smallcaps('string session generator — guide')}** ✦\n\n"
            f"• 🔑 `/session` : {to_smallcaps('interactive step-by-step pyrogram & telethon string session generator in telegram.')}"
            f"{format_watermark()}"
        )
    elif cat == "filepro":
        text = (
            f"✦ **{to_smallcaps('file pro studio — guide')}** ✦\n\n"
            f"• 📊 `/mediainfo` : {to_smallcaps('inspect full container, video, audio & subtitle streams.')}\n"
            f"• 🎵 `/extractaudio` : {to_smallcaps('extract all audio tracks separately.')}\n"
            f"• 💬 `/extractsub` : {to_smallcaps('extract all subtitle tracks (.srt/.ass).')}\n"
            f"• ➕🎵 `/addaudio` : {to_smallcaps('mux or replace audio track in video.')}\n"
            f"• ➕💬 `/addsub` : {to_smallcaps('soft-mux subtitle file into video.')}\n"
            f"• ✂️ `/trim` : {to_smallcaps('trim video segment by start & end time.')}"
            f"{format_watermark()}"
        )
    elif cat in ["tools", "cleaner"]:
        text = (
            f"✦ **{to_smallcaps('tools & service cleaner — guide')}** ✦\n\n"
            f"• 🆔 `/id` & `/info` : {to_smallcaps('user & chat id inspector.')}\n"
            f"• ⚡ `/ping` & `/speedtest` : {to_smallcaps('server latency & network check.')}\n"
            f"• 🔎 `/search <query>` : {to_smallcaps('search indexed stream files.')}\n"
            f"• 🧹 `/clean <count>` : {to_smallcaps('purge group messages & auto-delete service notices.')}\n"
            f"• ❌ `/cancel` : {to_smallcaps('cancel active tasks & prompts.')}"
            f"{format_watermark()}"
        )
    elif cat == "admin":
        text = (
            f"✦ **{to_smallcaps('admin control — guide')}** ✦\n\n"
            f"• 👑 `/admin` : {to_smallcaps('open admin control panel.')}\n"
            f"• 📊 `/stats` & `/dbstats` & `/cache` : {to_smallcaps('view live metrics.')}\n"
            f"• 📢 `/broadcast` : {to_smallcaps('broadcast message to all users.')}\n"
            f"• 🚫 `/ban <id>` & `/unban <id>` : {to_smallcaps('manage user access.')}\n"
            f"• 🔄 `/restart` : {to_smallcaps('reboot bot server.')}"
            f"{format_watermark()}"
        )

    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^settings_(view_thumb|view_caption|reset_all|toggle_autoren|toggle_autocomp|toggle_upmode)"))
async def settings_actions(client: Client, query: CallbackQuery):
    action = query.matches[0].group(1)
    user = query.from_user
    user_id = user.id
    buttons = [[InlineKeyboardButton(f"🔙 {to_smallcaps('back to settings')}", callback_data="nav_settings")]]

    u = await user_repo.get_or_create(user_id, user.first_name, user.username)

    if action == "toggle_autoren":
        new_val = not bool(u.get("auto_rename", False))
        await user_repo.update_user(user_id, {"auto_rename": new_val})
        await query.answer(to_smallcaps(f"auto rename {'enabled' if new_val else 'disabled'}!"))
        return await render_settings_menu(query.message, user, is_edit=True)

    elif action == "toggle_autocomp":
        new_val = not bool(u.get("auto_compress", False))
        await user_repo.update_user(user_id, {"auto_compress": new_val})
        await query.answer(to_smallcaps(f"auto compress {'enabled' if new_val else 'disabled'}!"))
        return await render_settings_menu(query.message, user, is_edit=True)

    elif action == "toggle_upmode":
        curr_mode = u.get("upload_mode", "video")
        new_mode = "document" if curr_mode == "video" else "video"
        await user_repo.update_user(user_id, {"upload_mode": new_mode})
        await query.answer(to_smallcaps(f"upload mode: {new_mode}!"))
        return await render_settings_menu(query.message, user, is_edit=True)

    elif action == "view_thumb":
        thumb_id = u.get("thumb_id")
        if thumb_id:
            await query.answer()
            await query.message.reply_photo(
                photo=thumb_id,
                caption=f"🖼️ **{to_smallcaps('your active custom thumbnail')}**{format_watermark()}"
            )
        else:
            tham_url = u.get("tham_url") or Config.THAM_URL
            await query.message.edit_text(
                f"ℹ️ **{to_smallcaps('no custom photo thumbnail set.')}**\n\n"
                f"• 🔗 **{to_smallcaps('automatic tham_url')}** : `{tham_url}`\n\n"
                f"💡 {to_smallcaps('send any photo or reply to a photo with')} `/setthumb`."
                f"{format_watermark()}",
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )

    elif action == "view_caption":
        c = u.get("custom_caption")
        cap_list = u.get("captions_list", [])
        text = f"✦ **{to_smallcaps('your caption settings')}** ✦\n\n"
        if c:
            text += f"• 📝 **{to_smallcaps('active caption')}** :\n`{c}`\n\n"
        else:
            text += f"• 📝 **{to_smallcaps('active caption')}** : `{to_smallcaps('default auto metadata template')}`\n\n"

        if cap_list:
            text += f"📚 **{to_smallcaps('saved dynamic captions (cap[])')}** :\n"
            for i, cap in enumerate(cap_list, 1):
                text += f"{i}. `{cap}`\n"
            text += "\n"

        text += f"💡 {to_smallcaps('use')} `/setcaption <template>` {to_smallcaps('to update.')}"
        text += format_watermark()
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif action == "reset_all":
        await user_repo.update_user(user_id, {
            "thumb_id": None,
            "custom_caption": None,
            "captions_list": [],
            "prefix": "",
            "suffix": "",
            "auto_rename": False,
            "auto_compress": False,
            "upload_mode": "video",
            "auto_delete_time": 0
        })
        await query.answer(to_smallcaps("all settings reset!"), show_alert=True)
        await render_settings_menu(query.message, user, is_edit=True)
