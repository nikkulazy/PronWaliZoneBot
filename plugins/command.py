import datetime
import asyncio
import random
import re
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

# =================================================
# STRONG SANITIZER – removes all surrogate characters
# =================================================
def sanitize_text(text):
    """Remove invalid surrogate characters and other problematic Unicode."""
    if not text:
        return ""
    # Remove surrogate characters explicitly
    text = re.sub(r'[\ud800-\udfff]', '', text)
    # Encode/ignore to remove any other non-encodable chars
    return text.encode('utf-8', 'ignore').decode('utf-8')

# =================================================
# START COMMAND
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

    # ---------- BUTTONS ----------
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💢 Get Video 💢", callback_data="get_video")],
        [InlineKeyboardButton("🔞 Brazzers", callback_data="get_brazzers"), 
         InlineKeyboardButton("✨ Subscription", callback_data="get_subscription")],
        [InlineKeyboardButton("📊 My Plan", callback_data="my_plan"), 
         InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("📝 Help", callback_data="help"), 
         InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])
    
    m = await message.reply_text("⏳")
    await asyncio.sleep(0.4)
    await m.delete()
    
    # ---------- SAFE CAPTION ----------
    caption = script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME)
    caption = sanitize_text(caption)   # <-- STRONG SANITIZATION
    
    # ---------- SEND PHOTO WITH FALLBACK ----------
    try:
        await message.reply_photo(
            photo=random.choice(START_PIC),
            caption=caption,
            reply_markup=buttons,
            parse_mode=enums.ParseMode.HTML
        )
    except UnicodeEncodeError:
        # अगर फिर भी एरर आता है तो बिना HTML के भेजें
        await message.reply_photo(
            photo=random.choice(START_PIC),
            caption=sanitize_text(caption),  # फिर से सैनिटाइज़
            reply_markup=buttons,
            parse_mode=enums.ParseMode.DISABLED
        )
    return


# =================================================
# HELPER HANDLERS (सभी में sanitize जोड़ा)
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
    text = sanitize_text(text)
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    try:
        await message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_buttons),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML
        )
    except UnicodeEncodeError:
        await message.reply_text(
            text=sanitize_text(text),
            reply_markup=InlineKeyboardMarkup(inline_buttons),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.DISABLED
        )

async def send_about_text(client, message):
    text = script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK)
    text = sanitize_text(text)
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    try:
        await message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_buttons),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML
        )
    except UnicodeEncodeError:
        await message.reply_text(
            text=sanitize_text(text),
            reply_markup=InlineKeyboardMarkup(inline_buttons),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.DISABLED
        )

# =========================================================
# CALLBACK QUERY HANDLER
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    message = query.message

    if data.startswith("index"):
        from plugins.index import index_files
        await index_files(client, query)
        return

    if data == "close_data":
        await query.message.delete()
        return

    if data == "get_video":
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.get_video import handle_video_request
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await handle_video_request(client, fake_msg)
        return

    if data == "get_brazzers":
        try:
            await query.answer("⏳ Processing...", show_alert=False)
            from plugins.brazzers import process_brazzers_request
            fake_msg = message
            fake_msg.from_user = query.from_user
            fake_msg.chat = message.chat
            await process_brazzers_request(client, fake_msg)
        except Exception as e:
            print(f"Brazzers callback error: {e}")
            await query.answer("❌ Error processing request", show_alert=True)
        return

    if data == "get_subscription":
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import buy_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await buy_handler(client, fake_msg)
        return

    if data == "my_plan":
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import myplan_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await myplan_handler(client, fake_msg)
        return

    if data == "refer":
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.refer import invite_command_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await invite_command_handler(client, fake_msg)
        return

    if data == "help":
        await query.answer("⏳ Loading...", show_alert=False)
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await send_legal_text(client, fake_msg, script.HELP_TXT)
        return

    if data == "about":
        await query.answer("⏳ Loading...", show_alert=False)
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await send_about_text(client, fake_msg)
        return

    if data == "get":
        await query.answer("⏳ Loading...", show_alert=False)
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        caption = sanitize_text(script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID))
        try:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        except UnicodeEncodeError:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=sanitize_text(caption),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.DISABLED
            )
        return
