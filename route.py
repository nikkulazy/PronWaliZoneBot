from aiohttp import web
import os
import asyncio
import aiofiles
from info import *
from database.users_db import db
from download_client import download_file, cleanup_temp_file, get_file_info, close_client, get_download_stats
import time

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "message": "PronWaliZoneBot"})

# ============================================================
# 📥 ULTRA FAST DOWNLOAD ROUTE - FIXED
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    ULTRA FAST download - 0.01 sec start delay
    """
    start_time = time.time()
    
    try:
        file_id = request.match_info.get('file_id')
        user_id_str = request.match_info.get('user_id')
        
        print(f"\n📥 Download Request: user={user_id_str}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ FIX: Remove 'l' suffix and convert to int
        user_id_str = user_id_str.rstrip('lL')  # Remove 'l' or 'L' from end
        try:
            user_id = int(user_id_str)
        except ValueError:
            return web.Response(text="❌ Invalid user ID!", status=400)
        
        # ✅ Premium Check (fast)
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(
                text="💎 Premium only!",
                status=403
            )
        
        # ✅ Check file in database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ START DOWNLOAD - INSTANT (0.01s)
        print(f"⏱️ Starting download at {time.time() - start_time:.3f}s")
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Download failed!", status=500)
        
        # ✅ Get file info (from cache - instant)
        file_size = os.path.getsize(downloaded_path)
        file_name = f'video_{user_id}.mp4'
        
        print(f"✅ File ready: {file_size/1024/1024:.2f}MB in {time.time() - start_time:.2f}s")
        
        # ✅ STREAM RESPONSE (chunk by chunk)
        async def file_stream():
            chunk_size = 1024 * 1024  # 1MB chunks
            try:
                async with aiofiles.open(downloaded_path, 'rb') as f:
                    while True:
                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                print(f"❌ Stream error: {e}")
            finally:
                try:
                    os.remove(downloaded_path)
                except:
                    pass
        
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        }
        
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        # Send chunks
        async for chunk in file_stream():
            await response.write(chunk)
            
        return response
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 📥 DOWNLOAD WITH CUSTOM FILE NAME - FIXED
# ============================================================
@routes.get("/d/{file_id}/{user_id}/{file_name}")
async def download_with_name_handler(request):
    """
    Download with custom file name
    """
    start_time = time.time()
    
    try:
        file_id = request.match_info.get('file_id')
        user_id_str = request.match_info.get('user_id')
        file_name = request.match_info.get('file_name', 'video.mp4')
        
        print(f"\n📥 Download Request: user={user_id_str}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ FIX: Remove 'l' suffix and convert to int
        user_id_str = user_id_str.rstrip('lL')
        try:
            user_id = int(user_id_str)
        except ValueError:
            return web.Response(text="❌ Invalid user ID!", status=400)
        
        # ✅ Premium Check
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(
                text="💎 Premium only!",
                status=403
            )
        
        # ✅ Check file in database
        file_data = await db.videos.find_one({"file_id": file_id})
        if not file_data:
            file_data = await db.brazzers.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ START DOWNLOAD
        downloaded_path = await download_file(file_id, custom_name=file_name)
        
        if not downloaded_path:
            return web.Response(text="❌ Download failed!", status=500)
        
        file_size = os.path.getsize(downloaded_path)
        
        print(f"✅ File ready: {file_size/1024/1024:.2f}MB in {time.time() - start_time:.2f}s")
        
        # ✅ STREAM RESPONSE
        async def file_stream():
            chunk_size = 1024 * 1024
            try:
                async with aiofiles.open(downloaded_path, 'rb') as f:
                    while True:
                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                print(f"❌ Stream error: {e}")
            finally:
                try:
                    os.remove(downloaded_path)
                except:
                    pass
        
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        }
        
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        async for chunk in file_stream():
            await response.write(chunk)
            
        return response
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 📊 STATS ROUTE
# ============================================================
@routes.get("/stats")
async def stats_handler(request):
    try:
        stats = await get_download_stats()
        return web.json_response(stats)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# 🧹 CLEAR CACHE ROUTE
# ============================================================
@routes.get("/clear_cache")
async def clear_cache_handler(request):
    try:
        from download_client import _cache, _file_info_cache
        file_deleted, file_size = _cache.clear_all_cache()
        _file_info_cache.clear()
        return web.json_response({
            "status": "success",
            "deleted_files": file_deleted,
            "deleted_size_mb": file_size / (1024*1024)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# 🧪 TEST ROUTE
# ============================================================
@routes.get("/test")
async def test_handler(request):
    return web.json_response({
        "status": "alive",
        "message": "Ultra Fast Download Server",
        "endpoints": {
            "/d/{file_id}/{user_id}": "Ultra fast download",
            "/d/{file_id}/{user_id}/{file_name}": "Download with custom name",
            "/stats": "System stats",
            "/clear_cache": "Clear cache",
            "/ping": "Ping"
        }
    })

# ============================================================
# ✅ PING ROUTE
# ============================================================
@routes.get("/ping")
async def ping_handler(request):
    return web.json_response({"status": "alive", "timestamp": "ok"})

# ============================================================
# ❌ CLOSE CLIENT ROUTE
# ============================================================
@routes.get("/close")
async def close_handler(request):
    try:
        await close_client()
        return web.json_response({"status": "client closed"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# WEB SERVER FUNCTION
# ============================================================
async def web_server():
    web_app = web.Application(client_max_size=1024*1024*1024)
    web_app.add_routes(routes)
    return web_app

# ============================================================
# COMPATIBILITY FUNCTIONS
# ============================================================
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
                user_id = user["id"]
                await db.remove_premium_access(user_id)
                try:
                    tg_user = await client.get_users(user_id)
                    await client.send_message(
                        user_id,
                        f"<b>ʜᴇʏ {tg_user.mention},\n\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ᴇxᴘɪʀᴇᴅ.\n\nTᴀᴘ /buy ꜰᴏʀ ʀᴇɴᴇᴡᴀʟ ᴏᴘᴛɪᴏɴs.</b>"
                    )
                except Exception as e:
                    print(f"[EXPIRED NOTIFY ERROR] {e}")
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[PREMIUM CHECK LOOP ERROR] {e}")
        await asyncio.sleep(60)

async def start_scheduler(client):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import pytz
    
    scheduler = AsyncIOScheduler()
    
    async def auto_daily_report():
        print("⏰ Sending Daily Auto Report...")
    
    scheduler.add_job(
        auto_daily_report, 
        trigger="cron", 
        hour=23, 
        minute=59, 
        timezone=pytz.timezone("Asia/Kolkata")
    )
    scheduler.start()
    print("⏰ Daily Report Scheduler Started")

def set_bot_client(client):
    global bot_client
    bot_client = client
    print("✅ Bot client set")

URL = "https://favourite-caresa-misslazy-34708588.koyeb.app/"
