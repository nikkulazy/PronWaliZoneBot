from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined
import datetime  # ✅ ADD THIS


@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):

    # Safety check
    if not m.from_user:
        return

    # Force subscribe check
    if FSUB and not await is_user_joined(client, m):
        return

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"

    # Ban check
    if await ban_manager.check_ban(client, m):
        return

    # =============================================
    # ✅ USER FETCH - FIXED
    # =============================================
    
    user = await db.get_user(user_id)
    
    if not user:
        await m.reply("❌ Please use /start first!")
        return
    
    # =============================================
    # ✅ PREMIUM CHECK
    # =============================================
    
    plan = user.get("plan", "Free")
    is_premium = (plan == "Premium")
    
    # =============================================
    # ✅ DAILY LIMIT CHECK
    # =============================================
    
    today = datetime.datetime.now().date()
    last_date = user.get("last_date")
    
    if str(today) != last_date:
        await db.update_user(user_id, {"used_today": 0, "last_date": str(today)})
        used_today = 0
    else:
        used_today = user.get("used_today", 0)
    
    # =============================================
    # ✅ LIMIT SET KAREIN
    # =============================================
    
    if is_premium:
        limit = PREMIUM_DAILY_LIMIT  # 999
    else:
        # ✅ Check if user is verified
        is_verified = await db.is_user_verified(user_id)
        if is_verified:
            limit = VERIFICATION_DAILY_LIMIT
        else:
            limit = DAILY_LIMIT  # 5
    
    # =============================================
    # ✅ FREE USER - LIMIT CHECK
    # =============================================
    
    if not is_premium:
        
        # ✅ CHECK: KYA LIMIT CROSS HO GAYI?
        if used_today >= limit:
            # ❌ ALERT MESSAGE - Video nahi milega
            await m.reply(
                f"🚫 **Daily Limit Exceeded!**\n\n"
                f"📊 **Today's Usage:** {used_today}/{limit}\n"
                f"⏳ **Reset Time:** Midnight (12:00 AM)\n\n"
                f"💎 **Upgrade to Premium for unlimited access!**\n\n"
                f"✅ Unlimited files\n"
                f"✅ No daily limit\n"
                f"✅ Priority access",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Buy Premium 💎", callback_data="subscription")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
            return  # ❌ VIDEO SEND NAHI HOGA
        
        # ✅ FREE USER: LIMIT UPDATE KAREIN
        await db.update_user(user_id, {"used_today": used_today + 1})
        
        # ✅ NAYA REMAINING CALCULATE KAREIN
        new_remaining = limit - (used_today + 1)
        
        # ✅ WARNING: JAB 3 YA USSE KAM FILES BAKI HO
        if new_remaining <= 3 and new_remaining > 0:
            await m.reply(
                f"⚠️ **Warning!**\n\n"
                f"📊 You have used {used_today + 1}/{limit} files today.\n"
                f"📉 **Remaining:** {new_remaining} file{'s' if new_remaining > 1 else ''}\n\n"
                f"💎 Upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Upgrade Now", callback_data="subscription")]
                ])
            )
        
        # ✅ JAB 0 FILES BAKI HO (5th file ke baad)
        if new_remaining == 0:
            await m.reply(
                f"⚠️ **Last Free File!**\n\n"
                f"📊 You have used {used_today + 1}/{limit} files today.\n"
                f"📉 **No files remaining!**\n\n"
                f"💎 Upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Buy Premium 💎", callback_data="subscription")]
                ])
            )
    
    # =============================================
    # ✅ PREMIUM USER - UNLIMITED
    # =============================================
    
    if is_premium:
        if used_today >= limit:
            await m.reply(
                f"⚠️ Premium Limit Reached!\n\n"
                f"📊 Used: {used_today}/{limit}\n"
                f"⏳ Reset at midnight!"
            )
            return
        
        # ✅ Premium user ka usage update
        await db.update_user(user_id, {"used_today": used_today + 1})
    
    # =============================================
    # ✅ GET VIDEO FROM DATABASE
    # =============================================
    
    video_id = await db.get_unseen_video(user_id)

    if not video_id:
        try:
            video_id = await db.get_random_video()
        except Exception as e:
            print(f"[Random Video Error] {e}")
            return

    if not video_id:
        return await m.reply("❌ No videos found in the database.")

    # =============================================
    # ✅ SEND VIDEO
    # =============================================
    
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
            ),
            reply_to_message_id=m.id
        )

        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        await m.reply(f"❌ Failed to send video: {str(e)}")
