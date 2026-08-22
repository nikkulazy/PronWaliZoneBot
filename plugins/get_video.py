import asyncio
import pytz
import uuid
import random
import string
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database.users_db import db
from info import (
    PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT,
    FSUB, IS_VERIFY, TIMEZONE, WEB_APP_URL, FREE_VIDEO_DURATION,
    VERIFY_START_IMG, TUTORIAL_LINK
)
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined, get_shortlink_av


# ---------- TEMP DOWNLOAD CACHE ----------
DOWNLOAD_CACHE = {}

# ---------- INITIALIZE USER HISTORY ----------
def init_user_history(user_id, is_brazzers=False):
    if user_id not in temp.USER_VIDEO_HISTORY:
        temp.USER_VIDEO_HISTORY[user_id] = {
            "history": [],
            "current_index": -1,
            "is_brazzers": is_brazzers
        }


# ---------- HELPER FUNCTION ----------
def get_ist_today():
    return datetime.now(pytz.timezone(TIMEZONE)).date()


# ---------- CHECK USER DURATION LIMIT ----------
async def check_user_duration_limit(user_id, video_duration):
    """Check if user can watch this video based on duration"""
    if await db.has_premium_access(user_id):
        return True, "Unlimited", None
    
    if video_duration <= 0:
        return False, 0, FREE_VIDEO_DURATION
    
    user = await db.get_user(user_id)
    user_duration_limit = user.get("duration_limit", FREE_VIDEO_DURATION)
    
    if video_duration <= user_duration_limit:
        remaining = user_duration_limit - video_duration
        return True, remaining, user_duration_limit
    
    return False, user_duration_limit, user_duration_limit


# ---------- CHECK LIMIT FUNCTION ----------
async def check_user_limit(user_id):
    is_premium = await db.has_premium_access(user_id)
    is_verified = await db.is_user_verified(user_id)
    
    if is_premium:
        current_limit = PREMIUM_DAILY_LIMIT
        user_type = "premium"
    elif is_verified:
        current_limit = VERIFICATION_DAILY_LIMIT
        user_type = "verified"
    else:
        current_limit = DAILY_LIMIT
        user_type = "normal"
    
    used = await db.get_video_count(user_id) or 0
    
    user = await db.get_user(user_id)
    if user:
        last_date = user.get("last_date")
        today = get_ist_today()
        
        if last_date:
            if isinstance(last_date, datetime):
                if last_date.tzinfo is not None:
                    check_date = last_date.astimezone(pytz.timezone(TIMEZONE)).date()
                else:
                    check_date = last_date.date()
            else:
                check_date = None
                
            if check_date != today:
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"video_count": 0, "last_date": datetime.combine(today, datetime.min.time())}}
                )
                used = 0
    
    return {
        "used": used,
        "limit": current_limit,
        "is_premium": is_premium,
        "is_verified": is_verified,
        "user_type": user_type,
        "reached": used >= current_limit
    }


# ---------- SEND LIMIT MESSAGE ----------
async def send_limit_message(client, message_or_query, limit_data):
    """Send limit reached message with proper buttons"""
    used = limit_data["used"]
    limit = limit_data["limit"]
    user_type = limit_data["user_type"]
    
    # Get user_id from message or query
    if hasattr(message_or_query, 'from_user'):
        user_id = message_or_query.from_user.id
    else:
        user_id = message_or_query.chat.id if hasattr(message_or_query, 'chat') else None
    
    if not user_id:
        return
    
    # Get IST time and calculate reset time (tomorrow 12:00 AM IST)
    ist = pytz.timezone(TIMEZONE)
    now = datetime.now(ist)
    tomorrow = now + timedelta(days=1)
    reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    reset_str = reset_time.strftime("%I:%M %p")
    
    # Generate verify URL
    verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    await db.create_verify_id(user_id, verify_id, None)
    long_url = f"https://telegram.me/{temp.U_NAME}?start=avbotz_{user_id}_{verify_id}"
    
    try:
        verify_url = await get_shortlink_av(long_url) or long_url
    except:
        verify_url = long_url
    
    tutorial_url = TUTORIAL_LINK if TUTORIAL_LINK and TUTORIAL_LINK.startswith("http") else "https://t.me"
    
    # Build message with exact text format
    text = (
        f"🔞 **𝗬𝗼𝘂𝗿 𝗙𝗿𝗲𝗲 𝗟𝗶𝗺𝗶𝘁 𝗘𝘅𝗽𝗶𝗿𝗲𝗱**\n\n"
        f"⌛ 𝚈𝚘𝚞𝚛 𝙻𝚒𝚖𝚒𝚝 𝚁𝚎𝚜𝚝𝚊𝚛𝚝 𝚃𝚘𝚖𝚘𝚛𝚛𝚘𝚠 {reset_str} (𝙸𝚂𝚃)\n\n"
        f"💎 𝙶𝚎𝚝 𝚁𝚎𝚌𝚎𝚒𝚟𝚎𝚛 𝚂𝚞𝚋𝚜𝚌𝚛𝚒𝚙𝚝𝚒𝚘𝚗 𝙵𝚘𝚛 𝚄𝚗𝚕𝚒𝚖𝚒𝚝𝚎𝚍 𝙰𝚌𝚌𝚎𝚜𝚜\n\n"
        f"📌 Click Verify Button Access More Video In 1 minute\n\n"
        f"👇 **𝗖𝗵𝗼𝗼𝘀𝗲 𝗮𝗻 𝗢𝗽𝘁𝗶𝗼𝗻 !**"
    )
    
    buttons = [
        [InlineKeyboardButton("💎 Upgrade To Premium", callback_data="get_subscription")],
        [InlineKeyboardButton("⚠️ Verify ⚠️", url=verify_url)],
        [InlineKeyboardButton("❓ How to Verify ❓", url=tutorial_url)]
    ]
    
    # Check if it's a callback query or regular message
    if hasattr(message_or_query, 'answer'):  # It's a CallbackQuery
        try:
            # DELETE the old video message first
            try:
                await message_or_query.message.delete()
            except Exception as e:
                print(f"⚠️ Could not delete old message: {e}")
            
            # Send new photo message with buttons
            await message_or_query.message.reply_photo(
                photo=VERIFY_START_IMG,
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
            await message_or_query.answer("⏳ Limit reached! Verify or upgrade to continue.", show_alert=False)
            
        except Exception as e:
            print(f"❌ Error in callback send_limit_message: {e}")
            # Fallback: try to send as text
            try:
                await message_or_query.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=enums.ParseMode.HTML
                )
            except:
                pass
    
    else:  # It's a regular Message (from /getvideo command)
        try:
            await message_or_query.reply_photo(
                photo=VERIFY_START_IMG,
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        except:
            await message_or_query.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )


# ---------- ASYNC WAIT FUNCTION ----------
async def send_waiting_and_wait(message, delay=1):
    """Send waiting message, wait for it to delete, then return"""
    try:
        waiting_msg = await message.reply_text("⏳ **Please wait...**")
        await asyncio.sleep(delay)
        try:
            await waiting_msg.delete()
        except Exception:
            pass
        return True
    except Exception:
        return False


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

    limit_data = await check_user_limit(user_id)
    
    if limit_data["reached"]:
        if limit_data["is_premium"]:
            return await send_limit_message(client, m, limit_data)
        else:
            if limit_data["is_verified"]:
                return await send_limit_message(client, m, limit_data)
            else:
                if IS_VERIFY:
                    if not hasattr(m, 'command') or m.command is None:
                        m.command = []
                    
                    verified = await av_x_verification(client, m)
                    if not verified:
                        return
                    limit_data = await check_user_limit(user_id)
                    if limit_data["reached"]:
                        return await send_limit_message(client, m, limit_data)
                else:
                    return await send_limit_message(client, m, limit_data)

    # ---------- GET NEW VIDEO ----------
    result = await db.get_unseen_video(user_id)

    if isinstance(result, tuple) and len(result) == 2:
        video_id, duration = result
    else:
        video_id = result
        duration = 0

    if not video_id:
        random_result = await db.get_random_video(user_id)
        if isinstance(random_result, tuple) and len(random_result) == 2:
            video_id, duration = random_result
        else:
            video_id = random_result
            duration = 0
            
    if not video_id:
        return await m.reply("❌ No videos found.")
    
    if not await db.has_premium_access(user_id):
        if duration <= 0:
            random_result = await db.get_random_video(user_id)
            if isinstance(random_result, tuple) and len(random_result) == 2:
                video_id, duration = random_result
            else:
                video_id = random_result
                duration = 0
            
            if not video_id or duration <= 0:
                return await m.reply(
                    "❌ No valid videos found with proper duration.\n\n"
                    "💎 Buy premium to access all videos!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")],
                        [InlineKeyboardButton("✖️Close✖️", callback_data="close_data")]
                    ])
                )
    
    is_allowed, remaining, limit_value = await check_user_duration_limit(user_id, duration)
    
    if not is_allowed:
        await m.reply(
            f"❌ **Video Duration Limit Exceeded!**\n\n"
            f"⏱️ Video Duration: `{duration}s` ({duration//60}m {duration%60}s)\n"
            f"📊 Your Limit: `{limit_value}s` ({limit_value//60}m {limit_value%60}s)\n\n"
            f"💎 Upgrade to Premium for Unlimited Duration!\n"
            f"🔄 Contact admin to reset your limit using `/resetlimit`.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Buy Premium", callback_data="get_subscription")],
                [InlineKeyboardButton("✖️Close✖️", callback_data="close_data")]
            ])
        )
        return

    init_user_history(user_id, is_brazzers=False)
    
    if video_id not in temp.USER_VIDEO_HISTORY[user_id]["history"]:
        temp.USER_VIDEO_HISTORY[user_id]["history"].append(video_id)
        temp.USER_VIDEO_HISTORY[user_id]["current_index"] = len(temp.USER_VIDEO_HISTORY[user_id]["history"]) - 1

    await send_video_with_buttons(client, m, user_id, video_id, duration, is_brazzers=False)


# ---------- SEND VIDEO WITH SPOILER ----------
async def send_video_with_buttons(client, m, user_id, video_id, duration=0, is_brazzers=False):
    try:
        username = m.from_user.username or m.from_user.first_name or "Unknown"
        
        await db.increase_video_count(user_id, username)
        
        init_user_history(user_id, is_brazzers)
        
        history = temp.USER_VIDEO_HISTORY[user_id]
        current_idx = history["current_index"]
        
        video_label = "🔞 Brazzers" if is_brazzers else "🎬 Video"
        
        video_data = await db.videos.find_one({"file_id": video_id})
        is_premium_video = video_data.get("is_premium", False) if video_data else False
        
        limit_data = await check_user_limit(user_id)
        used = limit_data["used"]
        total_limit = limit_data["limit"]
        
        is_premium_user = await db.has_premium_access(user_id)
        
        caption = f"**{video_label}**\n\n"
        
        if is_premium_user:
            caption += f"📂 **File Limit:** {total_limit} Files (Premium)\n"
            caption += f"📉 **Used:** {used}/{total_limit}\n\n"
        else:
            caption += f"📂 **File Limit:** {total_limit} Files\n"
            caption += f"📉 **Used:** {used}/{total_limit}\n\n"
        
        caption += (
            f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
            "<blockquote>"
            "ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
            "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ "
            "ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ."
            "</blockquote>"
        )
        
        download_id = str(uuid.uuid4())[:8]
        
        DOWNLOAD_CACHE[download_id] = {
            "file_id": video_id,
            "video_type": "brazzers" if is_brazzers else "video",
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        buttons = []
        
        row1 = []
        if current_idx > 0:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{'brazzers' if is_brazzers else 'video'}"))
        else:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data="noop"))
        
        row1.append(InlineKeyboardButton("⏩ Next", callback_data=f"next_{'brazzers' if is_brazzers else 'video'}"))
        buttons.append(row1)
        
        row2 = [InlineKeyboardButton("📂 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 📂", callback_data=f"dld_{download_id}")]
        buttons.append(row2)
        
        row3 = [InlineKeyboardButton("✖️ Close ✖️", callback_data="close_data")]
        buttons.append(row3)

        reply_markup = InlineKeyboardMarkup(buttons)

        sent = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=caption,
            reply_to_message_id=m.id,
            reply_markup=reply_markup,
            has_spoiler=True
        )

        asyncio.create_task(auto_delete_message(m, sent))
        
    except Exception as e:
        print(f"❌ send_video_with_buttons error: {e}")
        import traceback
        traceback.print_exc()
        await m.reply("❌ Failed to send video. Please try again later!")


# ---------- DOWNLOAD CALLBACK HANDLER ----------
@Client.on_callback_query(filters.regex(r"^dld_"))
async def download_callback_handler(client, query: CallbackQuery):
    user_id = query.from_user.id
    
    try:
        download_id = query.data.replace("dld_", "")
        cache_data = DOWNLOAD_CACHE.get(download_id)
        
        if not cache_data:
            await query.answer("❌ Download link expired! Please get a new video.", show_alert=True)
            return
        
        if time.time() - cache_data.get("timestamp", 0) > 300:
            await query.answer("❌ Link expired! Please request a new video.", show_alert=True)
            return
        
        if cache_data["user_id"] != user_id:
            await query.answer("❌ This download link is not for you!", show_alert=True)
            return
        
        file_id = cache_data["file_id"]
        video_type = cache_data["video_type"]
        is_brazzers = video_type == "brazzers"
        
        is_premium = await db.has_premium_access(user_id)
        
        if not is_premium:
            await query.answer("💎 This feature is only for premium users!\n\nBUY PREMIUM AND ACCESS UNLIMITED INDIAN OR BRAZZERS VIDEO FULL ADMIN SUPPORT.", show_alert=True)
            return
        
        web_app_url = WEB_APP_URL.rstrip('/')
        if not web_app_url:
            await query.answer("❌ Server URL not configured!", show_alert=True)
            return
        
        download_url = f"{web_app_url}/d/{file_id}/{user_id}"
        
        print(f"🔗 New Download URL generated: {download_url}")
        
        new_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ 𝗙𝗮𝘀𝘁 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 ⚡", url=download_url)],
            [InlineKeyboardButton("* ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ *", callback_data=f"back_{'brazzers' if is_brazzers else 'video'}")]
        ])
        
        try:
            await query.message.edit_reply_markup(reply_markup=new_buttons)
            await query.answer("✅ Download link generated!", show_alert=False)
        except Exception as edit_error:
            print(f"⚠️ Edit error: {edit_error}")
            fallback_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ 𝗙𝗮𝘀𝘁 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 ⚡", url=download_url)],
                [InlineKeyboardButton("* ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ *", callback_data=f"back_{'brazzers' if is_brazzers else 'video'}")]
            ])
            
            sent_message = await query.message.reply(
                "✅ **Download Link Generated!**\n\n⬇️ Click below to download",
                reply_markup=fallback_buttons
            )
            
            async def delete_download_message():
                await asyncio.sleep(120)
                try:
                    await sent_message.delete()
                except Exception:
                    pass
            
            asyncio.create_task(delete_download_message())
            await query.answer("✅ Download link generated!", show_alert=False)
        
    except Exception as e:
        print(f"❌ Download handler error: {e}")
        import traceback
        traceback.print_exc()
        await query.answer(f"❌ Error: {str(e)[:50]}...", show_alert=True)


# ---------- BACK BUTTON HANDLER ----------
@Client.on_callback_query(filters.regex(r"^back_"))
async def back_callback_handler(client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        data = query.data
        video_type = data.replace("back_", "")
        is_brazzers = video_type == "brazzers"
        
        await query.answer("🔙 Loading...", show_alert=False)
        
        history_data = temp.USER_VIDEO_HISTORY.get(user_id)
        if not history_data or not history_data["history"]:
            await query.answer("❌ No history found!", show_alert=True)
            return
        
        current_idx = history_data["current_index"]
        if current_idx < 0 or current_idx >= len(history_data["history"]):
            await query.answer("❌ Invalid video!", show_alert=True)
            return
        
        video_id = history_data["history"][current_idx]
        
        video_data = await db.videos.find_one({"file_id": video_id})
        duration = video_data.get("duration", 0) if video_data else 0
        
        download_id = str(uuid.uuid4())[:8]
        DOWNLOAD_CACHE[download_id] = {
            "file_id": video_id,
            "video_type": "brazzers" if is_brazzers else "video",
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        buttons = []
        
        row1 = []
        if current_idx > 0:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data=f"prev_{'brazzers' if is_brazzers else 'video'}"))
        else:
            row1.append(InlineKeyboardButton("⏪ Previous", callback_data="noop"))
        
        row1.append(InlineKeyboardButton("⏩ Next", callback_data=f"next_{'brazzers' if is_brazzers else 'video'}"))
        buttons.append(row1)
        
        row2 = [InlineKeyboardButton("📥 Download", callback_data=f"dld_{download_id}")]
        buttons.append(row2)
        
        row3 = [InlineKeyboardButton("✖️ Close ✖️", callback_data="close_data")]
        buttons.append(row3)
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        await query.message.edit_reply_markup(reply_markup=reply_markup)
        
    except Exception as e:
        print(f"❌ Back button error: {e}")
        await query.answer("❌ Error loading previous buttons", show_alert=True)


# ---------- CALLBACK HANDLER FOR NEXT / PREVIOUS ----------
@Client.on_callback_query(filters.regex(r"^(next_|prev_|noop)"))
async def video_navigation_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    message = query.message
    
    # Send waiting message
    try:
        waiting_msg = await message.reply_text("⏳ **Please wait...**")
    except Exception:
        waiting_msg = None
    
    # Answer callback
    await query.answer()
    
    if data == "noop":
        await query.answer("⚠️ This is the first video!", show_alert=True)
        if waiting_msg:
            try:
                await waiting_msg.delete()
            except Exception:
                pass
        return
    
    try:
        action, video_type = data.split("_")
    except ValueError:
        await query.answer("❌ Invalid request!", show_alert=True)
        if waiting_msg:
            try:
                await waiting_msg.delete()
            except Exception:
                pass
        return
    
    is_brazzers = video_type == "brazzers"

    history_data = temp.USER_VIDEO_HISTORY.get(user_id)
    if not history_data or not history_data["history"]:
        await query.answer("❌ No history found. Try /getvideo!", show_alert=True)
        if waiting_msg:
            try:
                await waiting_msg.delete()
            except Exception:
                pass
        return
    
    history = history_data["history"]
    current_idx = history_data["current_index"]
    
    limit_data = await check_user_limit(user_id)
    if limit_data["reached"]:
        if waiting_msg:
            try:
                await waiting_msg.delete()
            except Exception:
                pass
        await send_limit_message(client, query, limit_data)
        return
    
    # Wait 1 second
    await asyncio.sleep(1)
    
    # Delete waiting message
    if waiting_msg:
        try:
            await waiting_msg.delete()
        except Exception:
            pass
    
    if action == "prev":
        if current_idx <= 0:
            await query.answer("⚠️ This is the first video!", show_alert=True)
            return
        
        new_idx = current_idx - 1
        video_id = history[new_idx]
        
        await query.answer("⏪ Loading previous video...", show_alert=False)
        history_data["current_index"] = new_idx
        
        try:
            await message.delete()
        except Exception:
            pass

        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        video_data = await db.videos.find_one({"file_id": video_id})
        duration = video_data.get("duration", 0) if video_data else 0

        await send_video_with_buttons(client, fake_msg, user_id, video_id, duration, is_brazzers=is_brazzers)
        return

    if action == "next":
        if current_idx + 1 < len(history):
            new_idx = current_idx + 1
            video_id = history[new_idx]
            
            await query.answer("⏩ Loading...", show_alert=False)
            history_data["current_index"] = new_idx
            
            try:
                await message.delete()
            except Exception:
                pass

            fake_msg = message
            fake_msg.from_user = query.from_user
            fake_msg.chat = message.chat

            video_data = await db.videos.find_one({"file_id": video_id})
            duration = video_data.get("duration", 0) if video_data else 0

            await send_video_with_buttons(client, fake_msg, user_id, video_id, duration, is_brazzers=is_brazzers)
            return
        
        await query.answer("⏩ Loading....", show_alert=False)
        
        current_video = history[current_idx]
        if is_brazzers:
            await db.mark_brazzers_seen(user_id, current_video)
        else:
            await db.mark_seen(user_id, current_video)

        if is_brazzers:
            new_video = await db.get_unseen_brazzers(user_id)
            if not new_video:
                await message.reply("❌ No more unseen Brazzers videos!")
                return
            duration = 0
        else:
            result = await db.get_unseen_video(user_id)
            if result and isinstance(result, tuple) and len(result) == 2:
                new_video, duration = result
            else:
                new_video = result
                duration = 0
                
            if not new_video:
                random_result = await db.get_random_video(user_id)
                if random_result and isinstance(random_result, tuple) and len(random_result) == 2:
                    new_video, duration = random_result
                else:
                    new_video = random_result
                    duration = 0
                    
            if not new_video:
                await message.reply("❌ No more videos!")
                return
            
            if not await db.has_premium_access(user_id) and duration <= 0:
                result = await db.get_unseen_video(user_id)
                if result and isinstance(result, tuple) and len(result) == 2:
                    new_video, duration = result
                else:
                    new_video = result
                    duration = 0
                if not new_video or duration <= 0:
                    await message.reply("❌ No valid videos found with proper duration.")
                    return

        history.append(new_video)
        history_data["current_index"] = len(history) - 1

        try:
            await message.delete()
        except Exception:
            pass

        fake_msg = message
        fake_msg.from_user = query.from_user
        fake_msg.chat = message.chat

        await send_video_with_buttons(client, fake_msg, user_id, new_video, duration, is_brazzers=is_brazzers)


# ---------- START CACHE CLEANUP TASK ----------
async def start_cache_cleanup():
    """Start the cache cleanup background task"""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            current_time = time.time()
            expired_keys = []
            for key, data in DOWNLOAD_CACHE.items():
                if current_time - data.get("timestamp", 0) > 300:  # 5 minutes
                    expired_keys.append(key)
            for key in expired_keys:
                if key in DOWNLOAD_CACHE:
                    del DOWNLOAD_CACHE[key]
            if expired_keys:
                print(f"🗑️ Cleaned {len(expired_keys)} expired cache entries")
        except Exception as e:
            print(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)
