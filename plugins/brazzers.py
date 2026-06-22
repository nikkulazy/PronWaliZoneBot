import asyncio
import string
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_db import db
from info import LOG_CHANNEL, PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    """Handle /brazzers command"""
    await process_brazzers_request(client, m, direction="next")

async def process_brazzers_request(client, m: Message, direction="next", video_short_id=None):
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
            # Quick reply for non-premium users
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
        
        # Get video based on direction
        if direction == "next":
            video_id = await db.get_unseen_brazzers(user_id)
        elif direction == "previous" and video_short_id:
            # Get full video ID from short ID
            full_video_id = await db.get_brazzers_by_short_id(video_short_id)
            if full_video_id:
                video_id = await db.get_previous_brazzers(user_id, full_video_id)
            else:
                video_id = None
        else:
            video_id = await db.get_unseen_brazzers(user_id)
            
        if not video_id:
            if direction == "next":
                await m.reply("❌ No unseen Brazzers videos found!")
            else:
                await m.reply("❌ No previous Brazzers video found!")
            return

        # Get current video ID for navigation
        current_video_id = video_id
        
        # Generate short ID for navigation
        short_id = await db.get_short_brazzers_id(video_id)
        
        # Check if previous video exists
        has_previous = await db.has_previous_brazzers(user_id, video_id)
        
        # Create navigation buttons for Brazzers
        nav_buttons = []
        if has_previous:
            # Get previous video's short ID
            prev_video = await db.get_previous_brazzers(user_id, video_id)
            if prev_video:
                prev_short_id = await db.get_short_brazzers_id(prev_video)
                nav_buttons.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_brz_{prev_short_id}"))
        nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="get_brazzers"))
        
        reply_markup = InlineKeyboardMarkup([
            nav_buttons,
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])

        # Send video with protection and navigation buttons
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
