# route.py - ULTRA FAST (Direct Telegram Download)

from aiohttp import web
import json
import asyncio
from info import *
from database.users_db import db
from utils import temp

routes = web.RouteTableDef()

# ============================================================
# FILE CACHE (For Instant Response)
# ============================================================
file_cache = {}
cache_lock = asyncio.Lock()

async def get_cached(file_id):
    async with cache_lock:
        return file_cache.get(file_id)

async def set_cached(file_id, data):
    async with cache_lock:
        file_cache[file_id] = data
        # Clear after 1 hour
        asyncio.create_task(clear_cache(file_id, 3600))

async def clear_cache(file_id, seconds):
    await asyncio.sleep(seconds)
    async with cache_lock:
        file_cache.pop(file_id, None)

# ============================================================
# MAIN DOWNLOAD ROUTE - INSTANT!
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    ULTRA FAST download - Direct Telegram link
    Response time: < 50ms!
    """
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        print(f"⚡ Request: {file_id[:15]}... by {user_id}")
        
        # ✅ Premium Check (Fast)
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.json_response({
                "status": "error",
                "message": "💎 Premium users only!"
            }, status=403)
        
        # ✅ Check Cache First (INSTANT!)
        cached = await get_cached(file_id)
        if cached:
            print(f"⚡ CACHE HIT! Returning instantly...")
            return web.json_response({
                "status": "success",
                "cached": True,
                **cached
            })
        
        # ✅ Get from Database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.json_response({
                "status": "error",
                "message": "File not found!"
            }, status=404)
        
        # ✅ Get file info
        file_name = file_data.get('file_name', 'video.mp4')
        file_size = file_data.get('file_size', 0)
        
        # ✅ Generate Telegram download link (INSTANT!)
        # Option 1: Using Bot's start command
        telegram_link = f"https://t.me/{temp.U_NAME}?start=download_{file_id}"
        
        # Option 2: Direct file ID (if using inline mode)
        # telegram_link = f"https://t.me/{temp.U_NAME}?start=file_{file_id}"
        
        # Prepare response
        response_data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "download_url": telegram_link,
            "message": "Click the link to download instantly from Telegram"
        }
        
        # ✅ Cache for next request
        await set_cached(file_id, response_data)
        
        print(f"✅ Response sent instantly! Size: {file_size} bytes")
        
        return web.json_response({
            "status": "success",
            "cached": False,
            **response_data
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({
            "status": "error",
            "message": str(e)
        }, status=500)

# ============================================================
# DIRECT FILE DOWNLOAD (Without Server)
# ============================================================
@routes.get("/file/{file_id}/{user_id}")
async def direct_file_handler(request):
    """
    Direct file download from Telegram
    """
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        # ✅ Premium Check
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(text="💎 Premium only!", status=403)
        
        # ✅ Get file from database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="File not found!", status=404)
        
        # ✅ Get file info
        file_name = file_data.get('file_name', 'video.mp4')
        file_size = file_data.get('file_size', 0)
        
        # ✅ Create HTML page with direct download
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Download</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: #0d1117;
                    color: #c9d1d9;
                }}
                .container {{
                    max-width: 500px;
                    margin: 0 auto;
                    background: #161b22;
                    padding: 30px;
                    border-radius: 10px;
                    border: 1px solid #30363d;
                }}
                h1 {{ color: #58a6ff; }}
                .info {{ margin: 20px 0; padding: 15px; background: #0d1117; border-radius: 5px; }}
                .btn {{
                    display: inline-block;
                    padding: 15px 40px;
                    background: #238636;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 20px;
                    border: none;
                    cursor: pointer;
                }}
                .btn:hover {{ background: #2ea043; }}
                .size {{ color: #8b949e; }}
                .footer {{ margin-top: 30px; color: #8b949e; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📥 Download</h1>
                <div class="info">
                    <p><strong>File:</strong> {file_name}</p>
                    <p class="size"><strong>Size:</strong> {file_size} bytes</p>
                </div>
                <a href="https://t.me/{temp.U_NAME}?start=download_{file_id}" class="btn">
                    ⬇️ Download Now
                </a>
                <div class="footer">
                    <p>Powered by AV BOTZ</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return web.Response(text=f"Error: {str(e)}", status=500)

# ============================================================
# PRE-CACHE FILES (Background)
# ============================================================
async def pre_cache_files():
    """Pre-cache popular files"""
    while True:
        try:
            print("🔄 Pre-caching files...")
            # Get recent files
            recent = await db.videos.find().sort("_id", -1).limit(30).to_list(length=30)
            for file in recent:
                file_id = file.get('file_id')
                if file_id and file_id not in file_cache:
                    file_data = {
                        "file_id": file_id,
                        "file_name": file.get('file_name', 'video.mp4'),
                        "file_size": file.get('file_size', 0),
                        "download_url": f"https://t.me/{temp.U_NAME}?start=download_{file_id}"
                    }
                    await set_cached(file_id, file_data)
                    print(f"📦 Pre-cached: {file_id[:15]}...")
            await asyncio.sleep(300)  # Every 5 minutes
        except Exception as e:
            print(f"❌ Pre-cache error: {e}")
            await asyncio.sleep(60)

# ============================================================
# CACHE STATUS
# ============================================================
@routes.get("/cache")
async def cache_handler(request):
    return web.json_response({
        "cache_size": len(file_cache),
        "keys": list(file_cache.keys())[:10]
    })

@routes.get("/clear_cache")
async def clear_cache_handler(request):
    async with cache_lock:
        file_cache.clear()
    return web.json_response({"status": "cache cleared"})

# ============================================================
# ROOT ROUTES
# ============================================================
@routes.get("/", allow_head=True)
async def root_handler(request):
    return web.json_response({
        "status": "running",
        "message": "PronWaliZoneBot - ULTRA FAST",
        "cache_size": len(file_cache)
    })

@routes.get("/ping")
async def ping_handler(request):
    return web.json_response({"status": "alive"})

# ============================================================
# WEB SERVER
# ============================================================
async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app

# ============================================================
# PING SERVER
# ============================================================
async def ping_server():
    while True:
        await asyncio.sleep(600)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{URL}/ping") as resp:
                    print(f"📡 Ping: {resp.status}")
        except:
            pass

# ============================================================
# OTHER FUNCTIONS (For compatibility)
# ============================================================
async def check_expired_premium(client):
    while True:
        try:
            from datetime import datetime
            now = datetime.utcnow()
            expired = await db.get_expired(now)
            for user in expired:
                user_id = user["id"]
                await db.remove_premium_access(user_id)
                try:
                    await client.send_message(
                        user_id,
                        f"<b>Your premium has expired.\nTap /buy to renew.</b>"
                    )
                except:
                    pass
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Premium check error: {e}")
        await asyncio.sleep(60)

async def start_scheduler(client):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import pytz
    scheduler = AsyncIOScheduler()
    async def daily_report():
        print("⏰ Daily report...")
    scheduler.add_job(
        daily_report,
        trigger="cron",
        hour=23,
        minute=59,
        timezone=pytz.timezone("Asia/Kolkata")
    )
    scheduler.start()
    print("⏰ Scheduler started")

def set_bot_client(client):
    global bot_client
    bot_client = client
    print("✅ Bot client set!")

URL = environ.get("WEB_APP_URL", "https://casual-cristin-misslazy-9a60a509.koyeb.app/")
