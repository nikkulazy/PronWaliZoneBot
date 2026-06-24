import asyncio
from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
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
    # SEND VIDEO WITH SIRF 2 BUTTONS (NEXT & PREVIOUS)
    # ------------------------------------------------
    try:
        # Add to history BEFORE sending (for previous button)
        await db.add_to_history(user_id, video_id, video_id, "video")
        
        # Check if previous video exists
        prev_exists = await db.get_previous_video(user_id, video_id, "video")
        
        # SIRF 2 BUTTONS - Previous & Next
        row1 = []
        if prev_exists:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_video_{video_id}"))
        else:
            row1.append(InlineKeyboardButton("⏪ No History", callback_data="no_history"))
        
        row1.append(InlineKeyboardButton("⏩ Next", callback_data="next_video"))
        
        reply_markup = InlineKeyboardMarkup([row1])
        
        # Send video
        sent = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                f"<blockquote>"
                f"ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                f"ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ "
                f"ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ."
                f"</blockquote>"
            ),
            reply_to_message_id=m.id,
            reply_markup=reply_markup
        )

        # Increase daily count
        await db.increase_video_count(user_id, username)

        # Auto delete
        asyncio.create_task(auto_delete_message(m, sent))

    except Exception as e:
        await m.reply(f"❌ Failed to send video: {str(e)}")


# =============================================
# 🆕 NEXT VIDEO CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^next_video$"))
async def next_video_callback(client, query: CallbackQuery):
    """Handle Next button click for video"""
    try:
        await query.answer("⏩ Loading next...", show_alert=False)
        
        # Delete current message
        try:
            await query.message.delete()
        except:
            pass
        
        # Call video handler for next video
        fake_msg = query.message
        fake_msg.from_user = query.from_user
        fake_msg.chat = query.message.chat
        await handle_video_request(client, fake_msg)
    except Exception as e:
        print(f"Next button error: {e}")
        await query.answer("❌ Error loading next", show_alert=True)


# =============================================
# 🆕 PREVIOUS VIDEO CALLBACK
# =============================================
@Client.on_callback_query(filters.regex(r"^prev_video_"))
async def previous_video_callback(client, query: CallbackQuery):
    """Handle Previous button click for video"""
    try:
        data = query.data.split("_")
        current_file_unique_id = data[2]  # prev_video_FILEID
        
        user_id = query.from_user.id
        
        await query.answer("⏪ Loading previous...", show_alert=False)
        
        # Get previous video from history
        prev_video = await db.get_previous_video(user_id, current_file_unique_id, "video")
        
        if not prev_video:
            await query.answer("❌ No previous video found!", show_alert=True)
            return
        
        # Delete current message
        try:
            await query.message.delete()
        except:
            pass
        
        # Send previous video with buttons
        video_id = prev_video["file_unique_id"]
        
        # Check if previous exists for this new video
        prev_exists = await db.get_previous_video(user_id, video_id, "video")
        
        # Create buttons (SIRF 2 BUTTONS)
        row1 = []
        if prev_exists:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_video_{video_id}"))
        else:
            row1.append(InlineKeyboardButton("⏪ No History", callback_data="no_history"))
        
        row1.append(InlineKeyboardButton("⏩ Next", callback_data="next_video"))
        reply_markup = InlineKeyboardMarkup([row1])
        
        # Send video
        await client.send_video(
            chat_id=query.message.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                f"<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.</blockquote>"
            ),
            reply_markup=reply_markup
        )
        
    except Exception as e:
        print(f"Previous button error: {e}")
        await query.answer("❌ Error loading previous", show_alert=True)
