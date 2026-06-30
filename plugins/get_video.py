from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY, TIMEZONE
import asyncio
import pytz
from datetime import datetime
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined


# ---------- INITIALIZE USER HISTORY ----------
def init_user_history(user_id, is_brazzers=False):
    if user_id not in temp.USER_VIDEO_HISTORY:
        temp.USER_VIDEO_HISTORY[user_id] = {
            "history": [],
            "current_index": -1,
            "is_brazzers": is_brazzers
        }


# ---------- HELPER FUNCTION ----------
def get_ist_today():
    return datetime.now(pytz.timezone(TIMEZONE)).date()


# ---------- CHECK LIMIT FUNCTION ----------
async def check_user_limit(user_id):
    """Check if user has reached daily limit"""
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
        user_type = "premium"
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
        user_type = "verified"
    else:
        current_limit = DAILY_LIMIT
        user_type = "normal"
    
    used = await db.get_video_count(user_id) or 0
    
    # Auto reset check
    user = await db.get_user(user_id)
    if user:
        last_date = user.get("last_date")
        today = get_ist_today()
        
        if last_date:
            if isinstance(last_date, datetime):
                if last_date.tzinfo is not None:
                    check_date = last_date.astimezone(pytz.timezone(TIMEZONE)).date()
                else:
                    check_date = last_date.date()
            else:
                check_date = None
                
            if check_date != today:
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"video_count": 0, "last_date": datetime.combine(today, datetime.min.time())}}
                )
                used = 0
    
    return {
        "used": used,
        "limit": current_limit,
        "is_premium": is_premium,
        "is_verified": is_verified,
        "user_type": user_type,
        "reached": used >= current_limit
    }


# ---------- SEND LIMIT MESSAGE ----------
async def send_limit_message(message, limit_data):
    """Send proper limit reached message"""
    used = limit_data["used"]
    limit = limit_data["limit"]
    user_type = limit_data["user_type"]
    
    if user_type == "premium":
        text = f"❌ **Premium Daily Limit Reached!**\n\n📊 You have used {used}/{limit} videos today.\n🔄 Please try again tomorrow."
    elif user_type == "verified":
        text = f"❌ **Verified Daily Limit Reached!**\n\n📊 You have used {used}/{limit} videos today.\n💎 Buy premium for more!"
    else:
        text = f"❌ **Daily Limit Reached!**\n\n📊 You have used {used}/{limit} videos today.\n💎 Buy premium for unlimited access!"
    
    await message.reply(
    text,
    reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")],
        [InlineKeyboardButton("✖️Close✖️", callback_data="close_data")]
    ])
)


# ---------- MAIN COMMAND HANDLER ----------
@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):
    if not m.from_user:
        return
    if FSUB and not await is_user_joined(client, m):
        return

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"

    if await ban_manager.check_ban(client, m):
        return

    # Check limit
    limit_data = await check_user_limit(user_id)
    
    if limit_data["reached"]:
        if limit_data["is_premium"]:
            return await m.reply(f"❌ Premium limit {PREMIUM_DAILY_LIMIT} reached. Try tomorrow!")
        else:
            if limit_data["is_verified"]:
                return await m.reply(f"❌ Daily limit {limit_data['limit']} reached.\n✨ Upgrade to Premium for Unlimited Access! 💎")
            else:
                if IS_VERIFY:
                    # ✅ Ensure command attribute exists
                    if not hasattr(m, 'command') or m.command is None:
                        m.command = []
                    
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    # Recheck after verification
                    limit_data = await check_user_limit(user_id)
                    if limit_data["reached"]:
                        return await m.reply(f"❌ Verified limit reached. Buy premium!")
                else:
                    return await m.reply(
                        f"❌ Daily limit {limit_data['limit']} reached.\n✨ Upgrade to Premium for Unlimited Access! 💎",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")],
                            [InlineKeyboardButton("✖️Close✖️", callback_data="close_data")]
                        ])
                    )

    # ---------- GET NEW VIDEO ----------
    video_id = await db.get_unseen_video(user_id)
    if not video_id:
        video_id = await db.get_random_video()
    if not video_id:
        return await m.reply("❌ No videos found.")

    # ---------- INITIALIZE HISTORY ----------
    init_user_history(user_id, is_brazzers=False)
    
    # Add video to history if not already present
    if video_id not in temp.USER_VIDEO_HISTORY[user_id]["history"]:
        temp.USER_VIDEO_HISTORY[user_id]["history"].append(video_id)
        temp.USER_VIDEO_HISTORY[user_id]["current_index"] = len(temp.USER_VIDEO_HISTORY[user_id]["history"]) - 1

    # ---------- SEND VIDEO WITH BUTTONS ----------
    await send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False)


# ---------- SEND VIDEO FUNCTION ----------
async def send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False):
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    # Ensure history exists
    init_user_history(user_id, is_brazzers)
    
    # Get current index
    history = temp.USER_VIDEO_HISTORY[user_id]
    current_idx = history["current_index"]
    
    # Build Buttons - Previous + Next + Download + Close
    buttons = []
    
    # ✅ Row 1: Previous + Next
    row1 = []
    
    # ✅ Previous button
    if current_idx > 0:
        row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{'brazzers' if is_brazzers else 'video'}"))
    else:
        row1.append(InlineKeyboardButton("⏪ Previous", callback_data="noop"))
    
    # ✅ Next button
    row1.append(InlineKeyboardButton("⏩ Next", callback_data=f"next_{'brazzers' if is_brazzers else 'video'}"))
    buttons.append(row1)
    
    # ✅ Row 2: Download Button (NEW)
    row2 = [
        InlineKeyboardButton("📥 Download", callback_data=f"download_{video_id}_{'brazzers' if is_brazzers else 'video'}")
    ]
    buttons.append(row2)
    
    # ✅ Row 3: Close Button
    row3 = [
        InlineKeyboardButton("✖️ Close ✖️", callback_data="close_data")
    ]
    buttons.append(row3)

    reply_markup = InlineKeyboardMarkup(buttons)

    # Send video
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
        reply_to_message_id=m.id,
        reply_markup=reply_markup
    )

    # Increase count only for new videos (not for navigation)
    if not is_brazzers:
        await db.increase_video_count(user_id, username)

    asyncio.create_task(auto_delete_message(m, sent))


# ---------- DOWNLOAD CALLBACK HANDLER ----------
@Client.on_callback_query(filters.regex(r"^download_"))
async def download_callback_handler(client, query: CallbackQuery):
    """
    Handle download button clicks - Premium check + Download link generation
    """
    user_id = query.from_user.id
    
    try:
        # Parse callback data: download_fileId_videoType
        data_parts = query.data.split("_")
        if len(data_parts) < 3:
            await query.answer("❌ Invalid request!", show_alert=True)
            return
        
        # Extract file_id from callback data
        # Format: download_fileId_videoType
        # File ID can contain underscores, so we need to handle carefully
        file_id = "_".join(data_parts[1:-1])  # Join middle parts as file_id
        video_type = data_parts[-1]  # Last part is video type (video/brazzers)
        
        # ✅ Check if user is premium
        is_premium = await db.has_premium_access(user_id)
        
        if not is_premium:
            # ❌ Not premium - Only show popup alert (as requested)
            await query.answer(
                "💎 This feature is only for premium users!",
                show_alert=True
            )
            return
        
        # ✅ User is premium - Generate download link
        await query.answer("📥 Generating download link...", show_alert=False)
        
        # Get the file from database
        if video_type == "brazzers":
            file_data = await db.brazzers.find_one({"file_id": file_id})
        else:
            file_data = await db.videos.find_one({"file_id": file_id})
        
        if not file_data:
            await query.answer("❌ File not found!", show_alert=True)
            return
        
        # Send the file as document for download
        try:
            sent_msg = await client.send_document(
                chat_id=query.message.chat.id,
                document=file_data["file_id"],
                caption=f"📥 **Your download is ready!**\n\n"
                        f"🔹 _File will auto-delete after 10 minutes_",
                protect_content=True,
                reply_to_message_id=query.message.id
            )
            
            # Auto delete after 10 minutes
            asyncio.create_task(auto_delete_message(query.message, sent_msg))
            
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)[:50]}...", show_alert=True)
            
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)[:50]}...", show_alert=True)


# ---------- CALLBACK HANDLER FOR NEXT / PREVIOUS ----------
@Client.on_callback_query(filters.regex(r"^(next_|prev_|noop)"))
async def video_navigation_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    message = query.message
    
    # Handle noop (disabled button click)
    if data == "noop":
        await query.answer("⚠️ This is the first video!", show_alert=True)
        return
    
    # Parse callback data: next_video, prev_video, next_brazzers, prev_brazzers
    try:
        action, video_type = data.split("_")
    except ValueError:
        await query.answer("❌ Invalid request!", show_alert=True)
        return
    
    is_brazzers = video_type == "brazzers"

    # Get user history
    history_data = temp.USER_VIDEO_HISTORY.get(user_id)
    if not history_data or not history_data["history"]:
        await query.answer("❌ No history found. Try /getvideo!", show_alert=True)
        return
    
    history = history_data["history"]
    current_idx = history_data["current_index"]
    
    # ---------- CHECK LIMIT FIRST (for both Next and Previous) ----------
    limit_data = await check_user_limit(user_id)
    
    if limit_data["reached"]:
        # Don't show popup, just send message
        await send_limit_message(message, limit_data)
        return
    
    # ---------- PREVIOUS BUTTON ----------
    if action == "prev":
        if current_idx <= 0:
            await query.answer("⚠️ This is the first video!", show_alert=True)
            return
        
        new_idx = current_idx - 1
        video_id = history[new_idx]
        
        await query.answer("⏪ Loading previous video...", show_alert=False)
        
        # Update current index
        history_data["current_index"] = new_idx
        
        # Delete old message
        try:
            await message.delete()
        except Exception:
            pass

        # Resend video
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        await send_video_with_buttons(
            client, 
            fake_msg, 
            user_id, 
            video_id,
            is_brazzers=is_brazzers
        )
        return

    # ---------- NEXT BUTTON ----------
    if action == "next":
        # Check if video exists in history first
        if current_idx + 1 < len(history):
            # Video already in history - just navigate
            new_idx = current_idx + 1
            video_id = history[new_idx]
            
            await query.answer("⏩ Loading...", show_alert=False)
            
            # Update current index
            history_data["current_index"] = new_idx
            
            # Delete old message
            try:
                await message.delete()
            except Exception:
                pass

            fake_msg = message
            fake_msg.from_user = query.from_user
            fake_msg.chat = message.chat

            await send_video_with_buttons(
                client,
                fake_msg,
                user_id,
                video_id,
                is_brazzers=is_brazzers
            )
            return
        
        # ---------- GET NEW VIDEO (Not in history) ----------
        await query.answer("⏩ Loading....", show_alert=False)
        
        # Mark current as seen (only for next)
        current_video = history[current_idx]
        if is_brazzers:
            await db.mark_brazzers_seen(user_id, current_video)
        else:
            await db.mark_seen(user_id, current_video)

        # Get new video
        if is_brazzers:
            new_video = await db.get_unseen_brazzers(user_id)
            if not new_video:
                await message.reply("❌ No more unseen Brazzers videos!")
                return
        else:
            new_video = await db.get_unseen_video(user_id)
            if not new_video:
                new_video = await db.get_random_video()
            if not new_video:
                await message.reply("❌ No more videos!")
                return

        # Add to history
        history.append(new_video)
        history_data["current_index"] = len(history) - 1

        # Delete old message
        try:
            await message.delete()
        except Exception:
            pass

        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        await send_video_with_buttons(
            client,
            fake_msg,
            user_id,
            new_video,
            is_brazzers=is_brazzers
        )
