from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
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

    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0

    # ---------- LIMIT CHECK ----------
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(f"❌ Premium limit {PREMIUM_DAILY_LIMIT} reached. Try tomorrow!")
    else:
        if used >= current_limit:
            if is_verified:
                return await m.reply(f"❌ Daily limit {current_limit} reached. Buy premium!")
            else:
                if IS_VERIFY:
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    used = await db.get_video_count(user_id) or 0
                    if used >= VERIFICATION_DAILY_LIMIT:
                        return await m.reply(f"❌ Verified limit reached. Buy premium!")
                else:
                    return await m.reply(
                        f"❌ Daily limit {current_limit} reached. Buy premium!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")]
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
    
    # Build Buttons - Previous + Next only
    buttons = []
    row = []
    
    # ✅ Previous button - Always show (agar history mein pehle se koi video hai)
    if current_idx > 0:
        row.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{'brazzers' if is_brazzers else 'video'}"))
    else:
        # ✅ Disabled previous button (grayed out - but still visible)
        row.append(InlineKeyboardButton("⏪ Previous", callback_data="noop"))
    
    # ✅ Next button - Always show
    row.append(InlineKeyboardButton("⏩ Next", callback_data=f"next_{'brazzers' if is_brazzers else 'video'}"))
    buttons.append(row)

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


# ---------- GET VIDEO FROM HISTORY BY INDEX ----------
async def get_video_from_history(user_id, index, is_brazzers):
    history_data = temp.USER_VIDEO_HISTORY.get(user_id)
    if not history_data:
        return None
    
    history = history_data["history"]
    if index < 0 or index >= len(history):
        return None
    
    return history[index]


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
    action, video_type = data.split("_")
    is_brazzers = video_type == "brazzers"

    # Get user history
    history_data = temp.USER_VIDEO_HISTORY.get(user_id)
    if not history_data or not history_data["history"]:
        await query.answer("❌ No history found. Try /getvideo!", show_alert=True)
        return
    
    history = history_data["history"]
    current_idx = history_data["current_index"]
    
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
        except:
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
        # Check if next video exists in history
        if current_idx + 1 < len(history):
            # Video already in history - just navigate
            new_idx = current_idx + 1
            video_id = history[new_idx]
            
            await query.answer("⏩ Loading next video from history...", show_alert=False)
            
            # Update current index
            history_data["current_index"] = new_idx
            
            # Delete old message
            try:
                await message.delete()
            except:
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
        await query.answer("⏩ Loading new video...", show_alert=False)
        
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
                await query.message.reply("❌ No more unseen Brazzers videos!")
                return
        else:
            new_video = await db.get_unseen_video(user_id)
            if not new_video:
                new_video = await db.get_random_video()
            if not new_video:
                await query.message.reply("❌ No more videos!")
                return

        # Add to history
        history.append(new_video)
        history_data["current_index"] = len(history) - 1

        # Delete old message
        try:
            await message.delete()
        except:
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

# 🔥 NEW: Auto reset agar date change ho gayi ho
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
            # 🔥 Auto reset if date changed
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"video_count": 0, "last_date": datetime.combine(today, datetime.min.time())}}
            )
            used = 0
