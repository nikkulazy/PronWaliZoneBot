from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from plugins.video_session import video_session
from utils import temp, auto_delete_message, is_user_joined


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

    # Premium + limit check
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
    else:
        current_limit = DAILY_LIMIT
    
    used = await db.get_video_count(user_id) or 0

    # Limit Check
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(f"❌ Premium limit reached: {PREMIUM_DAILY_LIMIT} files.")
    else:
        if used >= current_limit:
            if is_verified:
                return await m.reply(f"❌ Daily limit reached: {current_limit} files.")
            else:
                if IS_VERIFY:
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    used = await db.get_video_count(user_id) or 0
                    if used >= VERIFICATION_DAILY_LIMIT:
                        return await m.reply(f"❌ Verified limit reached: {VERIFICATION_DAILY_LIMIT} files.")
                else:
                    return await m.reply(
                        f"❌ Daily limit reached: {current_limit} files.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")]
                        ])
                    )

    # GET VIDEO
    video_id = None
    
    # Check if user clicked "Previous"
    if hasattr(m, 'get_previous') and m.get_previous:
        video_id = video_session.get_previous(user_id)
    
    # If no previous, get new video
    if not video_id:
        video_id = await db.get_unseen_video(user_id)
        if not video_id:
            video_id = await db.get_random_video()

    if not video_id:
        return await m.reply("❌ No videos found.")

    # SEND VIDEO
    try:
        # Save current video in session
        video_session.set_current(user_id, video_id)
        
        # Create buttons
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
            reply_markup=reply_markup
        )

        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        await m.reply(f"❌ Error: {str(e)}")


# NEXT VIDEO HANDLER
@Client.on_callback_query(filters.regex("next_video"))
async def get_video_callback(client, query):
    await query.answer("⏳ Loading...", show_alert=False)
    
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    fake_msg.get_previous = False
    
    await handle_video_request(client, fake_msg)


# PREVIOUS VIDEO HANDLER
@Client.on_callback_query(filters.regex("prev_video"))
async def previous_video(client, query):
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
    
    await handle_video_request(client, fake_msg)
