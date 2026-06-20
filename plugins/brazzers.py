import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import PREMIUM_DAILY_LIMIT, FSUB
from utils import is_user_joined
from plugins.ban_manager import ban_manager 
from plugins.get_video import send_video_with_controls


@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    """Handle /brazzers command"""
    await process_brazzers_request(client, m)


# 🔴 FUNCTION KO EXPORT KARO (async def se pehle)
async def process_brazzers_request(client, m: Message):
    """Core function to process Brazzers request"""
    
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
            await m.reply(f"⚠️ Daily limit reached! {PREMIUM_DAILY_LIMIT}/day")
            return
        
        # Get brazzers video
        video_id = await db.get_unseen_brazzers(user_id)
        if not video_id:
            video_id = await db.get_random_brazzers_video()
        
        if not video_id:
            await m.reply("❌ No videos found!")
            return

        # Send video with controls (category = brazzers)
        await send_video_with_controls(client, m, video_id, category="brazzers")
        await db.increase_video_count(user_id, username)

    except Exception as e:
        print(f"Error in brazzers: {e}")
        await m.reply("❌ Something went wrong!")
