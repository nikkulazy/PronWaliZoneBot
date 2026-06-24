import asyncio
import string
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_db import db
from info import LOG_CHANNEL, PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined, get_video_with_buttons
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    """Handle /brazzers command"""
    await process_brazzers_request(client, m)

async def process_brazzers_request(client, m: Message):
    """Core function to process Brazzers request - with Previous/Next buttons"""
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
        
        video_id = await db.get_unseen_brazzers(user_id)
        if not video_id:
            await m.reply("❌ No unseen videos found!")
            return

        # Send with Previous/Next buttons
        video_data = {
            "file_unique_id": video_id,
            "file_id": video_id,
            "media_type": "brazzers"
        }
        
        await get_video_with_buttons(
            client=client,
            message=m,
            user_id=user_id,
            video_data=video_data,
            media_type="brazzers",
            is_next=True
        )

    except Exception as e:
        print(f"Error in process_brazzers_request: {e}")


# =============================================
# 🆕 NEXT BRAZZERS CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^next_brazzers$"))
async def next_brazzers_callback(client, query: CallbackQuery):
    """Handle Next button click for brazzers"""
    user_id = query.from_user.id
    
    # Delete current message
    try:
        await query.message.delete()
    except:
        pass
    
    # Call brazzers handler
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    await process_brazzers_request(client, fake_msg)
    
    await query.answer("⏩ Loading next Brazzers...")


# =============================================
# 🆕 PREVIOUS BRAZZERS CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^prev_brazzers_"))
async def previous_brazzers_callback(client, query: CallbackQuery):
    """Handle Previous button click for brazzers"""
    data = query.data.split("_")
    current_file_unique_id = data[2]  # prev_brazzers_FILEID
    
    user_id = query.from_user.id
    
    # Get previous video from history
    prev_video = await db.get_previous_video(user_id, current_file_unique_id, "brazzers")
    
    if not prev_video:
        await query.answer("❌ No previous Brazzers found!", show_alert=True)
        return
    
    # Send previous video
    await get_video_with_buttons(
        client=client,
        message=query.message,
        user_id=user_id,
        video_data=prev_video,
        media_type="brazzers",
        is_next=False
    )
    
    # Delete current message (old video)
    try:
        await query.message.delete()
    except:
        pass
    
    await query.answer("⏪ Loading previous Brazzers...")
