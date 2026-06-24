import asyncio
from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined, get_video_with_buttons


@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):

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

    # ✅ Premium + limit info
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

    # ------------------------------------------------
    # ✅ LIMIT CHECK
    # ------------------------------------------------
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

    # ------------------------------------------------
    # GET VIDEO
    # ------------------------------------------------
    video_id = await db.get_unseen_video(user_id)

    if not video_id:
        try:
            video_id = await db.get_random_video()
        except Exception as e:
            print(f"[Random Video Error] {e}")
            return

    if not video_id:
        return await m.reply("❌ No videos found in the database.")

    # ------------------------------------------------
    # SEND VIDEO WITH PREVIOUS/NEXT BUTTONS
    # ------------------------------------------------
    video_data = {
        "file_unique_id": video_id,
        "file_id": video_id,
        "media_type": "video"
    }
    
    await get_video_with_buttons(
        client=client,
        message=m,
        user_id=user_id,
        video_data=video_data,
        media_type="video",
        is_next=True
    )


# =============================================
# 🆕 NEXT VIDEO CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^next_video$"))
async def next_video_callback(client, query: CallbackQuery):
    """Handle Next button click for video"""
    user_id = query.from_user.id
    
    # Delete current message
    try:
        await query.message.delete()
    except:
        pass
    
    # Call video handler
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    await handle_video_request(client, fake_msg)
    
    await query.answer("⏩ Loading next video...")


# =============================================
# 🆕 PREVIOUS VIDEO CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^prev_video_"))
async def previous_video_callback(client, query: CallbackQuery):
    """Handle Previous button click for video"""
    data = query.data.split("_")
    current_file_unique_id = data[2]  # prev_video_FILEID
    
    user_id = query.from_user.id
    
    # Get previous video from history
    prev_video = await db.get_previous_video(user_id, current_file_unique_id, "video")
    
    if not prev_video:
        await query.answer("❌ No previous video found!", show_alert=True)
        return
    
    # Send previous video
    await get_video_with_buttons(
        client=client,
        message=query.message,
        user_id=user_id,
        video_data=prev_video,
        media_type="video",
        is_next=False
    )
    
    # Delete current message (old video)
    try:
        await query.message.delete()
    except:
        pass
    
    await query.answer("⏪ Loading previous video...")


# =============================================
# 🆕 NO HISTORY CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^no_history$"))
async def no_history_callback(client, query: CallbackQuery):
    """Handle No History button click"""
    await query.answer("❌ No previous video in history!", show_alert=True)
