import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, VERIFICATION_DAILY_LIMIT
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
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
            [KeyboardButton("🎬 Get Video"), KeyboardButton("🔥 Brazzers")],
            [KeyboardButton("📊 My Plan"), KeyboardButton("💎 Subscription")],
            [KeyboardButton("👥 Refer"), KeyboardButton("❓ Help")]
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
# 🎬 GET VIDEO DIRECT HANDLER (बिना अलग फाइल के)
# =================================================
@Client.on_message(filters.text & filters.private)
async def handle_menu_buttons(client, message: Message):
    text = message.text
    
    if text in ["🎬 Get Video", "Get Video"]:
        # सीधा यहाँ हैंडल करें
        await direct_get_video(client, message)
    
    elif text in ["🔥 Brazzers", "Brazzers"]:
        from plugins.brazzers import handle_brazzers_request
        await handle_brazzers_request(client, message)
    
    elif text in ["📊 My Plan", "My plan"]:
        await myplan_handler(client, message)
    
    elif text in ["💎 Subscription", "Subscription", "buy"]:
        await buy_handler(client, message)
    
    elif text in ["👥 Refer", "refer", "invite"]:
        await invite_command_handler(client, message)
    
    elif text in ["❓ Help", "help"]:
        await legal_hepl(client, message)


# =================================================
# 🎬 DIRECT GET VIDEO FUNCTION (पूरा फंक्शन यहीं)
# =================================================
async def direct_get_video(client, m: Message):
    from plugins.ban_manager import ban_manager
    from utils import auto_delete_message
    
    if not m.from_user:
        return

    if FSUB and not await is_user_joined(client, m):
        return

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"

    if await ban_manager.check_ban(client, m):
        return

    is_premium = await db.has_premium_access(user_id)
    used = await db.get_video_count(user_id) or 0

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
            return await m.reply(
                f"𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖯𝗋𝖾𝗆𝗂𝗎𝗆 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {PREMIUM_DAILY_LIMIT} 𝖥𝗂𝗅𝖾𝗌.\n𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐!"
            )
    else:
        if used >= VERIFICATION_DAILY_LIMIT:
            return await m.reply(limit_reached_msg, reply_markup=buy_button)
        if used >= DAILY_LIMIT:
            from plugins.verification import av_x_verification
            if IS_VERIFY:
                verified = await av_x_verification(client, m)
                if not verified:
                    return 
            else:
                return await m.reply(limit_reached_msg, reply_markup=buy_button)

    video_id = await db.get_unseen_video(user_id)

    if not video_id:
        try:
            video_id = await db.get_random_video()
        except Exception as e:
            print(f"[Random Video Error] {e}")
            return

    if not video_id:
        return await m.reply("❌ No videos found in the database.")

    try:
        bot_username = temp.U_NAME
        download_link = f"https://t.me/{bot_username}?start=avx-{video_id}"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Video", url=download_link)],
            [InlineKeyboardButton("🎬 Next Video", callback_data="get_another")]
        ])
        
        from info import PROTECT_CONTENT
        sent = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"🎬 **Your Video is Ready!**\n\n"
                f"📥 **Click below to download**\n\n"
                f"⚠️ Auto-deletes in 10 minutes\n\n"
                f"Powered by: {temp.B_LINK}"
            ),
            reply_markup=reply_markup,
            reply_to_message_id=m.id
        )

        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        await m.reply(f"❌ Failed to send video: {str(e)}")


# =================================================
# 📊 MY PLAN HANDLER
# =================================================
async def myplan_handler(client, message):
    user_id = message.from_user.id
    username = message.from_user.first_name

    used = await db.get_video_count(user_id)
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)

    if is_premium:
        daily_limit = PREMIUM_DAILY_LIMIT
        subscription_type = "💎 Premium"
    elif is_verified:
        daily_limit = VERIFICATION_DAILY_LIMIT
        subscription_type = "✅ Verified"
    else:
        daily_limit = DAILY_LIMIT
        subscription_type = "🆓 Free"

    remaining = max(daily_limit - used, 0)
    premium_details = await db.get_user(user_id) if is_premium else None

    text = f"""📊 **YOUR PLAN DETAILS**

👤 **User:** {username}
🆔 **ID:** `{user_id}`
💠 **Plan:** {subscription_type}
📁 **Daily Limit:** {daily_limit} Files
📤 **Used Today:** {used}
🟢 **Remaining:** {remaining}"""

    if is_premium and premium_details and premium_details.get('expiry_time'):
        expiry = premium_details['expiry_time']
        import pytz
        if expiry.tzinfo is None:
            expiry = pytz.utc.localize(expiry)
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
        text += f"""

💎 **Premium Info:**
📅 Expires: {expiry_ist.strftime('%d-%m-%Y')}
⏰ Time: {expiry_ist.strftime('%I:%M %p')}"""

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await message.reply(text, reply_markup=buttons)


# =================================================
# 💎 BUY PREMIUM HANDLER
# =================================================
async def buy_handler(client, message):
    user_id = message.from_user.id
    
    if await db.has_premium_access(user_id):
        await message.reply("✅ **You are already a Premium user!**")
        return
    
    text = f"""💎 **PREMIUM PLANS** 💎

╭─────────────────╮
│  📅 1 Month     │  ₹50
│  📅 3 Months    │  ₹120
│  📅 6 Months    │  ₹200
│  📅 1 Year      │  ₹350
╰─────────────────╯

✨ **Benefits:**
• 🔥 Unlimited Brazzers
• 📁 Higher daily limit
• 🚀 Priority access

💳 **UPI ID:** `{UPI_ID}`

📸 **How to Buy:**
1. Send payment to above UPI
2. Send screenshot here
3. Admin will activate"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Send Screenshot", callback_data="send_screenshot")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    if QR_CODE_IMAGE:
        await message.reply_photo(photo=QR_CODE_IMAGE, caption=text, reply_markup=buttons)
    else:
        await message.reply(text, reply_markup=buttons)


# =================================================
# 👥 REFER COMMAND HANDLER
# =================================================
@Client.on_message(filters.command(["invite", "refer"]))
async def invite_command_handler(client, message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{temp.U_NAME}?start=reff_{user_id}"
    share_link = f"https://telegram.me/share/url?url={ref_link}&text=Join%20Now!"
    
    points = await db.get_refer_points(user_id) or 0
    
    text = f"""👥 **REFER & EARN** 👥

🔗 **Your Link:** `{ref_link}`

📊 **Your Points:** `{points}/10`

━━━━━━━━━━━━━━━━
🎁 **Rewards:**
• 10 points = 1 Hour Premium!
━━━━━━━━━━━━━━━━

Share with friends and earn FREE Premium!"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link", url=share_link)],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await message.reply(text, reply_markup=buttons, disable_web_page_preview=True)


# =================================================
# 📜 LEGAL HANDLERS
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
# 🔙 CALLBACK QUERY HANDLER
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "close_data":
        await query.message.delete()
        await query.answer()

    elif data == "buy_premium":
        await query.message.delete()
        await buy_handler(client, query.message)
        await query.answer()

    elif data == "send_screenshot":
        await query.answer("Please send your payment screenshot as a photo", show_alert=True)

    elif data == "get_another":
        await query.message.delete()
        await direct_get_video(client, query.message)
        await query.answer("Fetching next video...")

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer()

    else:
        await query.answer("⚙️ Processing...")