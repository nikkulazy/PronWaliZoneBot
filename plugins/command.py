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
    
    # =============================================
    # ✅ INLINE KEYBOARD (Reply Keyboard Hata Diya)
    # =============================================
    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📹 Get Video", callback_data="get_video"),
                InlineKeyboardButton("🔞 Brazzers", callback_data="brazzers")
            ],
            [
                InlineKeyboardButton("💎 My Plan", callback_data="my_plan"),
                InlineKeyboardButton("📊 Subscription", callback_data="subscription")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help"),
                InlineKeyboardButton("ℹ️ About", callback_data="about")
            ]
        ]
    )

    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,  # ✅ Inline Keyboard
        has_spoiler=True
    )


# =================================================
# 📜 HELPER HANDLERS (Command se chalein)
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
# 📝 HELPER FUNCTIONS
# =================================================

async def send_legal_text(client, message, text):
    """Send legal text with close button"""
    inline_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('❌ Close', callback_data='close_data')]
        ]
    )
    await message.reply_text(
        text=text,
        reply_markup=inline_buttons,
        disable_web_page_preview=True
    )

async def send_about_text(client, message):
    """Send About text with close button"""
    inline_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('❌ Close', callback_data='close_data')]
        ]
    )
    await message.reply_text(
        text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
        reply_markup=inline_buttons,
        disable_web_page_preview=True
    )


# =================================================
# 🎯 MAIN CALLBACK QUERY HANDLER (Inline Buttons Ke Liye)
# =================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    # ✅ HAR CALLBACK KE LIYE YE LINE ZAROORI HAI
    await query.answer()
    
    # =============================================
    # 1️⃣ CLOSE BUTTON
    # =============================================
    if data == "close_data":
        await query.message.delete()
    
    # =============================================
    # 2️⃣ GET VIDEO BUTTON
    # =============================================
    elif data == "get_video":
        await query.message.reply(
            "📹 **Video Search Mode**\n\n"
            "Please send me the video name or ID you're looking for.\n"
            "Example: `/search Avengers`",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ]
            )
        )
    
    # =============================================
    # 3️⃣ BRAZZERS BUTTON
    # =============================================
    elif data == "brazzers":
        await query.message.reply(
            "🔞 **Brazzers Content**\n\n"
            "Use `/brazzers` command to search Brazzers videos.\n"
            "Example: `/brazzers hot scene`",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ]
            )
        )
    
    # =============================================
    # 4️⃣ MY PLAN BUTTON
    # =============================================
    elif data == "my_plan":
        user = await db.get_user(user_id)
        if user:
            plan = user.get("plan", "Free")
            expiry = user.get("expiry", "N/A")
            used = user.get("used_today", 0)
            limit = PREMIUM_DAILY_LIMIT if plan == "Premium" else DAILY_LIMIT
            
            await query.message.reply(
                f"💎 **Your Plan Details**\n\n"
                f"📌 **Plan:** {plan}\n"
                f"📅 **Expiry:** {expiry}\n"
                f"📊 **Today's Usage:** {used}/{limit}\n"
                f"🔑 **Status:** {'✅ Active' if plan == 'Premium' else '🆓 Free'}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                    ]
                )
            )
        else:
            await query.message.reply(
                "❌ User not found!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                    ]
                )
            )
    
    # =============================================
    # 5️⃣ SUBSCRIPTION BUTTON
    # =============================================
    elif data == "subscription":
        subscription_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("💰 Buy Premium", callback_data="buy_premium"),
                    InlineKeyboardButton("💳 UPI Pay", callback_data="upi_pay")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
                ]
            ]
        )
        await query.message.reply(
            "📊 **Subscription Plans**\n\n"
            "🔹 **Free Plan:** 1 request/day\n"
            "🔹 **Premium Plan:** Unlimited requests\n"
            "💰 **Price:** ₹99/month\n"
            "✅ **Benefits:**\n"
            "  • Unlimited video requests\n"
            "  • Priority support\n"
            "  • No ads",
            reply_markup=subscription_keyboard
        )
    
    # =============================================
    # 6️⃣ BUY PREMIUM BUTTON
    # =============================================
    elif data == "buy_premium":
        await query.message.reply(
            f"💳 **Payment Instructions**\n\n"
            f"📌 **UPI ID:** `{UPI_ID}`\n\n"
            "🔹 **Steps to Pay:**\n"
            "1. Send ₹99 via UPI\n"
            "2. Send transaction screenshot\n"
            "3. Premium will be activated within 5 mins\n\n"
            "📸 **Screenshot:** After payment, send screenshot here.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Back", callback_data="subscription")]
                ]
            )
        )
    
    # =============================================
    # 7️⃣ UPI PAY BUTTON
    # =============================================
    elif data == "upi_pay":
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=f"💳 **Scan QR to Pay**\n\n"
                    f"📌 **UPI ID:** `{UPI_ID}`\n"
                    f"💰 **Amount:** ₹99\n\n"
                    "After payment, send screenshot to admin.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Back", callback_data="subscription")]
                ]
            )
        )
    
    # =============================================
    # 8️⃣ HELP BUTTON
    # =============================================
    elif data == "help":
        await send_legal_text(client, query.message, script.HELP_TXT)
    
    # =============================================
    # 9️⃣ ABOUT BUTTON
    # =============================================
    elif data == "about":
        await send_about_text(client, query.message)
    
    # =============================================
    # 🔟 BACK TO START BUTTON
    # =============================================
    elif data == "back_to_start":
        # ✅ Wapas main menu
        await start_command(client, query.message)
    
    # =============================================
    # 1️⃣1️⃣ CLOSE WITH ALERT (Demo)
    # =============================================
    elif data == "close_with_alert":
        await query.answer("This will close!", show_alert=True)
        await query.message.delete()
    
    # =============================================
    # 1️⃣2️⃣ OLD DATA HANDLER (Agar pehle se kuch tha)
    # =============================================
    elif data == "get":
        # Ye aapka purana get button handler
        buttons = [
            [InlineKeyboardButton('❌ Close', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
    
    # =============================================
    # 1️⃣3️⃣ DEFAULT/UNKNOWN DATA
    # =============================================
    else:
        await query.answer("Invalid option!", show_alert=True)
