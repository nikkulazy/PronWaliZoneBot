import datetime
import asyncio
import random
import uuid
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
from plugins.get_video import DOWNLOAD_CACHE

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
    
    await asyncio.sleep(300)
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
# CALLBACK QUERY HANDLER - Main Handler
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    """Main callback handler"""
    
    data = query.data
    user_id = query.from_user.id
    message = query.message

    # =============================================
    # 🆕 BACK BUTTON HANDLER - Purane buttons wapas laane ke liye
    # =============================================
    if data.startswith("back_"):
        try:
            video_type = data.replace("back_", "")  # "video" ya "brazzers"
            is_brazzers = video_type == "brazzers"
            
            # User history se current video nikaalo
            history_data = temp.USER_VIDEO_HISTORY.get(user_id)
            if not history_data or not history_data["history"]:
                await query.answer("❌ No history found!", show_alert=True)
                return
            
            current_idx = history_data["current_index"]
            if current_idx < 0 or current_idx >= len(history_data["history"]):
                await query.answer("❌ Invalid video!", show_alert=True)
                return
            
            video_id = history_data["history"][current_idx]
            
            # Purane buttons rebuild karein
            buttons = []
            
            # Row 1: Previous + Next
            row1 = []
            if current_idx > 0:
                row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{video_type}"))
            else:
                row1.append(InlineKeyboardButton("⏪ Previous", callback_data="noop"))
            
            row1.append(InlineKeyboardButton("⏩ Next", callback_data=f"next_{video_type}"))
            buttons.append(row1)
            
            # Row 2: Download Button
            # Naya download ID generate karein
            download_id = str(uuid.uuid4())[:8]
            DOWNLOAD_CACHE[download_id] = {
                "file_id": video_id,
                "video_type": video_type,
                "user_id": user_id
            }
            
            row2 = [
                InlineKeyboardButton("📥 Download", callback_data=f"dld_{download_id}")
            ]
            buttons.append(row2)
            
            # Row 3: Close Button
            row3 = [
                InlineKeyboardButton("✖️ Close ✖️", callback_data="close_data")
            ]
            buttons.append(row3)
            
            original_buttons = InlineKeyboardMarkup(buttons)
            
            # ✅ Purane buttons wapas set karein
            await query.message.edit_reply_markup(
                reply_markup=original_buttons
            )
            
            await query.answer("🔙 Back to original buttons", show_alert=False)
            
        except Exception as e:
            print(f"❌ Back button error: {e}")
            await query.answer("❌ Error loading previous buttons", show_alert=True)
        return

    # =============================================
    # 🆕 DOWNLOAD HANDLER (dld_ - Short ID based)
    # =============================================
    if data.startswith("dld_"):
        from plugins.get_video import download_callback_handler
        await download_callback_handler(client, query)
        return

    # =============================================
    # 🆕 NEXT / PREVIOUS NAVIGATION
    # =============================================
    if data.startswith("next_") or data.startswith("prev_") or data == "noop":
        from plugins.get_video import video_navigation_callback
        await video_navigation_callback(client, query)
        return

    # =============================================
    # 🆕 DELETE HANDLER
    # =============================================
    if data.startswith("delete_"):
        from plugins.admin import delete_callback_handler
        await delete_callback_handler(client, query)
        return

    # =============================================
    # INDEX HANDLER
    # =============================================
    if data.startswith("index"):
        from plugins.index import index_files
        await index_files(client, query)
        return

    # =============================================
    # CLOSE BUTTON
    # =============================================
    if data == "close_data":
        await query.message.delete()
        return

    # =============================================
    # GET VIDEO
    # =============================================
    if data == "get_video":
    await query.answer("⏳ Loading...", show_alert=False)
    try:
        await message.delete()
    except Exception:
        pass
    
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
    try:
        await query.answer("⏳ Processing...", show_alert=False)
        try:
            await message.delete()
        except Exception:
            pass
        
        from plugins.brazzers import process_brazzers_request
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await process_brazzers_request(client, fake_msg)
    except Exception as e:
        print(f"Brazzers callback error: {e}")
        await query.answer("❌ Error processing request", show_alert=True)
    return

    # =============================================
    # SUBSCRIPTION
    # =============================================
    if data == "get_subscription":
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
        await approve_payment(client, query)
        return

    if data.startswith("reject_pay_"):
        await reject_payment(client, query)
        return

    # =============================================
    # MY PLAN FROM CALLBACK
    # =============================================
    if data == "my_plan_callback":
        await query.answer("⏳ Loading...", show_alert=False)
        from plugins.premium import myplan_handler
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        await myplan_handler(client, fake_msg)
        return
