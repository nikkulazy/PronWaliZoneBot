from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined


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

    # ---------- GET VIDEO ----------
    video_id = await db.get_unseen_video(user_id)
    if not video_id:
        video_id = await db.get_random_video()
    if not video_id:
        return await m.reply("❌ No videos found.")

    # ---------- STORE LAST VIDEO FOR PREVIOUS BUTTON ----------
    temp.USER_LAST_VIDEO[user_id] = video_id  # Store single last video

    # ---------- SEND VIDEO WITH NEXT + PREVIOUS BUTTONS ----------
    await send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False)


# ---------- SEND VIDEO FUNCTION (Common for both getvideo & brazzers) ----------
async def send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False):
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    # Check if previous video exists
    prev_video = temp.USER_LAST_VIDEO.get(user_id)
    has_prev = prev_video is not None and prev_video != video_id

    # Build Buttons - Previous + Next in same row
    buttons = []
    row = []
    
    if has_prev:
        row.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{'brazzers' if is_brazzers else 'video'}"))
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

    # Increase count only for new videos (not for previous)
    if not is_brazzers:
        await db.increase_video_count(user_id, username)

    asyncio.create_task(auto_delete_message(m, sent))


# ---------- CALLBACK HANDLER FOR NEXT / PREVIOUS ----------
@Client.on_callback_query(filters.regex(r"^(next_|prev_)"))
async def video_navigation_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    message = query.message
    
    # Parse callback data: next_video, prev_video, next_brazzers, prev_brazzers
    action, video_type = data.split("_")
    is_brazzers = video_type == "brazzers"

    # Get current video from message (we need to track it)
    # We'll store current video ID in temp
    current_video = temp.USER_LAST_VIDEO.get(user_id)
    
    if not current_video:
        await query.answer("❌ No video found. Try again!", show_alert=True)
        return

    # ---------- PREVIOUS BUTTON ----------
    if action == "prev":
        await query.answer("⏪ Sending previous video...", show_alert=False)
        
        # Delete old message
        try:
            await message.delete()
        except:
            pass

        # Resend same video (previous = current video)
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        # Don't increase count for previous
        await send_video_with_buttons(
            client, 
            fake_msg, 
            user_id, 
            current_video,
            is_brazzers=is_brazzers
        )
        return

    # ---------- NEXT BUTTON ----------
    if action == "next":
        await query.answer("⏩ Loading next video...", show_alert=False)
        
        # Delete old message
        try:
            await message.delete()
        except:
            pass

        # Mark current as seen (only for next)
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

        # Update last video for previous button
        temp.USER_LAST_VIDEO[user_id] = new_video

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
