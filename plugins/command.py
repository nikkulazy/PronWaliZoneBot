import datetime
import asyncio
import os
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
# 🚀 START COMMAND (केवल Help इनलाइन बटन के साथ)
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

    # ✅ केवल Help बटन वाला इनलाइन कीबोर्ड
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    
    # ✅ रिप्लाई कीबोर्ड (पुराने बटन ज्यों के त्यों)
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Get Video"), KeyboardButton("Brazzers")],
            [KeyboardButton("My plan"), KeyboardButton("Subscription")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # फोटो के साथ इनलाइन Help बटन भेजें
    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,
        has_spoiler=True
    )
    
    # रिप्लाई कीबोर्ड (नीचे वाले बटन) अलग से भेजें
    await message.reply(
        "👇 आप नीचे दिए बटन का भी उपयोग कर सकते हैं:", 
        reply_markup=reply_keyboard
    )

# =================================================
# 📜 लीगल / हेल्प टेक्स्ट भेजने वाले फंक्शन
# =================================================
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

# =================================================
# 📞 कॉलबैक हैंडलर (केवल close_data और help)
# =================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "close_data":
        await query.message.delete()
    elif data == "help":
        await send_legal_text(client, query.message, script.HELP_TXT)
        await query.answer()
    # अगर कोई और पुराना callback (जैसे "get") है तो उसे हटा दें या इग्नोर करें

# =================================================
# ⌨️ रिप्लाई कीबोर्ड के बटन हैंडलर (नया जोड़ा गया)
# =================================================
@Client.on_message(filters.private & filters.text)
async def handle_reply_buttons(client, message: Message):
    text = message.text
    user_id = message.from_user.id
    
    if text == "Get Video":
        # यूजर को वीडियो कोड मांगने का विकल्प दें
        await message.reply("📁 कृपया वीडियो का कोड या नाम भेजें।\nउदाहरण: `/file avx-123`", parse_mode=enums.ParseMode.MARKDOWN)
    elif text == "Brazzers":
        await message.reply("🍑 Brazzers सेक्शन जल्द आ रहा है। अभी प्रतीक्षा करें।")
    elif text == "My plan":
        # डेटाबेस से यूजर की प्लान जानकारी लें
        user_data = await db.get_user(user_id)  # मान लिया कि db में get_user मेथड है
        if user_data and user_data.get("premium"):
            expiry = user_data.get("expiry", "अज्ञात")
            await message.reply(f"🌟 **आपका प्लान:** प्रीमियम\n📅 **समाप्ति:** {expiry}")
        else:
            daily_limit = DAILY_LIMIT
            await message.reply(f"📋 **आपका प्लान:** फ्री\n📊 **दैनिक सीमा:** {daily_limit} फाइल\n💎 प्रीमियम के लिए /subscription")
    elif text == "Subscription":
        buttons = [[InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]]
        if QR_CODE_IMAGE and os.path.isfile(QR_CODE_IMAGE):
            await message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
    else:
        # किसी अन्य टेक्स्ट को इग्नोर करें (जैसे सामान्य चैट)
        pass

# =================================================
# 📟 कमांड हैंडलर (disclaimer, terms, about, help)
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

# =================================================
# ⚠️ ध्यान दें: plugins.verification, plugins.send_file, plugins.refer
#    आपकी खुद की फाइलें हैं। उनमें कोई बदलाव नहीं किया गया है।
# =================================================
