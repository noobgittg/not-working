from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, PasswordHashInvalid
from config import Config
from plugins.core_utils import cache, to_smallcaps, format_watermark, logger

ACTIVE_SESS_CLIENTS = {}

@Client.on_message(filters.private & filters.command("session"))
async def session_generator_command(client: Client, message: Message):
    btn = [
        [
            InlineKeyboardButton(f"⚡ {to_smallcaps('pyrogram / pyrofork')}", callback_data="sess_pyro"),
            InlineKeyboardButton(f"🚀 {to_smallcaps('telethon')}", callback_data="sess_tele")
        ],
        [
            InlineKeyboardButton(f"🔙 {to_smallcaps('back to home')}", callback_data="nav_home")
        ]
    ]

    await message.reply_text(
        f"✦ **{to_smallcaps('string session generator')}** ✦\n\n"
        f"🔐 **{to_smallcaps('generate secure telegram sessions')}**\n\n"
        f"• ⚡ **{to_smallcaps('pyrogram / pyrofork')}** : {to_smallcaps('used for modern userbots & pyrogram v2 apps.')}\n"
        f"• 🚀 **{to_smallcaps('telethon')}** : {to_smallcaps('used for telethon-based userbots & scripts.')}\n\n"
        f"🛡️ **{to_smallcaps('security guarantee')}** :\n"
        f"• {to_smallcaps('100% in-memory generation (zero disk storage).')}\n"
        f"• {to_smallcaps('the session string is sent directly to your saved messages.')}\n\n"
        f"💡 **{to_smallcaps('select your target library below:')}**"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_callback_query(filters.regex(r"^sess_(pyro|tele)"))
async def session_lib_choice(client: Client, query: CallbackQuery):
    lib = query.matches[0].group(1)
    user_id = query.from_user.id
    lib_name = "Pyrogram / Pyrofork" if lib == "pyro" else "Telethon"

    await cache.set(f"sess_step_{user_id}", {"lib": lib, "step": "phone"}, ttl=600)

    buttons = [[InlineKeyboardButton(f"❌ {to_smallcaps('cancel')}", callback_data="cancel_op")]]
    await query.message.edit_text(
        f"✦ **{to_smallcaps(f'{lib_name} session generator')}** ✦\n\n"
        f"📱 **{to_smallcaps('step 1: send your phone number')}**\n\n"
        f"• {to_smallcaps('send your phone number in international format (including country code).')}\n"
        f"• **{to_smallcaps('example')}** : `+919876543210`\n\n"
        f"💡 {to_smallcaps('send')} `/cancel` {to_smallcaps('anytime to abort.')}"
        f"{format_watermark()}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_session_text_step(client: Client, message: Message):
    user_id = message.from_user.id
    state = await cache.get(f"sess_step_{user_id}")
    if not state:
        return

    step = state.get("step")
    lib = state.get("lib", "pyro")
    text = (message.text or "").strip()

    if step == "phone":
        phone = text.replace(" ", "")
        if not phone.startswith("+") or len(phone) < 8:
            return await message.reply_text(
                f"⚠️ **{to_smallcaps('invalid phone number format!')}**\n\n"
                f"• {to_smallcaps('please include country code, e.g.')} `+919876543210`"
                f"{format_watermark()}"
            )
        status = await message.reply_text(f"⏳ **{to_smallcaps('sending login otp code...')}**")
        try:
            temp_client = Client(
                name=f"sess_{user_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                in_memory=True
            )
            await temp_client.connect()
            sent_code = await temp_client.send_code(phone)
            ACTIVE_SESS_CLIENTS[user_id] = temp_client
            state["phone"] = phone
            state["phone_code_hash"] = sent_code.phone_code_hash
            state["step"] = "otp"
            await cache.set(f"sess_step_{user_id}", state, ttl=600)
            await status.edit_text(
                f"✦ **{to_smallcaps('step 2: enter otp code')}** ✦\n\n"
                f"📩 {to_smallcaps('an otp code has been sent to your telegram account.')}\n"
                f"• {to_smallcaps('send the code with spaces between digits (e.g.')} `1 2 3 4 5` {to_smallcaps(') so telegram does not block it!')}"
                f"{format_watermark()}"
            )
        except Exception as e:
            await cache.delete(f"sess_step_{user_id}")
            return await status.edit_text(f"❌ **{to_smallcaps('failed to send otp')}** : `{e}`{format_watermark()}")

    elif step == "otp":
        otp_code = text.replace(" ", "").replace("-", "")
        temp_client = ACTIVE_SESS_CLIENTS.get(user_id)
        if not temp_client:
            await cache.delete(f"sess_step_{user_id}")
            return await message.reply_text(f"❌ **{to_smallcaps('session expired! start again with')}** `/session`")

        try:
            await temp_client.sign_in(state["phone"], state["phone_code_hash"], otp_code)
            await finalize_session_export(temp_client, message, user_id, lib)
        except SessionPasswordNeeded:
            state["step"] = "2fa"
            await cache.set(f"sess_step_{user_id}", state, ttl=600)
            return await message.reply_text(
                f"🔐 **{to_smallcaps('step 3: two-step verification (2fa)')}** ✦\n\n"
                f"• {to_smallcaps('your account has 2fa enabled. please send your cloud password now:')}"
                f"{format_watermark()}"
            )
        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            return await message.reply_text(f"❌ **{to_smallcaps('invalid or expired otp code')}** : `{e}`")
        except Exception as e:
            await cleanup_sess_client(user_id)
            return await message.reply_text(f"❌ **{to_smallcaps('sign-in error')}** : `{e}`")

    elif step == "2fa":
        temp_client = ACTIVE_SESS_CLIENTS.get(user_id)
        if not temp_client:
            await cache.delete(f"sess_step_{user_id}")
            return await message.reply_text(f"❌ **{to_smallcaps('session expired! start again with')}** `/session`")
        try:
            await temp_client.check_password(password=text)
            await finalize_session_export(temp_client, message, user_id, lib)
        except PasswordHashInvalid:
            return await message.reply_text(f"❌ **{to_smallcaps('invalid 2fa password! please try again.')}**")
        except Exception as e:
            await cleanup_sess_client(user_id)
            return await message.reply_text(f"❌ **{to_smallcaps('2fa error')}** : `{e}`")

async def finalize_session_export(temp_client: Client, message: Message, user_id: int, lib: str):
    try:
        session_str = await temp_client.export_session_string()
        caption_txt = (
            f"✦ **{to_smallcaps('string session generated')}** ✦\n\n"
            f"🔐 **{to_smallcaps('library')}** : `{'Pyrogram / Pyrofork' if lib == 'pyro' else 'Telethon / Pyrogram'}`\n\n"
            f"`{session_str}`\n\n"
            f"⚠️ **{to_smallcaps('do not share this string with anyone!')}**"
            f"{format_watermark()}"
        )
        try:
            await temp_client.send_message("me", caption_txt)
        except Exception:
            pass
        await message.reply_text(caption_txt)
    finally:
        await cleanup_sess_client(user_id)

async def cleanup_sess_client(user_id: int):
    await cache.delete(f"sess_step_{user_id}")
    cli = ACTIVE_SESS_CLIENTS.pop(user_id, None)
    if cli:
        try:
            await cli.disconnect()
        except Exception:
            pass
