import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import LOG_CHANNEL, PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    """Handle /brazzers command"""
    await process_brazzers_request(client, m, direction="next")

async def process_brazzers_request(client, m: Message, direction="next", current_video_id=None):
    """Core function to process Brazzers request with navigation"""
    if not m.from_user:
        return
    
    if FSUB and not await is_user_joined(client, m):
        return
    
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    if await ban_manager.check_ban(client, m):
        return

    try:
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            await m.reply(
                "💎 𝖡𝗎𝗒 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 𝖠𝗇𝖽 𝖦𝖾𝗍 900+ 𝖡𝖺𝗋𝗓𝗓𝖾𝗋𝗌 𝖵𝗂𝖽𝖾𝗈 𝖯𝖾𝗋 𝖬𝗈𝗇𝗍𝗁.", 
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •', callback_data='get')
                ]])
            )
            return

        used_today = await db.get_video_count(user_id)
        if used_today >= PREMIUM_DAILY_LIMIT:
            await m.reply(f"⚠️ 𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖣𝖺𝗂𝗅𝗒 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {PREMIUM_DAILY_LIMIT} 𝖥𝗂𝗅𝖾𝗌. 𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐")
            return
        
        # GET BRAZZERS VIDEO
        video_id = None
        
        if direction == "next":
            video_id = await get_unseen_brazzers_direct(user_id)
        elif direction == "previous" and current_video_id:
            video_id = await get_previous_brazzers_direct(user_id, current_video_id)
            if not video_id:
                await m.reply("❌ No previous Brazzers video found! Watch some videos first.")
                return
        else:
            video_id = await get_unseen_brazzers_direct(user_id)
            
        if not video_id:
            await m.reply("❌ No unseen Brazzers videos found!")
            return

        # SEND VIDEO WITH BUTTONS
        has_previous = await has_previous_brazzers_direct(user_id, video_id)
        
        nav_buttons = []
        if has_previous:
            prev_video = await get_previous_brazzers_direct(user_id, video_id)
            if prev_video:
                nav_buttons.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_brz_{prev_video}"))
        
        nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="get_brazzers"))
        
        reply_markup = InlineKeyboardMarkup([
            nav_buttons,
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])

        dlt = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ. ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>",
            reply_to_message_id=m.id,
            reply_markup=reply_markup
        )
        
        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, dlt))

    except Exception as e:
        print(f"Error in process_brazzers_request: {e}")


# ============================================================
# DIRECT DATABASE FUNCTIONS FOR BRAZZERS
# ============================================================

async def get_unseen_brazzers_direct(user_id):
    """Get unseen Brazzers video and save to history"""
    try:
        history = await db.braz_history.find_one({"user_id": user_id})
        seen_ids = history.get("seen", []) if history else []
        
        all_videos = []
        cursor = db.brazzers.find({})
        async for video in cursor:
            if video["file_id"] not in seen_ids:
                all_videos.append(video["file_id"])
        
        if not all_videos:
            return None
        
        video_id = random.choice(all_videos)
        await mark_brazzers_seen_direct(user_id, video_id)
        return video_id
    except Exception as e:
        print(f"❌ Error in get_unseen_brazzers_direct: {e}")
        return None

async def mark_brazzers_seen_direct(user_id, file_id):
    """Directly mark Brazzers video as seen in history"""
    try:
        history = await db.braz_history.find_one({"user_id": user_id})
        
        if history:
            seen_list = history.get("seen", [])
            if file_id not in seen_list:
                seen_list.append(file_id)
                await db.braz_history.update_one(
                    {"user_id": user_id},
                    {"$set": {"seen": seen_list}}
                )
        else:
            await db.braz_history.insert_one({
                "user_id": user_id,
                "seen": [file_id]
            })
    except Exception as e:
        print(f"❌ Error marking Brazzers seen: {e}")

async def get_previous_brazzers_direct(user_id, current_video_id):
    """Get previous Brazzers video from user's history"""
    try:
        history = await db.braz_history.find_one({"user_id": user_id})
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
        print(f"❌ Error getting previous Brazzers: {e}")
        return None

async def has_previous_brazzers_direct(user_id, current_video_id):
    """Check if previous Brazzers video exists in history"""
    try:
        history = await db.braz_history.find_one({"user_id": user_id})
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
        print(f"Error checking previous Brazzers: {e}")
        return False
