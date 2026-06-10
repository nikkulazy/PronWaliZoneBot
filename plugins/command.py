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
from plugins.get_video import handle_video_request

# =================================================
# 🚀 START COMMAND
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention

@Client.on_callback_query(filters.regex("next_video"))
async def next_video_callback(client, query: CallbackQuery):
    # पुरानी वीडियो डिलीट नहीं होगी, नई नीचे आएगी
    await handle_video_request(client, query.message)
    await query.answer()    
    
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
            
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Get Video"), KeyboardButton("Brazzers")],
            [KeyboardButton("My plan"), KeyboardButton("Subscription")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=reply_keyboard,
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
async def legal_hepl(client, message: Message):
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
# 🔙 CALLBACK QUERY HANDLER (Only for close & get)
# =========================================================
@Client.on_callback_query(filters.regex(r"^(close_data|get)$"))
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    if data == "close_data":
        await query.message.delete()
    elif data == "get":
        buttons = [[InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]]
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

# =========================================================
# 🧭 NAVIGATION CALLBACK (Previous/Next)
# =========================================================
@Client.on_callback_query(filters.regex(r"^nav_"))
async def navigation_handler(client, query: CallbackQuery):
    video_id = query.data.split("_")[1]
    user_id = query.from_user.id
    
    # Get video data
    file_data = await db.videos.find_one({"file_id": video_id})
    if not file_data:
        return await query.answer("Video not found!", show_alert=True)
    
    # Get prev/next for this new video
    prev_video = await db.get_prev_video(video_id)
    next_video = await db.get_next_video(video_id)
    
    nav_buttons = []
    if prev_video:
        nav_buttons.append(InlineKeyboardButton("◀ Previous", callback_data=f"nav_{prev_video}"))
    if next_video:
        nav_buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"nav_{next_video}"))
    
    row1 = nav_buttons if nav_buttons else []
    row2 = [
        InlineKeyboardButton("📁 Category", callback_data="category"),
        InlineKeyboardButton("❓ Help", callback_data="help_me")
    ]
    row3 = [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    
    reply_markup = InlineKeyboardMarkup([row1, row2, row3] if row1 else [row2, row3])
    
    # Send new video (without deleting old one)
    await client.send_video(
        chat_id=query.message.chat.id,
        video=video_id,
        protect_content=True,  # as per your info.PROTECT_CONTENT
        caption=(
            f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
            "<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
            "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>"
        ),
        reply_markup=reply_markup
    )
    await query.answer()  # Acknowledge callback

# =========================================================
# 📁 CATEGORY BUTTON HANDLER
# =========================================================
@Client.on_callback_query(filters.regex("category"))
async def category_handler(client, query: CallbackQuery):
    # आप यहाँ अपनी category लिंक या मैसेज डाल सकते हैं
    await query.answer("Coming soon! 🚀", show_alert=True)
    # या कोई मैसेज भेजें:
    # await query.message.reply("यहाँ आपको categories दिखेंगी")

# =========================================================
# ❓ HELP BUTTON HANDLER
# =========================================================
@Client.on_callback_query(filters.regex("help_me"))
async def help_callback_handler(client, query: CallbackQuery):
    await send_legal_text(client, query.message, script.HELP_TXT)
    await query.answer()
