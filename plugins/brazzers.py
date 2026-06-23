import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager
from plugins.video_session import video_session


@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    await process_brazzers_request(client, m)


async def process_brazzers_request(client, m: Message):
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
                "💎 Buy Subscription And Get 900+ Brazzers Videos Per Month.", 
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('• Purchase Subscription •', callback_data='get')
                ]])
            )
            return

        used_today = await db.get_video_count(user_id)
        if used_today >= PREMIUM_DAILY_LIMIT:
            await m.reply(f"⚠️ Limit reached: {PREMIUM_DAILY_LIMIT} files.")
            return
        
        # GET VIDEO
        video_id = None
        
        # Check if user clicked "Previous"
        if hasattr(m, 'get_previous') and m.get_previous:
            video_id = video_session.get_previous(user_id)
        
        # If no previous, get new video
        if not video_id:
            video_id = await db.get_unseen_brazzers(user_id)

        if not video_id:
            await m.reply("❌ No unseen Brazzers videos found!")
            return

        # Save current video in session
        video_session.set_current(user_id, video_id)

        # Create buttons
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏪ Previous", callback_data="prev_brazzers"),
                InlineKeyboardButton("⏩ Next", callback_data="next_brazzers")
            ]
        ])

        dlt = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n<blockquote>This file will auto delete after 10 minutes.</blockquote>",
            reply_to_message_id=m.id,
            reply_markup=reply_markup
        )
        
        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, dlt))

    except Exception as e:
        print(f"Brazzers Error: {e}")
        await m.reply(f"❌ Error: {str(e)}")


# NEXT BRAZZERS
@Client.on_callback_query(filters.regex("next_brazzers"))
async def next_brazzers(client, query):
    await query.answer("⏳ Loading...", show_alert=False)
    
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    fake_msg.get_previous = False
    
    await process_brazzers_request(client, fake_msg)


# PREVIOUS BRAZZERS
@Client.on_callback_query(filters.regex("prev_brazzers"))
async def previous_brazzers(client, query):
    user_id = query.from_user.id
    
    prev_video = video_session.get_previous(user_id)
    
    if not prev_video:
        await query.answer("❌ No previous video found!", show_alert=True)
        return
    
    await query.answer("⏳ Loading previous...", show_alert=False)
    
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    fake_msg.get_previous = True
    
    await process_brazzers_request(client, fake_msg)
