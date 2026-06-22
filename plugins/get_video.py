import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined


@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):
    await process_video_request(client, m, direction="next")

async def process_video_request(client, m: Message, direction="next", current_video_id=None):
    """Core function to handle video requests with navigation"""
    
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

    # Premium + limit info
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    # Define limits based on status
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0

    # LIMIT CHECK
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(
                f"❌ You've reached your Premium limit of {PREMIUM_DAILY_LIMIT} files.\n"
                f"⏳ Try again tomorrow!"
            )
    else:
        if used >= current_limit:
            if is_verified:
                return await m.reply(
                    f"❌ You've reached your daily limit of {current_limit} files.\n"
                    f"💎 Buy premium for more access!\n\n"
                    f"⏳ Resets tomorrow."
                )
            else:
                if IS_VERIFY:
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    used = await db.get_video_count(user_id) or 0
                    if used >= VERIFICATION_DAILY_LIMIT:
                        return await m.reply(
                            f"❌ You've reached your daily limit of {VERIFICATION_DAILY_LIMIT} files.\n"
                            f"💎 Buy premium for more access!"
                        )
                else:
                    return await m.reply(
                        f"❌ You've reached your daily limit of {current_limit} files.\n"
                        f"💎 Buy premium for unlimited access!\n\n"
                        f"⏳ Resets tomorrow.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")]
                        ])
                    )

    # GET VIDEO
    video_id = None
    
    if direction == "next":
        video_id = await get_unseen_video_direct(user_id)
    elif direction == "previous" and current_video_id:
        video_id = await get_previous_video_direct(user_id, current_video_id)
        if not video_id:
            return await m.reply("❌ No previous video found! Watch some videos first.")
    else:
        video_id = await get_unseen_video_direct(user_id)

    if not video_id:
        return await m.reply("❌ No videos found in the database.")

    # SEND VIDEO WITH BUTTONS
    try:
        has_previous = await has_previous_video_direct(user_id, video_id)
        
        nav_buttons = []
        if has_previous:
            prev_video = await get_previous_video_direct(user_id, video_id)
            if prev_video:
                nav_buttons.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_vid_{prev_video}"))
        
        nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="get_video"))
        
        reply_markup = InlineKeyboardMarkup([
            nav_buttons,
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])
        
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

        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        print(f"❌ Error sending video: {e}")
        await m.reply(f"❌ Failed to send video: {str(e)}")


# ============================================================
# DIRECT DATABASE FUNCTIONS
# ============================================================

async def get_unseen_video_direct(user_id):
    """Get unseen video and save to history"""
    try:
        history = await db.historys.find_one({"user_id": user_id})
        seen_ids = history.get("seen", []) if history else []
        
        all_videos = []
        cursor = db.videos.find({})
        async for video in cursor:
            if video["file_id"] not in seen_ids:
                all_videos.append(video["file_id"])
        
        if not all_videos:
            cursor = db.videos.aggregate([{"$sample": {"size": 1}}])
            result = await cursor.to_list(length=1)
            if result:
                video_id = result[0]["file_id"]
                await mark_seen_direct(user_id, video_id)
                return video_id
            return None
        
        video_id = random.choice(all_videos)
        await mark_seen_direct(user_id, video_id)
        return video_id
    except Exception as e:
        print(f"❌ Error in get_unseen_video_direct: {e}")
        return None

async def mark_seen_direct(user_id, file_id):
    """Directly mark video as seen in history"""
    try:
        history = await db.historys.find_one({"user_id": user_id})
        
        if history:
            seen_list = history.get("seen", [])
            if file_id not in seen_list:
                seen_list.append(file_id)
                await db.historys.update_one(
                    {"user_id": user_id},
                    {"$set": {"seen": seen_list}}
                )
        else:
            await db.historys.insert_one({
                "user_id": user_id,
                "seen": [file_id]
            })
    except Exception as e:
        print(f"❌ Error marking seen: {e}")

async def get_previous_video_direct(user_id, current_video_id):
    """Get previous video from user's history"""
    try:
        history = await db.historys.find_one({"user_id": user_id})
        if not history:
            return None
        
        seen_list = history.get("seen", [])
        if len(seen_list) < 2:
            return None
        
        try:
            current_index = seen_list.index(current_video_id)
        except ValueError:
            found = False
            for i, vid in enumerate(seen_list):
                if vid.startswith(current_video_id[:20]):
                    current_index = i
                    found = True
                    break
            if not found:
                return None
        
        if current_index > 0:
            return seen_list[current_index - 1]
        return None
    except Exception as e:
        print(f"❌ Error getting previous video: {e}")
        return None

async def has_previous_video_direct(user_id, current_video_id):
    """Check if previous video exists in history"""
    try:
        history = await db.historys.find_one({"user_id": user_id})
        if not history:
            return False
        
        seen_list = history.get("seen", [])
        if len(seen_list) < 2:
            return False
        
        try:
            current_index = seen_list.index(current_video_id)
            return current_index > 0
        except ValueError:
            for i, vid in enumerate(seen_list):
                if vid.startswith(current_video_id[:20]):
                    return i > 0
            return False
    except Exception as e:
        print(f"Error checking previous video: {e}")
        return False
