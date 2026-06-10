import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, PROTECT_CONTENT, VERIFICATION_DAILY_LIMIT, IS_VERIFY
from utils import temp, is_user_joined, auto_delete_message
from plugins.verification import verify_user_on_start, av_x_verification
from plugins.verification import IS_VERIFY
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# =================================================
# 🚀 START COMMAND
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
# 🆕 NEXT VIDEO SEND KARNE WALA FUNCTION
# =========================================================
async def send_next_video_to_user(client, query):
    """Next video bhejta hai – same logic as /getvideo"""
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    # Loading message
    loading = await client.send_message(chat_id, "⏳ Next video la raha hun...")
    
    # Limit check
    is_premium = await db.has_premium_access(user_id)
    used = await db.get_video_count(user_id) or 0
    
    if is_premium and used >= PREMIUM_DAILY_LIMIT:
        await loading.edit("❌ Aapki aaj ki premium limit complete ho chuki hai.")
        return
    if not is_premium:
        if used >= VERIFICATION_DAILY_LIMIT:
            await loading.edit("❌ Daily limit poora. Kal try karein ya subscription lein.",
                               reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buy", callback_data="get")]]))
            return
        if used >= DAILY_LIMIT:
            if IS_VERIFY:
                # Verification ke liye fake message object banana hoga
                # Simple: query.message hi use karte hain (delete ho chuka hai, par uski jgh dummy)
                # Better: ek naya dummy message bana kar bhej do
                dummy = await client.send_message(chat_id, "Verification required...")
                verified = await av_x_verification(client, dummy)
                await dummy.delete()
                if not verified:
                    await loading.delete()
                    return
            else:
                await loading.edit("❌ Daily limit poora. Kal try karo.",
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buy", callback_data="get")]]))
                return
    
    # Next video ID
    video_id = await db.get_unseen_video(user_id)
    if not video_id:
        video_id = await db.get_random_video()
    if not video_id:
        await loading.edit("❌ Database mein koi video nahi hai.")
        return
    
    # Send video with Next button
    next_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⏩ Next Video", callback_data="next_video")]])
    try:
        sent = await client.send_video(
            chat_id=chat_id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                "<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>"
            ),
            reply_markup=next_btn
        )
        await db.increase_video_count(user_id, query.from_user.username or query.from_user.first_name)
        asyncio.create_task(auto_delete_message(None, sent))  # auto delete after 10 min (function ke hisaab se)
        await loading.delete()
    except Exception as e:
        await loading.edit(f"❌ Failed: {str(e)}")

# =========================================================
# 🔙 CALLBACK QUERY HANDLER (with next_video case)
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

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
        )
    
    # 🆕 NEXT BUTTON HANDLER
    elif data == "next_video":
        # Pehle wali video delete karo
        await query.message.delete()
        # Ab next video bhejo
        await send_next_video_to_user(client, query)