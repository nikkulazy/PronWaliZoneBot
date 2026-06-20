import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined


# =================================================
# SEND VIDEO WITH REACTION BUTTONS
# =================================================
async def send_video_with_controls(client, message, video_id, category="main"):
    """
    Send video with Like, Dislike, Previous, Next buttons
    """
    user_id = message.from_user.id
    
    # 🔴 FIX: Safely get reactions
    reactions = await db.get_video_reactions(video_id)
    if reactions is None:
        reactions = {"likes": 0, "dislikes": 0}
    likes = reactions.get('likes', 0)
    dislikes = reactions.get('dislikes', 0)
    
    # Check if user already reacted
    user_reaction = await db.get_user_reaction(user_id, video_id)
    
    # Build buttons
    like_text = f"❤️ {likes}" if likes > 0 else "❤️"
    dislike_text = f"👎 {dislikes}" if dislikes > 0 else "👎"
    
    if user_reaction == 'like':
        like_text = f"❤️‍🔥 {likes}"
    elif user_reaction == 'dislike':
        dislike_text = f"👎💢 {dislikes}"
    
    # 🔴 FIX: Safely get history count (Default 0 if None)
    history_count = await db.get_user_history_count(user_id, category)
    if history_count is None:
        history_count = 0
    prev_disabled = history_count < 1
    
    prev_text = "⏮️" if not prev_disabled else "⏮️🚫"
    prev_callback = f"prev_{video_id}_{category}" if not prev_disabled else "no_history"
    
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0
    limit_reached = used >= current_limit
    
    next_text = "🔒" if limit_reached else "⏭️"
    next_callback = "limit_reached" if limit_reached else f"next_{video_id}_{category}"
    
    buttons = [
        [
            InlineKeyboardButton(like_text, callback_data=f"like_{video_id}"),
            InlineKeyboardButton(dislike_text, callback_data=f"dislike_{video_id}")
        ],
        [
            InlineKeyboardButton(prev_text, callback_data=prev_callback),
            InlineKeyboardButton(next_text, callback_data=next_callback)
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_data")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    extra_info = ""
    if limit_reached:
        extra_info = f"\n\n⚠️ Daily limit reached ({used}/{current_limit})"
    
    # Send video
    try:
        sent = await client.send_video(
            chat_id=message.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                f"<blockquote>"
                f"❤️ Likes: {likes} | 👎 Dislikes: {dislikes}\n"
                f"📁 Category: {'🔞 Brazzers' if category == 'brazzers' else '🎬 Main'}\n"
                f"📊 Used: {used}/{current_limit}\n"
                f"📜 History: {history_count} videos{extra_info}\n\n"
                f"ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                f"ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ "
                f"ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ."
                f"</blockquote>"
            ),
            reply_to_message_id=message.id,
            reply_markup=reply_markup
        )
        
        # 🔴 FIX: Save to history
        await db.add_to_user_history(user_id, video_id, category)
        
        # Auto delete
        asyncio.create_task(auto_delete_message(message, sent))
        return sent
        
    except Exception as e:
        await message.reply(f"❌ Failed to send video: {str(e)}")
        return None


# =================================================
# MAIN VIDEO REQUEST HANDLER
# =================================================
@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):
    """Handle video request"""
    
    if not m.from_user:
        return
    
    if FSUB and not await is_user_joined(client, m):
        return
    
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    if await ban_manager.check_ban(client, m):
        return
    
    # Check limits
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0
    
    # Premium User Logic
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(f"❌ Premium limit reached! {PREMIUM_DAILY_LIMIT}/day")
    else:
        if used >= current_limit:
            if is_verified:
                return await m.reply(f"❌ Daily limit reached! {current_limit}/day")
            else:
                if IS_VERIFY:
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    used = await db.get_video_count(user_id) or 0
                    if used >= VERIFICATION_DAILY_LIMIT:
                        return await m.reply(f"❌ Limit reached! {VERIFICATION_DAILY_LIMIT}/day")
                else:
                    return await m.reply(
                        f"❌ Daily limit reached! {current_limit}/day\n💎 Buy premium for more!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")]
                        ])
                    )
    
    # Get video
    video_id = await db.get_unseen_video(user_id)
    if not video_id:
        video_id = await db.get_random_video()
    
    if not video_id:
        return await m.reply("❌ No videos found!")
    
    # Send video
    await send_video_with_controls(client, m, video_id, category="main")
    await db.increase_video_count(user_id, username)


# =================================================
# CALLBACK HANDLER
# =================================================
@Client.on_callback_query()
async def video_callback_handler(client, query: CallbackQuery):
    """Handle all video callbacks"""
    
    data = query.data
    user_id = query.from_user.id
    message = query.message
    
    # Close
    if data == "close_data":
        await message.delete()
        return
    
    # No history
    if data == "no_history":
        await query.answer("❌ No history found! Watch some videos first.", show_alert=True)
        return
    
    # Limit reached
    if data == "limit_reached":
        await query.answer("❌ Daily limit reached! Try tomorrow.", show_alert=True)
        return
    
    # =============================================
    # LIKE / DISLIKE
    # =============================================
    
    if data.startswith("like_"):
        video_id = data.replace("like_", "")
        
        current = await db.get_user_reaction(user_id, video_id)
        
        if current == 'like':
            await db.remove_reaction(user_id, video_id, 'like')
            await query.answer("❤️ Removed like")
        else:
            await db.add_reaction(user_id, video_id, 'like')
            if current == 'dislike':
                await db.remove_reaction(user_id, video_id, 'dislike')
            await query.answer("❤️ Liked!")
        
        await update_reaction_buttons(client, query, video_id)
        return
    
    if data.startswith("dislike_"):
        video_id = data.replace("dislike_", "")
        
        current = await db.get_user_reaction(user_id, video_id)
        
        if current == 'dislike':
            await db.remove_reaction(user_id, video_id, 'dislike')
            await query.answer("👎 Removed dislike")
        else:
            await db.add_reaction(user_id, video_id, 'dislike')
            if current == 'like':
                await db.remove_reaction(user_id, video_id, 'like')
            await query.answer("👎 Disliked!")
        
        await update_reaction_buttons(client, query, video_id)
        return
    
    # =============================================
    # PREVIOUS BUTTON
    # =============================================
    
    if data.startswith("prev_"):
        parts = data.split("_")
        current_video_id = parts[1]
        category = parts[2] if len(parts) > 2 else "main"
        
        # Get previous video from history
        previous_video = await db.get_previous_video(user_id, current_video_id, category)
        
        if not previous_video:
            await query.answer("❌ No previous video found!", show_alert=True)
            return
        
        # Delete old video
        await message.delete()
        
        # Send previous video
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        
        await send_video_with_controls(client, fake_msg, previous_video, category=category)
        await query.answer("⏮️ Previous video")
        return
    
    # =============================================
    # NEXT BUTTON - Same as /getvideo
    # =============================================
    
    if data.startswith("next_"):
        parts = data.split("_")
        current_video_id = parts[1]
        category = parts[2] if len(parts) > 2 else "main"
        
        # Check limits again
        is_premium = await db.has_premium_access(user_id)
        is_verified = await db.is_user_verified(user_id)
        
        if is_premium:
            current_limit = PREMIUM_DAILY_LIMIT
        elif is_verified:
            current_limit = VERIFICATION_DAILY_LIMIT
        else:
            current_limit = DAILY_LIMIT
        
        used = await db.get_video_count(user_id) or 0
        
        if used >= current_limit:
            await query.answer(f"❌ Limit reached! {used}/{current_limit}", show_alert=True)
            return
        
        # Get next video (same as getvideo)
        video_id = await db.get_unseen_video(user_id)
        if not video_id:
            video_id = await db.get_random_video()
        
        if not video_id:
            await query.answer("❌ No more videos!", show_alert=True)
            return
        
        # Delete old video
        await message.delete()
        
        # Send new video
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat
        
        await send_video_with_controls(client, fake_msg, video_id, category)
        
        # Increase count
        username = query.from_user.username or query.from_user.first_name or "Unknown"
        await db.increase_video_count(user_id, username)
        
        await query.answer("⏭️ Next video")


# =================================================
# UPDATE REACTION BUTTONS ONLY
# =================================================
async def update_reaction_buttons(client, query, video_id):
    """Update only like/dislike buttons"""
    
    reactions = await db.get_video_reactions(video_id)
    if reactions is None:
        reactions = {"likes": 0, "dislikes": 0}
    likes = reactions.get('likes', 0)
    dislikes = reactions.get('dislikes', 0)
    
    user_reaction = await db.get_user_reaction(query.from_user.id, video_id)
    
    like_text = f"❤️ {likes}" if likes > 0 else "❤️"
    dislike_text = f"👎 {dislikes}" if dislikes > 0 else "👎"
    
    if user_reaction == 'like':
        like_text = f"❤️‍🔥 {likes}"
    elif user_reaction == 'dislike':
        dislike_text = f"👎💢 {dislikes}"
    
    # Get category and current video
    category = "main"
    current_video = video_id
    
    if query.message.reply_markup:
        for row in query.message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("next_"):
                    parts = btn.callback_data.split("_")
                    if len(parts) > 2:
                        category = parts[2]
                    break
    
    # 🔴 FIX: Safely get history count
    user_id = query.from_user.id
    history_count = await db.get_user_history_count(user_id, category)
    if history_count is None:
        history_count = 0
    prev_disabled = history_count < 1
    
    prev_text = "⏮️" if not prev_disabled else "⏮️🚫"
    prev_callback = f"prev_{current_video}_{category}" if not prev_disabled else "no_history"
    
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0
    limit_reached = used >= current_limit
    
    next_text = "🔒" if limit_reached else "⏭️"
    next_callback = "limit_reached" if limit_reached else f"next_{current_video}_{category}"
    
    buttons = [
        [
            InlineKeyboardButton(like_text, callback_data=f"like_{video_id}"),
            InlineKeyboardButton(dislike_text, callback_data=f"dislike_{video_id}")
        ],
        [
            InlineKeyboardButton(prev_text, callback_data=prev_callback),
            InlineKeyboardButton(next_text, callback_data=next_callback)
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_data")
        ]
    ]
    
    await query.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )
