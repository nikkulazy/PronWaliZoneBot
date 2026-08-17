# route.py - Fast Download with Flood Protection

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
# 📥 ULTRA FAST DOWNLOAD ROUTE
# ============================================================

@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    Ultra-fast download with multi-client support
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
        
        # ✅ Ultra-Fast Download
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file!", status=500)
        
        # ✅ Read and Send
        async with aiofiles.open(downloaded_path, 'rb') as f:
            file_content = await f.read()
        
        # ✅ Cleanup
        cleanup_temp_file(downloaded_path)
        
        # ✅ Calculate time
        total_time = (time.time() - start_time) * 1000
        
        # ✅ Response with timing header
        return web.Response(
            body=file_content,
            headers={
                'Content-Disposition': f'attachment; filename="video_{user_id}.mp4"',
                'Content-Type': 'video/mp4',
                'Content-Length': str(len(file_content)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Download-Time': f'{total_time:.0f}ms',
                'X-Clients': str(get_client_count())
            }
        )
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 📥 TEST DOWNLOAD (Without User ID)
# ============================================================

@routes.get("/download/{file_id}")
async def simple_download_handler(request):
    """
    Simple download for testing
    """
    try:
        file_id = request.match_info.get('file_id')
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Download failed!", status=500)
        
        async with aiofiles.open(downloaded_path, 'rb') as f:
            file_content = await f.read()
        
        cleanup_temp_file(downloaded_path)
        
        return web.Response(
            body=file_content,
            headers={
                'Content-Disposition': 'attachment; filename="video.mp4"',
                'Content-Type': 'video/mp4',
                'Content-Length': str(len(file_content)),
                'Cache-Control': 'no-cache'
            }
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return web.Response(text=f"Error: {str(e)}", status=500)

# ============================================================
# 🧪 TEST ROUTE
# ============================================================

@routes.get("/test")
async def test_handler(request):
    """Test route with status"""
    from download_client import _file_cache
    return web.json_response({
        "status": "alive",
        "message": "Download server is running! 🚀",
        "clients": get_client_count(),
        "cache_size": len(_file_cache),
        "endpoints": {
            "/d/{file_id}/{user_id}": "Fast download (premium only)",
            "/download/{file_id}": "Simple download (testing)",
            "/ping": "Health check",
            "/clients": "Client status"
        }
    })

# ============================================================
# 📊 CLIENT STATUS
# ============================================================

@routes.get("/clients")
async def clients_handler(request):
    """Show client status"""
    from fast_client import manager
    return web.json_response({
        "total_clients": len(manager.clients),
        "ready": manager.ready,
        "loads": manager.loads
    })

# ============================================================
# ✅ PING ROUTE
# ============================================================

@routes.get("/ping")
async def ping_handler(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "alive",
        "clients": get_client_count(),
        "timestamp": "ok"
    })

# ============================================================
# ❌ CLOSE CLIENTS ROUTE
# ============================================================

@routes.get("/close")
async def close_handler(request):
    """Close all download clients"""
    try:
        await close_client()
        return web.json_response({"status": "all clients closed"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# WEB SERVER
# ============================================================

async def web_server():
    """Create and return web application"""
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# ============================================================
# BACKGROUND TASKS
# ============================================================

async def keep_alive():
    """Keep the server alive"""
    while True:
        await asyncio.sleep(600)
        print("🔄 Keep alive...")

async def ping_server():
    """Ping server to keep alive"""
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
    """Check expired premium users"""
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
    """Start scheduler for daily reports"""
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
    """Set bot client"""
    global bot_client
    bot_client = client
    print("✅ Bot client set!")

URL = os.getenv("WEB_APP_URL", "https://favourite-caresa-misslazy-34708588.koyeb.app/")
