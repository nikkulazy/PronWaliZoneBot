# route.py - Fast Download with Streaming

from aiohttp import web
import os
import tempfile
import asyncio
import aiofiles
import time
from info import *
from database.users_db import db
from download_client import download_file, cleanup_temp_file, get_file_info, close_client
from fast_client import get_client_count

# ============================================================
# ROUTES
# ============================================================

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "running", 
        "message": "PronWaliZoneBot - Fast Download Active! 🚀",
        "clients": get_client_count()
    })

# ============================================================
# 📥 ULTRA FAST DOWNLOAD WITH STREAMING
# ============================================================

@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    Fast download with streaming (no memory issues)
    """
    start_time = time.time()
    
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        print(f"\n📥 Download Request: user={user_id}")
        print(f"📁 File ID: {file_id[:20]}...")
        
        # ✅ Premium Check
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(
                text="💎 This feature is only for premium users!",
                status=403
            )
        
        # ✅ File Check (Fast)
        file_data = await db.videos.find_one(
            {"file_id": file_id},
            {"file_id": 1}
        )
        if not file_data:
            file_data = await db.brazzers.find_one(
                {"file_id": file_id},
                {"file_id": 1}
            )
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Get file info
        file_info = await get_file_info(file_id)
        if not file_info:
            return web.Response(text="❌ Could not get file info!", status=500)
        
        file_size = file_info.get('file_size', 0)
        file_name = file_info.get('file_name', f'video_{user_id}.mp4')
        
        print(f"📊 File Size: {file_size/1024/1024:.1f} MB")
        
        # ✅ Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file!", status=500)
        
        # ✅ STREAM FILE (Chunk by chunk - NO MEMORY ISSUE)
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Accept-Ranges'] = 'bytes'
        
        await response.prepare(request)
        
        # ✅ Stream in 4MB chunks
        chunk_size = 1024 * 1024 * 4
        bytes_sent = 0
        
        async with aiofiles.open(downloaded_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                await response.write(chunk)
                bytes_sent += len(chunk)
                
                # Show progress every 50MB
                if bytes_sent % (1024 * 1024 * 50) < chunk_size:
                    progress = (bytes_sent / file_size) * 100 if file_size > 0 else 0
                    print(f"📤 Sent: {bytes_sent/1024/1024:.1f} MB ({progress:.1f}%)")
        
        # ✅ Cleanup
        cleanup_temp_file(downloaded_path)
        
        total_time = (time.time() - start_time) * 1000
        print(f"✅ Streamed {bytes_sent/1024/1024:.1f} MB in {total_time/1000:.2f}s")
        
        return response
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 📥 TEST DOWNLOAD
# ============================================================

@routes.get("/download/{file_id}")
async def simple_download_handler(request):
    """Simple download for testing"""
    try:
        file_id = request.match_info.get('file_id')
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Download failed!", status=500)
        
        # Stream
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Content-Disposition'] = 'attachment; filename="video.mp4"'
        response.headers['Cache-Control'] = 'no-cache'
        
        await response.prepare(request)
        
        chunk_size = 1024 * 1024 * 4
        async with aiofiles.open(downloaded_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                await response.write(chunk)
        
        cleanup_temp_file(downloaded_path)
        return response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return web.Response(text=f"Error: {str(e)}", status=500)

# ============================================================
# 🧪 TEST ROUTE
# ============================================================

@routes.get("/test")
async def test_handler(request):
    """Test route"""
    from download_client import _file_cache
    return web.json_response({
        "status": "alive",
        "message": "Download server is running! 🚀",
        "clients": get_client_count(),
        "cache_size": len(_file_cache),
        "endpoints": {
            "/d/{file_id}/{user_id}": "Fast download (premium only)",
            "/download/{file_id}": "Simple download (testing)",
            "/ping": "Health check"
        }
    })

# ============================================================
# ✅ PING ROUTE
# ============================================================

@routes.get("/ping")
async def ping_handler(request):
    """Health check"""
    return web.json_response({
        "status": "alive",
        "clients": get_client_count(),
        "timestamp": "ok"
    })

# ============================================================
# ❌ CLOSE ROUTE
# ============================================================

@routes.get("/close")
async def close_handler(request):
    """Close client"""
    try:
        await close_client()
        return web.json_response({"status": "client closed"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# WEB SERVER
# ============================================================

async def web_server():
    """Create web application"""
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# ============================================================
# BACKGROUND TASKS
# ============================================================

async def keep_alive():
    while True:
        await asyncio.sleep(600)
        print("🔄 Keep alive...")

async def ping_server():
    while True:
        await asyncio.sleep(600)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{URL}/ping") as resp:
                    print(f"📡 Ping: {resp.status}")
        except Exception as e:
            print(f"❌ Ping error: {e}")

async def check_expired_premium(client):
    while True:
        try:
            from datetime import datetime
            now = datetime.utcnow()
            expired_users = await db.get_expired(now)
            for user in expired_users:
                await db.remove_premium_access(user["id"])
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[PREMIUM CHECK] {e}")
        await asyncio.sleep(60)

async def start_scheduler(client):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import pytz
    
    scheduler = AsyncIOScheduler()
    
    async def auto_daily_report():
        print("⏰ Daily Report...")
    
    scheduler.add_job(
        auto_daily_report, 
        trigger="cron", 
        hour=23, 
        minute=59, 
        timezone=pytz.timezone("Asia/Kolkata")
    )
    scheduler.start()
    print("⏰ Scheduler Started!")

# ============================================================
# SET BOT CLIENT
# ============================================================

bot_client = None

def set_bot_client(client):
    global bot_client
    bot_client = client
    print("✅ Bot client set!")

URL = os.getenv("WEB_APP_URL", "https://your-app.com/")
