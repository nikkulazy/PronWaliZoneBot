# get_video.py - modified

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
    temp.USER_LAST_VIDEO[user_id] = {
        "file_id": video_id,
        "is_brazzers": False
    }

    # ---------- SEND VIDEO WITH NEXT + PREVIOUS BUTTONS ----------
    await send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False)


# ---------- SEND VIDEO FUNCTION (Common for both) ----------
async def send_video_with_buttons(client, m, user_id, video_id, is_brazzers=False):
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    # Get current video history
    last_data = temp.USER_LAST_VIDEO.get(user_id, {})
    prev_file_id = last_data.get("file_id") if not is_brazzers else None
    has_prev = prev_file_id is not None and prev_file_id != video_id

    # Build Buttons
    buttons = []
    row = []
    
    if has_prev:
        row.append(InlineKeyboardButton("⏪ Previous", callback_data="prev_video"))
    row.append(InlineKeyboardButton("⏩ Next", callback_data="next_video"))
    buttons.append(row)
    
    # Optional: Extra button for Brazzers
    if is_brazzers:
        buttons.append([InlineKeyboardButton("🔞 More Brazzers", callback_data="get_brazzers")])
    else:
        buttons.append([InlineKeyboardButton("🎬 Next Video", callback_data="get_video")])

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

    # Increase count only for NEXT (not for previous)
    if not is_brazzers:
        await db.increase_video_count(user_id, username)

    asyncio.create_task(auto_delete_message(m, sent))


# ---------- CALLBACK HANDLER FOR NEXT / PREVIOUS ----------
@Client.on_callback_query(filters.regex(r"^(next_video|prev_video)$"))
async def video_navigation_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    action = query.data
    message = query.message

    # Get current video data
    last_data = temp.USER_LAST_VIDEO.get(user_id, {})
    current_file_id = last_data.get("file_id")

    if not current_file_id:
        await query.answer("❌ No video found. Try /getvideo again.", show_alert=True)
        return

    # ---------- PREVIOUS BUTTON ----------
    if action == "prev_video":
        # Previous video = same file_id (dubara bhejo)
        await query.answer("⏪ Sending previous video...", show_alert=False)
        
        # Delete old message
        try:
            await message.delete()
        except:
            pass

        # Resend same video with buttons
        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        await send_video_with_buttons(
            client, 
            fake_msg, 
            user_id, 
            current_file_id,
            is_brazzers=last_data.get("is_brazzers", False)
        )
        return

    # ---------- NEXT BUTTON ----------
    if action == "next_video":
        await query.answer("⏩ Loading next video...", show_alert=False)
        
        # Delete old message
        try:
            await message.delete()
        except:
            pass

        # Mark current as seen (only for next)
        if last_data.get("is_brazzers", False):
            await db.mark_brazzers_seen(user_id, current_file_id)
        else:
            await db.mark_seen(user_id, current_file_id)

        # Get new video
        if last_data.get("is_brazzers", False):
            new_video = await db.get_unseen_brazzers(user_id)
            if not new_video:
                await query.message.reply("❌ No more unseen videos!")
                return
        else:
            new_video = await db.get_unseen_video(user_id)
            if not new_video:
                new_video = await db.get_random_video()
            if not new_video:
                await query.message.reply("❌ No more videos!")
                return

        # Update last video
        temp.USER_LAST_VIDEO[user_id] = {
            "file_id": new_video,
            "is_brazzers": last_data.get("is_brazzers", False)
        }

        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        await send_video_with_buttons(
            client,
            fake_msg,
            user_id,
            new_video,
            is_brazzers=last_data.get("is_brazzers", False)
        )
