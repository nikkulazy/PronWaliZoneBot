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

# =================================================
# 🚀 START COMMAND (Auto-Delete 60 sec + Button)
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention
    
    # कमांड वाला मैसेज डिलीट करो
    try:
        await message.delete()
    except:
        pass
    
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
    
    # 🔥 फोटो के नीचे दिखने वाला इनलाइन बटन
    inline_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Get Video 🎬", callback_data="get_video")],
        [InlineKeyboardButton("📚 My Plan", callback_data="myplan"), InlineKeyboardButton("💎 Buy", callback_data="buy")]
    ])
    
    # मैसेज भेजो
    sent_msg = await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_buttons,  # 🔥 बटन यहाँ लगा
        has_spoiler=True
    )
    
    # 🔥 60 सेकंड बाद मैसेज डिलीट करो
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
    except:
        pass


# =================================================
# 🎬 GET VIDEO CALLBACK HANDLER
# =================================================
@Client.on_callback_query(filters.regex("get_video"))
async def get_video_callback(client, callback_query: CallbackQuery):
    await callback_query.answer("🔍 Searching videos...", show_alert=False)
    # यहाँ अपना get video वाला कोड लगाओ
    # उदाहरण:
    await callback_query.message.reply_text("🎬 Please send the movie name or /getvideo command")
    try:
        await callback_query.message.delete()
    except:
        pass


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
    sent_msg = await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )
    # 60 सेकंड बाद डिलीट
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
        await message.delete()
    except:
        pass

async def send_about_text(client, message):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    sent_msg = await message.reply_text(
        text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )
    # 60 सेकंड बाद डिलीट
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
        await message.delete()
    except:
        pass


# =========================================================
# 🔙 CALLBACK QUERY HANDLER (close, buy, myplan, get_video)
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "close_data":
        try:
            await query.message.delete()
        except:
            pass
    
    elif data == "get_video":
        await query.answer("🎬 Get Video feature coming soon!", show_alert=True)
        # यहाँ अपना get video वाला कोड लगाओ
    
    elif data == "myplan":
        await query.answer("📊 Checking your plan...", show_alert=False)
        # यहाँ अपना myplan वाला कोड लगाओ
        await query.message.reply_text("📊 Use /myplan command to check your plan")
    
    elif data == "buy":
        await query.answer("💎 Subscription details...", show_alert=False)
        buttons = [
            [InlineKeyboardButton('✖️ ᴄʟᴏsᴇ ✖️', callback_data='close_data')]
        ]
        if QR_CODE_IMAGE:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
    
    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        if QR_CODE_IMAGE:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
