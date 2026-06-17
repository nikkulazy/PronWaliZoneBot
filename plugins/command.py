import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start
from plugins.get_video import handle_video_request  # ✅ Import
from plugins.brazzers import handle_brazzers_request  # ✅ Import
from plugins.premium import approve_payment, reject_payment, payment_screenshot_handler

# =================================================
# 🚀 START COMMAND - WITH INLINE BUTTONS
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention
    
    if FSUB and not await is_user_joined(client, message):
        return
        
    argument = message.command[1] if len(message.command) > 1 else None

    if argument and argument.startswith('avbotz'):
        await verify_user_on_start(client, message)
        return

    if argument == "terms":
        await send_legal_text(client, message, script.TERMS_TXT)
        return
    elif argument == "disclaimer":
        await send_legal_text(client, message, script.DISCLAIMER_TXT)
        return
    elif argument == "help":
        await send_legal_text(client, message, script.HELP_TXT)
        return
    elif argument == "about":
        await send_about_text(client, message)
        return

    if argument and argument.startswith("reff_"):
        try:
            await refer_on_start(client, message)
            return 
        except Exception as e:
            print(f"Referral Error: {e}")

    if argument and argument.startswith("avx-"):
        search_id = argument.replace("avx-", "")
        await send_requested_file(client, message, user_id, search_id)
        return

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        try:
            await client.send_message(
                LOG_CHANNEL,
                script.LOG_TEXT.format(me2, user_id, mention)
            )
        except Exception:
            pass

    # ✅ INLINE BUTTONS
    inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("💢 Get Video 💢", callback_data="get_video")],
    [
        InlineKeyboardButton("🔞 Brazzers 🔞", callback_data="brazzers"),
        InlineKeyboardButton("✨ Subscription ✨", callback_data="subscription")
    ]
])

    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,
        has_spoiler=True
    )


# =================================================
# 📜 HELPER HANDLERS
# =================================================

@Client.on_message(filters.command("disclaimer") & filters.private)
async def legal_disclaimer(client, message: Message):
    await send_legal_text(client, message, script.DISCLAIMER_TXT)

@Client.on_message(filters.command("terms") & filters.private)
async def legal_terms(client, message: Message):
    await send_legal_text(client, message, script.TERMS_TXT)

@Client.on_message(filters.command("about") & filters.private)
async def legal_about(client, message: Message):
    await send_about_text(client, message)

@Client.on_message(filters.command("help") & filters.private)
async def legal_help(client, message: Message):
    await send_legal_text(client, message, script.HELP_TXT)
    
async def send_legal_text(client, message, text):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )

async def send_about_text(client, message):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )


# =========================================================
# 🔙 CALLBACK QUERY HANDLER
# =========================================================
"""@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    message = query.message

    if data == "close_data":
        await query.message.delete()
        await query.answer()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    # ✅ GET VIDEO BUTTON
    elif data == "get_video":
        await query.answer("📹 Getting your video...", show_alert=False)
        await handle_video_request(client, message)

    # ✅ BRAZZERS BUTTON
    elif data == "brazzers":
        await query.answer("🔞 Getting Brazzers video...", show_alert=False)
        await handle_brazzers_request(client, message)

    # ✅ SUBSCRIPTION BUTTON
    elif data == "subscription":
        await query.answer("✨ Opening subscription...", show_alert=False)
        from plugins.premium import buy_handler
        await buy_handler(client, message)

# =========================================================
# 🔙 CALLBACK QUERY HANDLER
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # 🔥🔥🔥 YEH ADD KAREIN - index wale callbacks ko ignore karein
    if data.startswith("index"):
        # index.py handle karega
        return

    if data == "close_data":
        await query.message.delete()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )"""
# =========================================================
# 🔙 CALLBACK QUERY HANDLER - ONLY ONE
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # index.py ke callbacks ko ignore karein
    if data.startswith("index"):
        return

    if data == "close_data":
        await query.message.delete()
        await query.answer()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer()

    # ✅ GET VIDEO BUTTON - FIXED
    elif data == "get_video":
        await query.answer("📹 Getting your video...", show_alert=False)
        await handle_video_request(client, query.message)  # ✅ query.message use karein

    # ✅ BRAZZERS BUTTON - FIXED
    elif data == "brazzers":
        await query.answer("🔞 Getting Brazzers video...", show_alert=False)
        await handle_brazzers_request(client, query.message)  # ✅ query.message use karein

    # ✅ SUBSCRIPTION BUTTON
    elif data == "subscription":
        await query.answer("✨ Opening subscription...", show_alert=False)
        from plugins.premium import buy_handler
        await buy_handler(client, query.message)  # ✅ query.message use karein
