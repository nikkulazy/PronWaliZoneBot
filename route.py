from aiohttp import web
import os
import time
import tempfile
import asyncio
import logging
from info import *
from database.users_db import db
from download_client import download_file, cleanup_temp_file

logger = logging.getLogger(__name__)

# ============================================================
# URL
# ============================================================
URL = environ.get("WEB_APP_URL", "https://your-app.koyeb.app/")

# ✅ CACHE for file data (MongoDB queries reduce karo)
FILE_CACHE = {}
CACHE_EXPIRY = 300  # 5 minutes

def get_cached_file(file_id):
    """Get file from cache"""
    if file_id in FILE_CACHE:
        data, timestamp = FILE_CACHE[file_id]
        if time.time() - timestamp < CACHE_EXPIRY:
            return data
        else:
            del FILE_CACHE[file_id]
    return None

def set_cached_file(file_id, data):
    """Set file in cache"""
    FILE_CACHE[file_id] = (data, time.time())

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
    from download_client import get_download_stats
    stats = get_download_stats()
    return web.json_response(stats)

# ============================================================
# 📥 FAST DOWNLOAD ROUTE - ⚡ OPTIMIZED
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """⚡ FAST DOWNLOAD - Optimized for speed"""
    temp_path = None
    start_time = time.time()
    
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        logger.info(f"⚡ Download Request: {file_id[:20]}... user={user_id}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ STEP 1: Premium Check (Fast)
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(
                text="💎 Premium feature! Buy premium to access downloads.",
                status=403
            )
        
        # ✅ STEP 2: Get File Data (Cache se)
        file_data = get_cached_file(file_id)
        if not file_data:
            # MongoDB se fetch
            file_data = await db.videos.find_one({"file_id": file_id})
            if not file_data:
                file_data = await db.brazzers.find_one({"file_id": file_id})
            if file_data:
                set_cached_file(file_id, file_data)
        
        if not file_data:
            logger.warning(f"File not found: {file_id[:20]}...")
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ STEP 3: SKIP file_exists() - Direct download (1-2 sec bachao)
        
        # ✅ STEP 4: Download File (Fast)
        try:
            downloaded_path = await download_file(file_id)
        except Exception as e:
            logger.error(f"Download error: {e}")
            return web.Response(text="❌ Download failed!", status=500)
        
        if not downloaded_path or not os.path.exists(downloaded_path):
            return web.Response(text="❌ File not accessible!", status=404)
        
        temp_path = downloaded_path
        
        # ✅ STEP 5: Read File (FAST - without aiofiles)
        try:
            with open(downloaded_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"File read error: {e}")
            cleanup_temp_file(downloaded_path)
            return web.Response(text="❌ Error reading file!", status=500)
        
        # ✅ STEP 6: Cleanup
        cleanup_temp_file(downloaded_path)
        temp_path = None
        
        # ✅ STEP 7: Get file name
        file_name = file_data.get('file_name', f'video_{user_id}.mp4')
        if not file_name or file_name in ['None', 'unknown', '']:
            file_name = f'video_{user_id}.mp4'
        
        mime_type = file_data.get('mime_type', 'video/mp4')
        if not mime_type or mime_type == 'None':
            mime_type = 'video/mp4'
        
        # ✅ STEP 8: Send Response
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"✅ Download ready! Size: {len(file_content)/1024/1024:.1f}MB, Time: {elapsed:.0f}ms")
        
        return web.Response(
            body=file_content,
            headers={
                'Content-Disposition': f'attachment; filename="{file_name}"',
                'Content-Type': mime_type,
                'Content-Length': str(len(file_content)),
                'Cache-Control': 'public, max-age=300',
                'Accept-Ranges': 'bytes',
            },
            status=200
        )
        
    except ValueError as e:
        logger.error(f"Invalid user_id: {e}")
        return web.Response(text="❌ Invalid user ID!", status=400)
    except Exception as e:
        logger.error(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        if temp_path and os.path.exists(temp_path):
            cleanup_temp_file(temp_path)
        return web.Response(text=f"❌ Error: {str(e)[:100]}", status=500)

# ============================================================
# 📥 SIMPLE DOWNLOAD ROUTE (Testing)
# ============================================================
@routes.get("/download/{file_id}")
async def simple_download_handler(request):
    """Simple download without user verification (Testing only)"""
    temp_path = None
    try:
        file_id = request.match_info.get('file_id')
        
        logger.info(f"📥 Simple Download Request: {file_id[:30]}...")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Check file in database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path or not os.path.exists(downloaded_path):
            return web.Response(text="❌ Failed to download file!", status=500)
        
        temp_path = downloaded_path
        
        # ✅ Read file
        with open(downloaded_path, 'rb') as f:
            file_content = f.read()
        
        cleanup_temp_file(downloaded_path)
        temp_path = None
        
        file_name = file_data.get('file_name', 'video.mp4')
        if not file_name or file_name in ['None', 'unknown', '']:
            file_name = 'video.mp4'
        
        mime_type = file_data.get('mime_type', 'video/mp4')
        if not mime_type or mime_type == 'None':
            mime_type = 'video/mp4'
        
        return web.Response(
            body=file_content,
            headers={
                'Content-Disposition': f'attachment; filename="{file_name}"',
                'Content-Type': mime_type,
                'Content-Length': str(len(file_content)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            },
            status=200
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
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
