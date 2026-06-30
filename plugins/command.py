import datetime
import asyncio
import random
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, PICS
from utils import temp, is_user_joined, get_shortlink
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start
from plugins.premium import approve_payment, reject_payment, payment_screenshot_handler

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

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💢 Get Video 💢", callback_data="get_video")],
        [InlineKeyboardButton("🔞 Brazzers", callback_data="get_brazzers"), 
         InlineKeyboardButton("✨ Subscription", callback_data="get_subscription")],
        [InlineKeyboardButton("📊 My Plan", callback_data="my_plan"), 
         InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("📝 Help", callback_data="help"), 
         InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    msg = await message.reply_photo(
        photo=random.choice(PICS),
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=buttons,
    )
    
    await asyncio.sleep(30)
    await msg.delete()  


# =================================================
# HELPER HANDLERS
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
# CALLBACK QUERY HANDLER - Main Handler (WITH DEBUGGING)
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    """Main callback handler with debugging for all callbacks"""
    
    # ---------- DEBUGGING LOGS ----------
    print(f"\n{'='*50}")
    print(f"🔔 CALLBACK RECEIVED")
    print(f"📌 Data: {query.data}")
    print(f"👤 User ID: {query.from_user.id}")
    print(f"👤 Username: {query.from_user.username}")
    print(f"{'='*50}\n")
    
    data = query.data
    user_id = query.from_user.id
    message = query.message

    # =============================================
    # 🆕 DOWNLOAD HANDLER (dld_ - Short ID based)
    # =============================================
    if data.startswith("dld_"):
        print("✅ Download handler triggered!")
        from plugins.get_video import download_callback_handler
        await download_callback_handler(client, query)
        return

    # =============================================
    # 🆕 NEXT / PREVIOUS NAVIGATION
    # =============================================
    if data.startswith("next_") or data.startswith("prev_") or data == "noop":
        print("✅ Navigation handler triggered!")
        from plugins.get_video import video_navigation_callback
        await video_navigation_callback(client, query)
        return

    # =============================================
    # 🆕 DELETE HANDLER
    # =============================================
    if data.startswith("delete_"):
        print("✅ Delete handler triggered!")
        from plugins.admin import delete_callback_handler
        await delete_callback_handler(client, query)
        return

    # =============================================
    # INDEX HANDLER
    # =============================================
    if data.startswith("index"):
        print("✅ Index handler triggered!")
        from plugins.index import index_files
        await index_files(client, query)
        return

    # =============================================
    # CLOSE BUTTON
    # =============================================
    if data == "close_data":
        print("✅ Close handler triggered!")
        await query.message.delete()
        return

    # =============================================
    # GET VIDEO
    # =============================================
    if data == "get_video":
        print("✅ Get Video handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.get_video import handle_video_request
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await handle_video_request(client, fake_msg)
        return

    # =============================================
    # GET BRAZZERS
    # =============================================
    if data == "get_brazzers":
        print("✅ Get Brazzers handler triggered!")
        try:
            await query.answer("⏳ Processing...", show_alert=False)
            from plugins.brazzers import process_brazzers_request
            fake_msg = message
            fake_msg.from_user = query.from_user
            fake_msg.chat = message.chat
            await process_brazzers_request(client, fake_msg)
        except Exception as e:
            print(f"❌ Brazzers callback error: {e}")
            await query.answer("❌ Error processing request", show_alert=True)
        return

    # =============================================
    # SUBSCRIPTION
    # =============================================
    if data == "get_subscription":
        print("✅ Subscription handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import buy_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await buy_handler(client, fake_msg)
        return

    # =============================================
    # MY PLAN
    # =============================================
    if data == "my_plan":
        print("✅ My Plan handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import myplan_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await myplan_handler(client, fake_msg)
        return

    # =============================================
    # REFER
    # =============================================
    if data == "refer":
        print("✅ Refer handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.refer import invite_command_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await invite_command_handler(client, fake_msg)
        return

    # =============================================
    # HELP
    # =============================================
    if data == "help":
        print("✅ Help handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await send_legal_text(client, fake_msg, script.HELP_TXT)
        return

    # =============================================
    # ABOUT
    # =============================================
    if data == "about":
        print("✅ About handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await send_about_text(client, fake_msg)
        return

    # =============================================
    # GET (Subscription Buy)
    # =============================================
    if data == "get":
        print("✅ Get (Subscription) handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        return

    # =============================================
    # PREMIUM APPROVE/REJECT
    # =============================================
    if data.startswith("add_prem_"):
        print("✅ Premium Approve handler triggered!")
        await approve_payment(client, query)
        return

    if data.startswith("reject_pay_"):
        print("✅ Premium Reject handler triggered!")
        await reject_payment(client, query)
        return

    # =============================================
    # MY PLAN FROM CALLBACK
    # =============================================
    if data == "my_plan_callback":
        print("✅ My Plan Callback handler triggered!")
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import myplan_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await myplan_handler(client, fake_msg)
        return

    # =============================================
    # UNKNOWN CALLBACK (Debug)
    # =============================================
    print(f"⚠️ UNKNOWN CALLBACK: {data}")
    await query.answer("⚠️ Unknown command!", show_alert=True)
