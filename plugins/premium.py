from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from Script import script
from database.users_db import db
from info import (
    VERIFICATION_DAILY_LIMIT, 
    DAILY_LIMIT, 
    PREMIUM_DAILY_LIMIT, 
    ADMINS, 
    LOG_CHANNEL, 
    PREMIUM_LOGS, 
    OWNER_USERNAME, 
    UPI_ID, 
    QR_CODE_IMAGE, 
    FREE_VIDEO_DURATION
)
from datetime import timedelta
import pytz, datetime
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from utils import temp, get_seconds

# -------------------------------------------------------------------------
# 📋 ADMIN: LIST PREMIUM USERS
# -------------------------------------------------------------------------
@Client.on_message(filters.command("premium_user") & filters.user(ADMINS))
async def premium_user(client, message):
    aa = await message.reply_text("Fetching ...")  
    users = db.get_all_users()
    users_list = []
    async for user in users:
        users_list.append(user)    
    user_data = {user['id']: await db.get_user(user['id']) for user in users_list}    
    new_users = []
    for user in users_list:
        user_id = user['id']
        data = user_data.get(user_id)
        expiry = data.get("expiry_time") if data else None        
        if expiry:
            # Check if expiry is timezone aware
            if expiry.tzinfo is None:
                expiry = pytz.utc.localize(expiry)
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y %I:%M:%S %p")          
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days, remainder = divmod(time_left.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)            
            time_left_str = f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes"            
            user_info = await client.get_users(user_id)
            user_str = (
                f"{len(new_users) + 1}. User ID: {user_id}\n"
                f"Name: {user_info.mention}\n"
                f"Expiry Date: {expiry_str_in_ist}\n"
                f"Expiry Time: {time_left_str}\n\n"
            )
            new_users.append(user_str)
    
    if not new_users:
        await aa.edit_text("No premium users found.")
        return
        
    new = "Paid Users - \n\n" + "\n".join(new_users)   
    try:
        await aa.edit_text(new)
    except MessageTooLong:
        with open('usersplan.txt', 'w+') as outfile:
            outfile.write(new)
        await message.reply_document('usersplan.txt', caption="Paid Users:")

# -------------------------------------------------------------------------
# 🛍️ BUY COMMAND (Shows Plan & QR Code)
# -------------------------------------------------------------------------
@Client.on_message(filters.command("buy") | filters.regex(r"(?i)Subscription"))
async def buy_handler(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    is_premium = await db.has_premium_access(user_id)
    user_username = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    log_text = (
        f"#Buy_Command_Used\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"👤 Name: {username}\n"
        f"💬 Username: {user_username}\n"
    )
    
    try:
        await client.send_message(PREMIUM_LOGS, log_text)
    except Exception as e:
        print(f"Failed to send log to PREMIUM_LOGS: {e}")
        
    if is_premium:
        await message.reply_text("✅ You already have Premium Subscription! Enjoy your benefits.", quote=True)
        return
        
    text = script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID)
    btn = [
        [InlineKeyboardButton('✖️ Close ✖️', callback_data='close_data')]
    ]
    if QR_CODE_IMAGE:
        await message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=text,
            reply_markup=InlineKeyboardMarkup(btn)
        )
    else:
        await message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(btn)
        )

# -------------------------------------------------------------------------
# 📸 SCREENSHOT HANDLER (Direct Auto-Forward to Admin)
# -------------------------------------------------------------------------
@Client.on_message(filters.photo & filters.private)
async def payment_screenshot_handler(client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.mention
    user_note = message.caption if message.caption else "No caption provided"
    msg = await message.reply_text("🔄 Sending payment screenshot to Admins... Please wait.")
    
    admin_btns = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve (1 Day)", callback_data=f"add_prem_{user_id}_1"),
            InlineKeyboardButton("✅ Approve (1 Week)", callback_data=f"add_prem_{user_id}_7")
        ],
        [
            InlineKeyboardButton("✅ Approve (1 Month)", callback_data=f"add_prem_{user_id}_30")
        ],
        [
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_pay_{user_id}")
        ]
    ])
    
    try:
        await client.send_photo(
            chat_id=PREMIUM_LOGS,
            photo=message.photo.file_id,
            caption=f"🧾 **New Payment Screenshot**\n\n👤 <b>User:</b> {user_name}\n🆔 <b>ID:</b> <code>{user_id}</code>\n📝 <b>Note:</b> {user_note}",
            reply_markup=admin_btns
        )
        await msg.edit_text("✅ Screenshot sent!\nAdmin will verify and activate your plan shortly.")
    except Exception as e:
        await msg.edit_text(f"❌ Error sending to admin: {e}")

# -------------------------------------------------------------------------
# ✅ APPROVE PAYMENT CALLBACK
# -------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^add_prem_"))
async def approve_payment(client, callback_query: CallbackQuery):
    try:
        _, _, user_id, days = callback_query.data.split("_")
        user_id = int(user_id)
        days = int(days)
    except ValueError:
        await callback_query.answer("Invalid data format!", show_alert=True)
        return
    
    new_expiry = await db.add_premium_access(user_id, days)
    
    # Ensure expiry is timezone aware
    if new_expiry.tzinfo is None:
        new_expiry = pytz.utc.localize(new_expiry)
    expiry_ist = new_expiry.astimezone(pytz.timezone("Asia/Kolkata"))
    expiry_str = expiry_ist.strftime("%d-%m-%Y %I:%M %p")
    
    try:
        await client.send_message(
            user_id,
            f"🎉 <b>Payment Approved!</b>\n\n💎 <b>Premium Activated</b> for {days} Days.\n🗓 <b>Expiry:</b> {expiry_str}\n\n<i>Enjoy Unlimited Access!</i>"
        )
    except Exception as e:
        print(f"Failed to send approval message to user: {e}")
        
    await callback_query.message.edit_caption(
        caption=f"✅ <b>Approved by {callback_query.from_user.mention}</b>\n\n🆔 User: <code>{user_id}</code>\n⏳ Added: {days} Days"
    )
    await callback_query.answer("Premium access granted!", show_alert=True)

# -------------------------------------------------------------------------
# ❌ REJECT PAYMENT CALLBACK
# -------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^reject_pay_"))
async def reject_payment(client, callback_query: CallbackQuery):
    try:
        user_id = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        await callback_query.answer("Invalid data format!", show_alert=True)
        return
        
    try:
        await client.send_message(
            user_id,
            f"❌ <b>Payment Rejected.</b>\n\n<i>Possible reasons:</i>\n- Invalid Screenshot\n- Payment not received\n- Wrong Amount\n\n<i>Contact Admin for support. @{OWNER_USERNAME}</i>"
        )
    except Exception as e:
        print(f"Failed to send rejection message to user: {e}")
        
    await callback_query.message.edit_caption(
        caption=f"❌ <b>Rejected by {callback_query.from_user.mention}</b>\n\n🆔 User: <code>{user_id}</code>"
    )
    await callback_query.answer("Payment rejected!", show_alert=True)

# -------------------------------------------------------------------------
# 👤 MY PLAN COMMAND (MODIFIED - WITH DURATION LIMIT)
# -------------------------------------------------------------------------
@Client.on_message((filters.command("myplan") | filters.regex(r"(?i)^my\s?plan$")) & filters.private)
async def myplan_handler(_, m: Message):
    user_id = m.from_user.id
    username = m.from_user.first_name

    used = await db.get_video_count(user_id)
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)

    # -------- LIMIT LOGIC --------
    if is_premium:
        daily_limit = PREMIUM_DAILY_LIMIT
        subscription_type = "💎 Premium"
        duration_limit = "Unlimited"
    elif is_verified:
        daily_limit = VERIFICATION_DAILY_LIMIT
        subscription_type = "✅ Verified"
        duration_limit = f"{FREE_VIDEO_DURATION//60}m"
    else:
        daily_limit = DAILY_LIMIT
        subscription_type = "🆓 Free"
        duration_limit = f"{FREE_VIDEO_DURATION//60}m"

    remaining = max(daily_limit - used, 0)

    premium_details = await db.get_user(user_id) if is_premium else None

    # -------- SAME STYLE TEXT --------
    text = f"""📊 <b>Your Plan Details</b>

👤 <b>User:</b> {username}
🆔 <b>User ID:</b> <code>{user_id}</code>
💠 <b>Subscription:</b> {subscription_type}
📂 <b>Daily Limit:</b> {daily_limit} Files
⏱️ <b>Max Duration:</b> {duration_limit}
📉 <b>Used:</b> {used} | <b>Left:</b> {remaining}

✨ Upgrade to Premium for Unlimited Access & Ad-Free Experience! 💎"""

    # -------- PREMIUM EXPIRY --------
    if is_premium and premium_details and premium_details.get('expiry_time'):
        expiry = premium_details['expiry_time']
        if expiry.tzinfo is None:
            expiry = pytz.utc.localize(expiry)
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))

        text += f"""

⏳ <b>Subscription Details</b>
📅 Expiry: {expiry_ist.strftime('%d-%m-%Y')}
⏰ Time: {expiry_ist.strftime('%I:%M %p')}"""

    await m.reply(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade To Premium", callback_data="get_subscription")],
        [InlineKeyboardButton("✖️ Close ✖️", callback_data="close_data")]
    ]))

# -------------------------------------------------------------------------
# 🛠 ADMIN COMMAND: ADD PREMIUM (Manual)
# -------------------------------------------------------------------------
@Client.on_message(filters.command("add_premium") & filters.user(ADMINS))
async def give_premium_cmd_handler(client, message):
    if len(message.command) == 4:
        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y\n⏱️ Joining Time: %I:%M:%S %p") 
        user_id = int(message.command[1])  
        
        try:
            user = await client.get_users(user_id)
        except Exception:
            await message.reply_text("❌ Invalid user ID")
            return
        
        # Combine duration parts
        duration = message.command[2] + " " + message.command[3]
        seconds = await get_seconds(duration)
        
        if seconds > 0:
            expiry_time = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=seconds)
            user_data = {"id": user_id, "expiry_time": expiry_time, "is_premium": True}  
            await db.update_user(user_data) 
            
            data = await db.get_user(user_id)
            expiry = data.get("expiry_time")   
            
            # Ensure expiry is timezone aware
            if expiry.tzinfo is None:
                expiry = pytz.utc.localize(expiry)

            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ Expiry Time: %I:%M:%S %p")
            expiry_str_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y At: %I:%M:%S %p")         
            
            await message.reply_text(
                f"✅ Premium added successfully!\n\n"
                f"👤 User: {user.mention}\n"
                f"⚡ User ID: <code>{user_id}</code>\n"
                f"⏰ Premium Access: <code>{duration}</code>\n\n"
                f"⏳ Joining Date: {current_time}\n\n"
                f"⌛️ Expiry Date: {expiry_str_in_ist}",
                disable_web_page_preview=True
            )
            
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=f"🎉 Congratulations! You've got Premium Access!\n\n"
                         f"⏳ Duration: {duration}\n"
                         f"📅 Expiry: {expiry_str_ist}\n\n"
                         f"✨ Enjoy your premium benefits!",
                    disable_web_page_preview=True             
                )    
            except Exception as e:
                print(f"Failed to send premium notification to user: {e}")
                
            await client.send_message(
                PREMIUM_LOGS, 
                text=f"#Added_Premium\n\n"
                     f"👤 User: {user.mention}\n"
                     f"⚡ User ID: <code>{user_id}</code>\n"
                     f"⏰ Premium Access: <code>{duration}</code>\n\n"
                     f"⏳ Joining Date: {current_time}\n\n"
                     f"⌛️ Expiry Date: {expiry_str_in_ist}", 
                disable_web_page_preview=True
            )
        else:
            await message.reply_text("❌ Invalid time format. Please use '1 day', '1 hour', '1 min', '1 month', or '1 year'")
    else:
        await message.reply_text("Usage: /add_premium user_id time (e.g., '1 day', '1 hour', '1 min', '1 month', or '1 year')")

# -------------------------------------------------------------------------
# 🛠 ADMIN COMMAND: REMOVE PREMIUM
# -------------------------------------------------------------------------
@Client.on_message(filters.command("remove_premium") & filters.user(ADMINS))
async def remove_premium(client, message):
    if len(message.command) == 2:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID format")
            return
            
        try:
            user = await client.get_users(user_id)
        except Exception:
            await message.reply_text("❌ Invalid user ID")
            return
            
        if await db.remove_premium_access(user_id):
            await message.reply_text("✅ User removed successfully!")
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=f"<b>Hey {user.mention},\n\nYour Premium Access has been removed.</b>"
                )
            except Exception as e:
                print(f"Failed to send removal notification: {e}")
        else:
            await message.reply_text("❌ Unable to remove user!\nAre you sure it was a premium user?")
    else:
        await message.reply_text("Usage: /remove_premium user_id")

# -------------------------------------------------------------------------
# 🆘 HELP: CLOSE BUTTON CALLBACK
# -------------------------------------------------------------------------
@Client.on_callback_query(filters.regex("close_data"))
async def close_callback(client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await callback_query.answer()

# -------------------------------------------------------------------------
# 🆘 HELP: GET SUBSCRIPTION CALLBACK
# -------------------------------------------------------------------------
@Client.on_callback_query(filters.regex("get_subscription"))
async def get_subscription_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    # This will trigger the buy command functionality
    await buy_handler(client, callback_query.message)
