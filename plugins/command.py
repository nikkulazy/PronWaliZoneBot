import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, VERIFICATION_DAILY_LIMIT, PROTECT_CONTENT, IS_VERIFY
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start, av_x_verification
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start
from plugins.ban_manager import ban_manager

# =================================================
# 🚀 START COMMAND (दोनों बटन के साथ)
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
    
    # 🔥 पुराना रिप्लाई कीबोर्ड (नीचे टाइपिंग एरिया के ऊपर)
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("💢 Get Video 💢")],
            [KeyboardButton("My plan"), KeyboardButton("Subscription")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    # 🔥 नया इनलाइन बटन (फोटो के नीचे क्लिक करने वाले)
    inline_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Get Video 🎬", callback_data="get_video")],
        [InlineKeyboardButton("📚 My Plan", callback_data="myplan"), InlineKeyboardButton("💎 Buy", callback_data="buy")]
    ])
    
    # फोटो के साथ इनलाइन बटन भेजो
    sent_msg = await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_buttons,  # 🔥 इनलाइन बटन
        has_spoiler=True
    )
    
    # रिप्लाई कीबोर्ड के साथ टेक्स्ट मैसेज भेजो
    await message.reply_text(
        "📱 **Use the buttons below to navigate:**",
        reply_markup=reply_keyboard  # 🔥 रिप्लाई कीबोर्ड
    )
    
    # 🔥 60 सेकंड बाद फोटो वाला मैसेज डिलीट करो
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
    except:
        pass


# =================================================
# 🎬 GET VIDEO FUNCTION (Command और Button दोनों के लिए)
# =================================================
async def send_video_to_user(client, m):
    """Function to send video to user (used by both command and button)"""
    
    # Safety check
    if not m.from_user:
        return False

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"

    # Ban check
    if await ban_manager.check_ban(client, m):
        return False

    # Premium + limit info
    is_premium = await db.has_premium_access(user_id)
    used = await db.get_video_count(user_id) or 0

    # Limit reached message
    limit_reached_msg = (
        f"𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖣𝖺𝗂𝗅𝗒 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {used} 𝖥𝗂𝗅𝖾𝗌.\n\n"
        "𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐!\n"
        "𝖮𝗋 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 𝖳𝗈 𝖡𝗈𝗈𝗌𝗍 𝖸𝗈𝗎𝗋 𝖣𝖺𝗂𝗅𝗒 𝖫𝗂𝗆𝗂𝗍"
    )
    buy_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •", callback_data="get")]
    ])

    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            await m.reply(
                f"𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖯𝗋𝖾𝗆𝗂𝗎𝗆 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {PREMIUM_DAILY_LIMIT} 𝖥𝗂𝗅𝖾𝗌.\n"
                f"𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐!"
            )
            return False
    else:
        if used >= VERIFICATION_DAILY_LIMIT:
            await m.reply(limit_reached_msg, reply_markup=buy_button)
            return False
        if used >= DAILY_LIMIT:
            if IS_VERIFY:
                verified = await av_x_verification(client, m)
                if not verified:
                    return False
            else:
                await m.reply(limit_reached_msg, reply_markup=buy_button)
                return False

    # Get video from database
    video_id = await db.get_unseen_video(user_id)

    if not video_id:
        try:
            video_id = await db.get_random_video()
        except Exception as e:
            print(f"[Random Video Error] {e}")
            return False

    if not video_id:
        await m.reply("❌ No videos found in the database.")
        return False

    # Send video
    try:
        sent = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                "<blockquote>"
                "ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ "
                "ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ."
                "</blockquote>"
            )
        )

        # Increase daily count
        await db.increase_video_count(user_id, username)

        # Auto delete in background (10 minutes = 600 seconds)
        asyncio.create_task(auto_delete_video(m, sent))
        return True

    except Exception as e:
        await m.reply(f"❌ Failed to send video: {str(e)}")
        return False


async def auto_delete_video(command_msg, video_msg):
    """Auto delete video after 10 minutes"""
    await asyncio.sleep(600)  # 10 minutes
    try:
        await video_msg.delete()
        await command_msg.delete()
    except:
        pass


# =================================================
# 📜 GET VIDEO COMMAND HANDLER
# =================================================
@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):
    # Force subscribe check
    if FSUB and not await is_user_joined(client, m):
        return
    await send_video_to_user(client, m)


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
    await asyncio.sleep(60)
    try:
        await sent_msg.delete()
        await message.delete()
    except:
        pass


# =========================================================
# 🔙 CALLBACK QUERY HANDLER (सभी इनलाइन बटन के लिए)
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
        await query.answer("🔍 Getting video...", show_alert=False)
        
        # Fake message for send_video_to_user function
        class FakeMessage:
            def __init__(self, user_id, chat_id, from_user):
                self.chat = type('obj', (object,), {'id': chat_id})()
                self.from_user = from_user
                self.id = user_id
            
            async def reply(self, text, reply_markup=None):
                return await query.message.reply_text(text, reply_markup=reply_markup)
        
        fake_user = type('obj', (object,), {
            'id': user_id,
            'username': query.from_user.username,
            'first_name': query.from_user.first_name
        })()
        
        fake_msg = FakeMessage(user_id, query.message.chat.id, fake_user)
        
        # Send video
        await send_video_to_user(client, fake_msg)
        
        # Delete original message
        try:
            await query.message.delete()
        except:
            pass
    
    elif data == "myplan":
        await query.answer("📊 Checking your plan...", show_alert=False)
        sent_msg = await query.message.reply_text(
            "📊 **Your Subscription Plan**\n\nUse `/myplan` command to check complete details",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Close", callback_data="close_data")]
            ])
        )
        await asyncio.sleep(60)
        try:
            await sent_msg.delete()
        except:
            pass
    
    elif data == "buy":
        await query.answer("💎 Subscription details...", show_alert=False)
        buttons = [
            [InlineKeyboardButton('✖️ ᴄʟᴏsᴇ ✖️', callback_data='close_data')]
        ]
        if QR_CODE_IMAGE:
            sent_msg = await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            sent_msg = await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        
        # 60 सेकंड बाद डिलीट
        await asyncio.sleep(60)
        try:
            await sent_msg.delete()
        except:
            pass
    
    elif data == "get":
        buttons = [
            [InlineKeyboardButton('✖️ ᴄʟᴏsᴇ ✖️', callback_data='close_data')]
        ]
        if QR_CODE_IMAGE:
            sent_msg = await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            sent_msg = await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        await asyncio.sleep(60)
        try:
            await sent_msg.delete()
        except:
            pass
