import os
import logging
import traceback
import asyncio
import aiohttp
from aiohttp import web
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import your database and config
from database.users_db import db
from info import (
    PREMIUM_LOGS, 
    LOG_CHANNEL, 
    PREMIUM_DAILY_LIMIT, 
    DAILY_LIMIT,
    WEB_APP_URL,
    VERIFICATION_DAILY_LIMIT
)
from utils import temp

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "message": "Made with Aman Kumar"})

# ============================================================
# 📥 DOWNLOAD ROUTE - Video Download Link Generator
# ============================================================
@routes.get("/download/{file_id}/{user_id}")
async def download_file_with_user_handler(request):
    """
    Handle download requests with user verification
    URL format: https://your-domain.com/download/{file_id}/{user_id}
    """
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        print(f"📥 Download request: file_id={file_id[:30]}..., user_id={user_id}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Verify user is premium
        is_premium = await db.has_premium_access(user_id)
        
        if not is_premium:
            return web.Response(
                text="💎 This feature is only for premium users!",
                status=403
            )
        
        # Get file from database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Generate Telegram file download URL
        try:
            # Get bot username
            bot_username = temp.U_NAME
            if not bot_username:
                bot_username = "PronWaliZoneBot"  # Fallback
            
            # Create download link using start parameter
            download_url = f"https://t.me/{bot_username}?start=avx-{file_data['file_unique_id']}"
            
            # Redirect to Telegram download
            return web.HTTPFound(download_url)
            
        except Exception as e:
            print(f"❌ Error generating download: {e}")
            return web.Response(text=f"❌ Error: {str(e)}", status=500)
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

@routes.get("/download/{file_id}")
async def download_file_handler(request):
    """
    Simple download handler (without user verification)
    """
    try:
        file_id = request.match_info.get('file_id')
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # Get file from database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # Get bot username
        bot_username = temp.U_NAME
        if not bot_username:
            bot_username = "PronWaliZoneBot"
        
        download_url = f"https://t.me/{bot_username}?start=avx-{file_data['file_unique_id']}"
        return web.HTTPFound(download_url)
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# --- SERVER PINGER (To keep bot alive) ---
async def ping_server():
    if not WEB_APP_URL:
        logging.warning("WEB_APP_URL not found. Pinger disabled.")
        return

    sleep_time = 600  # Ping every 10 minutes
    while True:
        await asyncio.sleep(sleep_time)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(WEB_APP_URL) as resp:
                    logging.info(f"Pinged server with response: {resp.status}")
        except Exception as e:
            logging.warning(f"Couldn't connect to the site URL: {e}")

# --- PREMIUM EXPIRY CHECKER ---
REMINDER_TIMES = [
    ("1d", timedelta(days=1)),
    ("5h30m", timedelta(hours=5, minutes=30)),
    ("10m", timedelta(minutes=10))
]

async def check_expired_premium(client):
    while True:
        try:
            now = datetime.utcnow()

            # 1. Handle Expired Users
            expired_users = await db.get_expired(now)
            for user in expired_users:
                user_id = user["id"]

                # Remove premium status
                await db.remove_premium_access(user_id)

                # Unset reminder flags in DB
                unset_flags = {f"reminder_{label}_sent": "" for label, _ in REMINDER_TIMES}
                await db.users.update_one({"id": user_id}, {"$unset": unset_flags})

                # Notify User & Log
                try:
                    tg_user = await client.get_users(user_id)
                    await client.send_message(
                        user_id,
                        f"<b>ʜᴇʏ {tg_user.mention},\n\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ᴇxᴘɪʀᴇᴅ.\n\nTᴀᴘ /buy ꜰᴏʀ ʀᴇɴᴇᴡᴀʟ ᴏᴘᴛɪᴏɴs.</b>"
                    )
                    await client.send_message(
                        PREMIUM_LOGS,
                        f"<b>#Premium_Expired\nUser: {tg_user.mention}\nID: <code>{user_id}</code></b>"
                    )
                except Exception as e:
                    print(f"[EXPIRED NOTIFY ERROR] {e}")

                await asyncio.sleep(0.5)

            # 2. Handle Reminders (Expiring Soon)
            for label, delta in REMINDER_TIMES:
                reminder_users = await db.get_expiring_soon(label, delta)
                for user in reminder_users:
                    user_id = user["id"]
                    try:
                        tg_user = await client.get_users(user_id)
                        await client.send_message(
                            user_id,
                            f"<b>ʜᴇʏ {tg_user.mention},\n\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴡɪʟʟ ᴇxᴘɪʀᴇ ɪɴ {label}.\nTᴀᴘ /buy ᴛᴏ ʀᴇɴᴇᴡ ɴᴏᴡ!</b>"
                        )
                        await client.send_message(
                            PREMIUM_LOGS,
                            f"<b>#Reminder ({label})\nUser: {tg_user.mention}\nID: <code>{user_id}</code></b>"
                        )
                    except Exception as e:
                        print(f"[REMINDER NOTIFY ERROR] {e}")

                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[PREMIUM CHECK LOOP ERROR] {e}")
        
        # Check every minute
        await asyncio.sleep(60)

# --- AUTOMATIC DAILY REPORT ---
async def auto_daily_report(client):
    print("⏰ Sending Daily Auto Report...")

    users_cursor = db.users.find({})
    report_list = []
    total_files_used = 0
    active_users_count = 0

    async for user in users_cursor:
        user_id = user.get("id", "N/A")
        username = user.get("username")
        username_display = f"@{username}" if username else "N/A"

        # -------- USAGE --------
        used = await db.get_video_count(user_id) or 0
        if used == 0:
            continue

        # -------- STATUS CHECK --------
        is_premium = await db.has_premium_access(user_id)
        is_verified = await db.is_user_verified(user_id)

        # -------- LIMIT LOGIC --------
        if is_premium:
            daily_limit = PREMIUM_DAILY_LIMIT
            subscription_type = "Paid"
        elif is_verified:
            daily_limit = VERIFICATION_DAILY_LIMIT
            subscription_type = "Verified"
        else:
            daily_limit = DAILY_LIMIT
            subscription_type = "Free"

        remaining = max(daily_limit - used, 0)

        total_files_used += used

        # -------- FORMAT ENTRY (same style) --------
        user_entry = (
            f"👤 User: {username_display} ({user_id})\n"
            f"╰ 💠 Plan: {subscription_type}\n"
            f"╰ 📁 Limit: {daily_limit} | Used: {used} | Left: {remaining}"
        )

        report_list.append(user_entry)
        active_users_count += 1

    # -------- REPORT SUMMARY --------
    today_date = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y")

    summary_text = (
        f"📅 **Date:** {today_date}\n"
        f"🧾 **Active Users:** `{active_users_count}`\n"
        f"📊 **Total Files Sent:** `{total_files_used}`"
    )

    chat_id = LOG_CHANNEL

    # -------- SEND REPORT --------
    if active_users_count > 10:
        file_path = f"Daily_Report_{today_date}.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"📊 DAILY USAGE REPORT - {today_date}\n")
            f.write("=================================\n\n")
            f.write("\n\n---------------------------------\n\n".join(report_list))
            f.write("\n\n=================================\n")
            f.write(f"Total Active Users: {active_users_count}\n")
            f.write(f"Total Files Used: {total_files_used}")

        try:
            await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=f"📊 **Daily Auto Report** 🌙\n\n{summary_text}\n\nℹ️ _Full details in file._"
            )
        except Exception as e:
            print(f"Failed to send auto report document: {e}")

        if os.path.exists(file_path):
            os.remove(file_path)

    else:
        if active_users_count == 0:
            final_msg = f"📊 **Daily Report ({today_date})**\n\n❌ No active usage today."
        else:
            formatted_entries = []
            for entry in report_list:
                entry = entry.replace("User:", "**User:**").replace("Plan:", "`Plan:`")
                formatted_entries.append(entry)

            final_msg = (
                f"📊 **Daily Report ({today_date})**\n\n"
                + "\n\n".join(formatted_entries)
                + "\n\n"
                + summary_text
            )

        try:
            await client.send_message(chat_id, final_msg)
        except Exception as e:
            print(f"Failed to send auto report message: {e}")

# --- START SCHEDULER ---
async def start_scheduler(client):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_daily_report, 
        trigger="cron", 
        hour=23, 
        minute=59, 
        timezone=pytz.timezone("Asia/Kolkata"), 
        args=[client]
    )
    scheduler.start()
    print("⏰ Daily Report Scheduler Started (11:59 PM IST)")
