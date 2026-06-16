import datetime
import asyncio
import pytz
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, ADMINS
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

    # ✅ INLINE BUTTONS
    inline_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 Get Video", callback_data="get_video")],
        [InlineKeyboardButton("🔞 Brazzers", callback_data="brazzers")],
        [InlineKeyboardButton("📋 My Plan", callback_data="my_plan")],
        [InlineKeyboardButton("💰 Subscription", callback_data="subscription")]
    ])

    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_buttons,
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


# =================================================
# 🔙 MAIN CALLBACK HANDLER - SAB BUTTONS KE LIYE
# =================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    admin_id = query.from_user.id
    
    # ✅ Answer callback
    await query.answer()
    
    # ============ CLOSE BUTTON ============
    if data == "close_data":
        try:
            await query.message.delete()
        except Exception:
            pass
        return
    
    # ============ GET / SUBSCRIPTION BUTTON ============
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
    
    # ============ GET VIDEO BUTTON ============
    elif data == "get_video":
        await client.send_message(user_id, "/getvideo")
    
    # ============ BRAZZERS BUTTON ============
    elif data == "brazzers":
        await client.send_message(user_id, "/brazzers")
    
    # ============ MY PLAN BUTTON ============
    elif data == "my_plan":
        await client.send_message(user_id, "/myplan")
    
    # ============ SUBSCRIPTION BUTTON ============
    elif data == "subscription":
        await client.send_message(user_id, "/buy")
    
    # ============ APPROVE PAYMENT ============
    elif data.startswith("approve_"):
        if admin_id not in ADMINS:
            await query.answer("❌ You are not authorized!", show_alert=True)
            return
        
        try:
            parts = data.split("_")
            if len(parts) >= 3:
                user_id = int(parts[1])
                days = int(parts[2])
                
                new_expiry = await db.add_premium_access(user_id, days)
                expiry_ist = new_expiry.astimezone(pytz.timezone("Asia/Kolkata"))
                expiry_str = expiry_ist.strftime("%d-%m-%Y %I:%M %p")
                
                try:
                    await client.send_message(
                        user_id,
                        f"🎉 <b>Payment Approved!</b>\n\n"
                        f"💎 <b>Premium Activated</b> for {days} Days.\n"
                        f"🗓 <b>Expiry:</b> {expiry_str}\n\n"
                        f"<i>Enjoy Unlimited Access!</i>"
                    )
                except Exception as e:
                    print(f"Could not notify user: {e}")
                
                await query.message.edit_caption(
                    caption=f"✅ <b>Approved by {query.from_user.mention}</b>\n\n"
                           f"🆔 User: <code>{user_id}</code>\n"
                           f"⏳ Added: {days} Days\n"
                           f"📅 Expires: {expiry_str}"
                )
                
                await query.answer(f"✅ Approved {days} days for user {user_id}", show_alert=True)
            else:
                await query.answer("Invalid data format!", show_alert=True)
                
        except Exception as e:
            print(f"Approve error: {e}")
            await query.answer(f"Error: {str(e)}", show_alert=True)
    
    # ============ REJECT PAYMENT ============
    elif data.startswith("reject_"):
        if admin_id not in ADMINS:
            await query.answer("❌ You are not authorized!", show_alert=True)
            return
        
        try:
            parts = data.split("_")
            if len(parts) >= 2:
                user_id = int(parts[1])
                
                try:
                    await client.send_message(
                        user_id,
                        f"❌ <b>Payment Rejected.</b>\n\n"
                        f"<i>Possible reasons:</i>\n"
                        f"- Invalid Screenshot\n"
                        f"- Payment not received\n"
                        f"- Wrong Amount\n\n"
                        f"<i>Contact Admin for support.</i>"
                    )
                except Exception as e:
                    print(f"Could not notify user: {e}")
                
                await query.message.edit_caption(
                    caption=f"❌ <b>Rejected by {query.from_user.mention}</b>\n\n"
                           f"🆔 User: <code>{user_id}</code>"
                )
                
                await query.answer(f"❌ Rejected payment for user {user_id}", show_alert=True)
            else:
                await query.answer("Invalid data format!", show_alert=True)
                
        except Exception as e:
            print(f"Reject error: {e}")
            await query.answer(f"Error: {str(e)}", show_alert=True)
    
    # ============ INDEX BUTTONS (index.py handle karega) ============
    elif data.startswith("index"):
        # Yeh index.py handle karega
        pass
    
    # ============ DELETE BUTTONS (bot_stats.py handle karega) ============
    elif data.startswith("del_"):
        # Yeh bot_stats.py handle karega
        pass
    
    # ============ BROADCAST CANCEL ============
    elif data.startswith("broadcast_cancel"):
        # Yeh broadcast.py handle karega
        pass
    
    # ============ UNKNOWN ============
    else:
        print(f"Unknown callback: {data}")
