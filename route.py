from aiohttp import web
import os
import tempfile
import asyncio
import aiofiles
import logging
from info import *
from database.users_db import db
from download_client import (
    download_file, 
    cleanup_temp_file, 
    get_file_info, 
    close_client, 
    file_exists,
    get_download_stats
)

logger = logging.getLogger(__name__)

# ============================================================
# URL
# ============================================================
URL = environ.get("WEB_APP_URL", "https://casual-cristin-misslazy-9a60a509.koyeb.app/")

# ============================================================
# ROUTES
# ============================================================

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "running", 
        "message": "PronWaliZoneBot",
        "endpoints": {
            "/d/{file_id}/{user_id}": "Download (Premium Only)",
            "/download/{file_id}": "Download (Testing)",
            "/ping": "Health Check",
            "/stats": "Download Stats"
        }
    })

@routes.get("/stats")
async def stats_handler(request):
    """Get download statistics"""
    stats = get_download_stats()
    return web.json_response(stats)

# ============================================================
# 📥 DIRECT DOWNLOAD ROUTE - ✅ FIXED
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    Direct file download from server
    URL: https://yourapp.com/d/{file_id}/{user_id}
    """
    temp_path = None
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        logger.info(f"📥 Download Request: file_id={file_id[:30]}..., user_id={user_id}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Premium Check
        try:
            is_premium = await db.has_premium_access(user_id)
        except Exception as e:
            logger.error(f"Premium check error: {e}")
            is_premium = False
        
        if not is_premium:
            return web.Response(
                text="💎 This feature is only for premium users!\n\nBuy premium to access downloads.",
                status=403
            )
        
        # ✅ Check file in database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            logger.warning(f"File not found in DB: {file_id[:30]}...")
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Check if file exists in Telegram
        file_exists_check = await file_exists(file_id)
        if not file_exists_check:
            logger.warning(f"File not found in Telegram: {file_id[:30]}...")
            return web.Response(text="❌ File not accessible in Telegram!", status=404)
        
        # ✅ Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file from Telegram!", status=500)
        
        if not os.path.exists(downloaded_path):
            logger.error(f"❌ Downloaded file not found at: {downloaded_path}")
            return web.Response(text="❌ Downloaded file not found!", status=500)
        
        temp_path = downloaded_path
        
        # ✅ Get file size
        file_size = os.path.getsize(downloaded_path)
        logger.info(f"📁 File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("❌ Downloaded file is empty!")
            cleanup_temp_file(downloaded_path)
            return web.Response(text="❌ Downloaded file is empty!", status=500)
        
        # ✅ Read file content - ✅ FIXED with better error handling
        try:
            # ✅ Method 1: Read with aiofiles
            async with aiofiles.open(downloaded_path, 'rb') as f:
                file_content = await f.read()
            logger.info(f"✅ File read successfully! Size: {len(file_content)} bytes")
        except Exception as e:
            logger.error(f"❌ aiofiles read error: {e}")
            try:
                # ✅ Method 2: Read with normal open (fallback)
                with open(downloaded_path, 'rb') as f:
                    file_content = f.read()
                logger.info(f"✅ File read with fallback! Size: {len(file_content)} bytes")
            except Exception as e2:
                logger.error(f"❌ Both read methods failed: {e2}")
                cleanup_temp_file(downloaded_path)
                return web.Response(text=f"❌ Error reading file: {str(e2)}", status=500)
        
        # ✅ Cleanup temp file
        cleanup_temp_file(downloaded_path)
        temp_path = None
        
        # ✅ Get file name
        file_name = file_data.get('file_name', f'video_{user_id}.mp4')
        if not file_name or file_name == 'None' or file_name == 'unknown':
            file_name = f'video_{user_id}.mp4'
        
        # ✅ Get mime type
        mime_type = file_data.get('mime_type', 'video/mp4')
        if not mime_type or mime_type == 'None':
            mime_type = 'video/mp4'
        
        # ✅ Create download response
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': mime_type,
            'Content-Length': str(len(file_content)),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Accept-Ranges': 'bytes',
        }
        
        logger.info(f"✅ Sending file... Name: {file_name}, Size: {len(file_content)} bytes")
        
        return web.Response(
            body=file_content,
            headers=headers,
            status=200
        )
        
    except ValueError as e:
        logger.error(f"Invalid user_id: {e}")
        return web.Response(text="❌ Invalid user ID!", status=400)
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        if temp_path and os.path.exists(temp_path):
            cleanup_temp_file(temp_path)
        return web.Response(text=f"❌ Error: {str(e)[:100]}", status=500)

# ============================================================
# 📥 SIMPLE DOWNLOAD ROUTE - ✅ FIXED
# ============================================================
@routes.get("/download/{file_id}")
async def simple_download_handler(request):
    """
    Simple download without user verification (Testing only)
    """
    temp_path = None
    try:
        file_id = request.match_info.get('file_id')
        
        logger.info(f"📥 Simple Download Request: file_id={file_id[:30]}...")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Check file in database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Check if file exists in Telegram
        file_exists_check = await file_exists(file_id)
        if not file_exists_check:
            return web.Response(text="❌ File not accessible in Telegram!", status=404)
        
        # ✅ Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file from Telegram!", status=500)
        
        if not os.path.exists(downloaded_path):
            logger.error(f"❌ Downloaded file not found at: {downloaded_path}")
            return web.Response(text="❌ Downloaded file not found!", status=500)
        
        temp_path = downloaded_path
        
        # ✅ Get file size
        file_size = os.path.getsize(downloaded_path)
        logger.info(f"📁 File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("❌ Downloaded file is empty!")
            cleanup_temp_file(downloaded_path)
            return web.Response(text="❌ Downloaded file is empty!", status=500)
        
        # ✅ Read file content - ✅ FIXED
        try:
            async with aiofiles.open(downloaded_path, 'rb') as f:
                file_content = await f.read()
            logger.info(f"✅ File read successfully! Size: {len(file_content)} bytes")
        except Exception as e:
            logger.error(f"❌ aiofiles read error: {e}")
            try:
                with open(downloaded_path, 'rb') as f:
                    file_content = f.read()
                logger.info(f"✅ File read with fallback! Size: {len(file_content)} bytes")
            except Exception as e2:
                logger.error(f"❌ Both read methods failed: {e2}")
                cleanup_temp_file(downloaded_path)
                return web.Response(text=f"❌ Error reading file: {str(e2)}", status=500)
        
        # ✅ Cleanup temp file
        cleanup_temp_file(downloaded_path)
        temp_path = None
        
        # ✅ Get file name
        file_name = file_data.get('file_name', 'video.mp4')
        if not file_name or file_name == 'None' or file_name == 'unknown':
            file_name = 'video.mp4'
        
        # ✅ Get mime type
        mime_type = file_data.get('mime_type', 'video/mp4')
        if not mime_type or mime_type == 'None':
            mime_type = 'video/mp4'
        
        # ✅ Create download response
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': mime_type,
            'Content-Length': str(len(file_content)),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        }
        
        logger.info(f"✅ Sending file... Name: {file_name}, Size: {len(file_content)} bytes")
        
        return web.Response(
            body=file_content,
            headers=headers,
            status=200
        )
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        if temp_path and os.path.exists(temp_path):
            cleanup_temp_file(temp_path)
        return web.Response(text=f"❌ Error: {str(e)[:100]}", status=500)

# ============================================================
# ✅ PING ROUTE
# ============================================================
@routes.get("/ping")
async def ping_handler(request):
    """Health check endpoint"""
    return web.json_response({"status": "alive", "timestamp": "ok"})

# ============================================================
# 🧪 TEST ROUTE
# ============================================================
@routes.get("/test")
async def test_handler(request):
    """Test route"""
    return web.json_response({
        "status": "alive",
        "message": "Server is working!",
        "download_endpoints": {
            "/d/{file_id}/{user_id}": "Download (premium only)",
            "/download/{file_id}": "Download (testing)",
            "/ping": "Health check"
        }
    })

# ============================================================
# WEB SERVER FUNCTION
# ============================================================
async def web_server():
    """Create and return web application"""
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# ============================================================
# PING SERVER FUNCTION
# ============================================================
async def ping_server():
    """Ping server to keep alive"""
    import aiohttp
    while True:
        await asyncio.sleep(600)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{URL}/ping") as resp:
                    logger.info(f"📡 Ping response: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Ping error: {e}")

# ============================================================
# PREMIUM EXPIRY CHECKER
# ============================================================
async def check_expired_premium(client):
    """Check expired premium users"""
    while True:
        try:
            from datetime import datetime
            
            now = datetime.utcnow()
            expired_users = await db.get_expired(now)
            
            for user in expired_users:
                user_id = user["id"]
                await db.remove_premium_access(user_id)
                
                try:
                    await client.send_message(
                        user_id,
                        f"<b>ʜᴇʏ {user.get('name', 'User')},\n\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ᴇxᴘɪʀᴇᴅ.\n\nTᴀᴘ /buy ꜰᴏʀ ʀᴇɴᴇᴡᴀʟ ᴏᴘᴛɪᴏɴs.</b>"
                    )
                except Exception as e:
                    logger.error(f"[EXPIRED NOTIFY ERROR] {e}")
                
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"[PREMIUM CHECK LOOP ERROR] {e}")
        
        await asyncio.sleep(60)

# ============================================================
# START SCHEDULER
# ============================================================
async def start_scheduler(client):
    """Start scheduler for daily reports"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import pytz
    
    scheduler = AsyncIOScheduler()
    
    async def auto_daily_report():
        logger.info("⏰ Sending Daily Auto Report...")
    
    scheduler.add_job(
        auto_daily_report, 
        trigger="cron", 
        hour=23, 
        minute=59, 
        timezone=pytz.timezone("Asia/Kolkata")
    )
    scheduler.start()
    logger.info("⏰ Daily Report Scheduler Started (11:59 PM IST)")

# ============================================================
# SET BOT CLIENT
# ============================================================
bot_client = None

def set_bot_client(client):
    """Set bot client for route.py"""
    global bot_client
    bot_client = client
    logger.info("✅ Bot client set in route.py")
