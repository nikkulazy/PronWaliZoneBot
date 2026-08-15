# route.py - FIXED VERSION (With Real File Size)

from aiohttp import web
import json
import asyncio
from info import *
from database.users_db import db
from utils import temp

routes = web.RouteTableDef()

# ============================================================
# FILE CACHE
# ============================================================
file_cache = {}
cache_lock = asyncio.Lock()

async def get_cached(file_id):
    async with cache_lock:
        return file_cache.get(file_id)

async def set_cached(file_id, data):
    async with cache_lock:
        file_cache[file_id] = data
        asyncio.create_task(clear_cache(file_id, 3600))

async def clear_cache(file_id, seconds):
    await asyncio.sleep(seconds)
    async with cache_lock:
        file_cache.pop(file_id, None)

# ============================================================
# GET FILE SIZE FROM TELEGRAM
# ============================================================
async def get_file_size_from_telegram(file_id):
    """
    Get real file size from Telegram
    """
    try:
        from pyrogram import Client
        from info import API_ID, API_HASH, BOT_TOKEN
        
        temp_client = Client(
            name="temp_size",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True
        )
        
        await temp_client.start()
        
        try:
            msg = await temp_client.get_messages('me', ids=file_id)
            if msg and msg.media:
                media_type = msg.media.value
                media = getattr(msg, media_type)
                file_size = getattr(media, 'file_size', 0)
                file_name = getattr(media, 'file_name', 'video.mp4')
                await temp_client.stop()
                return file_size, file_name
        except Exception as e:
            print(f"❌ Error getting file size: {e}")
        
        await temp_client.stop()
        return 0, 'video.mp4'
        
    except Exception as e:
        print(f"❌ Temp client error: {e}")
        return 0, 'video.mp4'

# ============================================================
# MAIN DOWNLOAD ROUTE
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    ULTRA FAST download - With Real File Size
    """
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        print(f"⚡ Request: {file_id[:20]}... by {user_id}")
        
        # ✅ Premium Check
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.json_response({
                "status": "error",
                "message": "💎 Premium users only!"
            }, status=403)
        
        # ✅ Check Cache
        cached = await get_cached(file_id)
        if cached and cached.get('file_size', 0) > 0:
            print(f"⚡ CACHE HIT! (with size)")
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
        
        # ✅ Get file info from database
        file_name = file_data.get('file_name', 'video.mp4')
        file_size = file_data.get('file_size', 0)
        
        # ✅ If file_size is 0, get from Telegram
        if file_size == 0:
            print(f"📥 Getting real file size from Telegram...")
            real_size, real_name = await get_file_size_from_telegram(file_id)
            if real_size > 0:
                file_size = real_size
                file_name = real_name
                # Update database
                await db.videos.update_one(
                    {"file_id": file_id},
                    {"$set": {"file_size": file_size, "file_name": file_name}},
                    upsert=True
                )
                print(f"✅ Updated file size: {file_size} bytes")
        
        # ✅ Generate download link
        telegram_link = f"https://t.me/{temp.U_NAME}?start=download_{file_id}"
        
        # ✅ Format file size
        def format_size(bytes):
            if bytes == 0:
                return "Unknown"
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024
            return f"{bytes:.1f} TB"
        
        # Prepare response
        response_data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_size_human": format_size(file_size),
            "download_url": telegram_link,
            "message": "Click the link to download instantly from Telegram"
        }
        
        # ✅ Cache
        await set_cached(file_id, response_data)
        
        print(f"✅ Response sent! Size: {file_size} bytes")
        
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
# PRE-CACHE FILES (Background)
# ============================================================
async def pre_cache_files():
    """Pre-cache files with real sizes"""
    while True:
        try:
            print("🔄 Pre-caching files with sizes...")
            recent = await db.videos.find().sort("_id", -1).limit(30).to_list(length=30)
            
            for file in recent:
                file_id = file.get('file_id')
                if not file_id:
                    continue
                    
                file_size = file.get('file_size', 0)
                file_name = file.get('file_name', 'video.mp4')
                
                # If size is 0, get from Telegram
                if file_size == 0:
                    print(f"📥 Getting size for: {file_id[:15]}...")
                    real_size, real_name = await get_file_size_from_telegram(file_id)
                    if real_size > 0:
                        file_size = real_size
                        file_name = real_name
                        # Update database
                        await db.videos.update_one(
                            {"file_id": file_id},
                            {"$set": {"file_size": file_size, "file_name": file_name}},
                            upsert=True
                        )
                        print(f"✅ Size updated: {file_size} bytes")
                
                # Cache
                if file_id not in file_cache:
                    response_data = {
                        "file_id": file_id,
                        "file_name": file_name,
                        "file_size": file_size,
                        "file_size_human": format_size(file_size),
                        "download_url": f"https://t.me/{temp.U_NAME}?start=download_{file_id}"
                    }
                    await set_cached(file_id, response_data)
                    print(f"📦 Cached: {file_id[:15]}... ({file_size} bytes)")
            
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"❌ Pre-cache error: {e}")
            await asyncio.sleep(60)

def format_size(bytes):
    if bytes == 0:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

# ============================================================
# CACHE STATUS
# ============================================================
@routes.get("/cache")
async def cache_handler(request):
    cache_list = []
    for key, value in list(file_cache.items())[:10]:
        cache_list.append({
            "file_id": key[:20],
            "file_name": value.get('file_name'),
            "file_size": value.get('file_size')
        })
    
    return web.json_response({
        "cache_size": len(file_cache),
        "items": cache_list
    })

@routes.get("/clear_cache")
async def clear_cache_handler(request):
    async with cache_lock:
        file_cache.clear()
    return web.json_response({"status": "cache cleared"})

@routes.get("/")
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
# WEB SERVER & OTHER FUNCTIONS
# ============================================================
async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app

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
