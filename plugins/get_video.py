from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined

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

    # ✅ Premium + limit info - FIXED
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
    # ✅ LIMIT CHECK - FIXED
    # ------------------------------------------------
    
    # Premium User Logic
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(
                f"❌ You've reached your Premium limit of {PREMIUM_DAILY_LIMIT} files.\n"
                f"⏳ Try again tomorrow!"
            )
    else:
        # ✅ Free/Verified users - Check their respective limits
        if used >= current_limit:
            if is_verified:
                # Verified user reached limit
                return await m.reply(
                    f"❌ You've reached your daily limit of {current_limit} files.\n"
                    f"💎 Buy premium for more access!\n\n"
                    f"⏳ Resets tomorrow."
                )
            else:
                # Free user - Check if verification can help
                if IS_VERIFY:
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    # After verification, re-check limits
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
    # SEND VIDEO WITH NEXT BUTTON
    # ------------------------------------------------
    try:
        # Create Next button
        reply_markup = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⏪ Previous", callback_data="prev_video"),
        InlineKeyboardButton("⏩ Next", callback_data="next_video")
    ]
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
            reply_markup=reply_markup  # Added Next button
        )

        # Increase daily count ONLY after successful send
        await db.increase_video_count(user_id, username)

        # Auto delete in background
        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        await m.reply(f"❌ Failed to send video: {str(e)}")
