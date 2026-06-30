from aiohttp import web
import os
import re
import logging
import tempfile
import asyncio
import aiofiles
from info import *
from database.users_chats_db import db
from database.ia_filterdb import Media, Media2
from download_client import download_file, cleanup_temp_file, get_file_info, close_client

# ============================================================
# ROUTES
# ============================================================

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "message": "DreamxBotz"})

# ============================================================
# 📥 DIRECT DOWNLOAD ROUTE - PREMIUM USERS ONLY
# ============================================================
@routes.get("/d/{file_id}/{user_id}")
async def download_handler(request):
    """
    Direct file download from server
    URL: https://yourapp.com/d/{file_id}/{user_id}
    Only for premium users
    """
    try:
        file_id = request.match_info.get('file_id')
        user_id = int(request.match_info.get('user_id'))
        
        print(f"📥 Download Request: file_id={file_id[:30]}..., user_id={user_id}")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Premium Check
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return web.Response(
                text="💎 This feature is only for premium users!",
                status=403
            )
        
        # ✅ Find file in database
        file_data = await Media.find_one({"file_id": file_id})
        if not file_data and MULTIPLE_DB:
            file_data = await Media2.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Get file info
        file_info = await get_file_info(file_id)
        if file_info:
            file_name = file_info.get('file_name', f'video_{user_id}.mp4')
        else:
            file_name = f'video_{user_id}.mp4'
        
        # ✅ Download file using our custom client
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file from Telegram!", status=500)
        
        # ✅ Read file content
        try:
            async with aiofiles.open(downloaded_path, 'rb') as f:
                file_content = await f.read()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            cleanup_temp_file(downloaded_path)
            return web.Response(text="❌ Error reading file!", status=500)
        
        # ✅ Cleanup temp file
        cleanup_temp_file(downloaded_path)
        
        # ✅ Create download response
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(len(file_content)),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        print(f"✅ Sending file... Size: {len(file_content)} bytes")
        
        return web.Response(
            body=file_content,
            headers=headers
        )
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 📥 SIMPLE DOWNLOAD ROUTE (Without User ID - For Testing)
# ============================================================
@routes.get("/download/{file_id}")
async def simple_download_handler(request):
    """
    Simple download without user verification (Testing only)
    URL: https://yourapp.com/download/{file_id}
    """
    try:
        file_id = request.match_info.get('file_id')
        
        print(f"📥 Simple Download Request: file_id={file_id[:30]}...")
        
        if not file_id:
            return web.Response(text="❌ Invalid file ID!", status=400)
        
        # ✅ Find file in database
        file_data = await Media.find_one({"file_id": file_id})
        if not file_data and MULTIPLE_DB:
            file_data = await Media2.find_one({"file_id": file_id})
        
        if not file_data:
            return web.Response(text="❌ File not found!", status=404)
        
        # ✅ Get file info
        file_info = await get_file_info(file_id)
        if file_info:
            file_name = file_info.get('file_name', 'video.mp4')
        else:
            file_name = 'video.mp4'
        
        # ✅ Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return web.Response(text="❌ Failed to download file from Telegram!", status=500)
        
        # ✅ Read file content
        try:
            async with aiofiles.open(downloaded_path, 'rb') as f:
                file_content = await f.read()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            cleanup_temp_file(downloaded_path)
            return web.Response(text="❌ Error reading file!", status=500)
        
        # ✅ Cleanup temp file
        cleanup_temp_file(downloaded_path)
        
        # ✅ Create download response
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(len(file_content)),
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
        
        print(f"✅ Sending file... Size: {len(file_content)} bytes")
        
        return web.Response(
            body=file_content,
            headers=headers
        )
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text=f"❌ Error: {str(e)}", status=500)

# ============================================================
# 🔍 GET FILE INFO ROUTE
# ============================================================
@routes.get("/fileinfo/{file_id}")
async def file_info_handler(request):
    """
    Get file information
    URL: https://yourapp.com/fileinfo/{file_id}
    """
    try:
        file_id = request.match_info.get('file_id')
        
        if not file_id:
            return web.json_response({"error": "Invalid file ID!"}, status=400)
        
        # ✅ Get file info
        file_info = await get_file_info(file_id)
        
        if not file_info:
            return web.json_response({"error": "File not found!"}, status=404)
        
        return web.json_response({
            "status": "success",
            "data": file_info
        })
        
    except Exception as e:
        print(f"❌ File info error: {e}")
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# 🧪 TEST ROUTE
# ============================================================
@routes.get("/test")
async def test_handler(request):
    """
    Test route to check if server is working
    """
    return web.json_response({
        "status": "alive",
        "message": "Download server is running!",
        "endpoints": {
            "/d/{file_id}/{user_id}": "Download file (premium only)",
            "/download/{file_id}": "Download file (no auth, testing)",
            "/fileinfo/{file_id}": "Get file info",
            "/ping": "Ping check"
        }
    })

# ============================================================
# ✅ PING ROUTE
# ============================================================
@routes.get("/ping")
async def ping_handler(request):
    """
    Health check endpoint
    """
    return web.json_response({"status": "alive", "timestamp": "ok"})

# ============================================================
# ❌ CLOSE CLIENT ROUTE (Admin Only)
# ============================================================
@routes.get("/close")
async def close_handler(request):
    """
    Close download client (for maintenance)
    """
    try:
        await close_client()
        return web.json_response({"status": "client closed"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ============================================================
# WEB SERVER FUNCTION
# ============================================================
async def web_server():
    """
    Create and return web application
    """
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# ============================================================
# KEEP ALIVE FUNCTION (For compatibility)
# ============================================================
async def keep_alive():
    """
    Keep the server alive
    """
    while True:
        await asyncio.sleep(600)  # 10 minutes
        print("🔄 Keep alive ping...")
