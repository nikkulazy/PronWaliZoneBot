# download_client.py - Complete Download Client (FAST)

import os
import tempfile
import asyncio
import logging
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# GLOBAL VARIABLES
# ============================================================
_download_client = None
_download_client_started = False
_file_cache = {}
_download_stats = {
    "total_downloads": 0,
    "total_size": 0,
    "active_downloads": 0
}

# ============================================================
# INIT CLIENT ON START - ⚡ FAST
# ============================================================
async def init_download_client():
    """Start download client on bot startup"""
    global _download_client, _download_client_started
    try:
        logger.info("⚡ Initializing download client...")
        _download_client = Client(
            name="download_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True,
            sleep_threshold=5,
            workers=10,
        )
        await _download_client.start()
        _download_client_started = True
        logger.info("✅ Download client ready!")
        return _download_client
    except Exception as e:
        logger.error(f"❌ Client init error: {e}")
        return None

# ============================================================
# GET CLIENT - ⚡ FAST
# ============================================================
async def get_client():
    """Get download client - Already started"""
    global _download_client, _download_client_started
    if _download_client and _download_client_started:
        return _download_client
    # Fallback: Try to start
    return await init_download_client()

# ============================================================
# DOWNLOAD FILE - ⚡ FAST
# ============================================================
async def download_file(file_id, custom_name=None):
    """⚡ FAST DOWNLOAD - Direct download without extra checks"""
    temp_path = None
    try:
        client = await get_client()
        if not client:
            logger.error("❌ No client available!")
            return None
        
        # ✅ Check cache
        if file_id in _file_cache:
            cached_path = _file_cache[file_id]
            if os.path.exists(cached_path):
                logger.info(f"📦 Cache hit!")
                return cached_path
            else:
                del _file_cache[file_id]
        
        # ✅ Create temp file
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
        
        logger.info(f"📥 Downloading...")
        _download_stats["active_downloads"] += 1
        
        # ✅ Fast download - without progress callback
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path,
            progress=None  # ❌ Progress callback hatao (speed improve)
        )
        
        _download_stats["active_downloads"] -= 1
        
        if not downloaded or not os.path.exists(downloaded):
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return None
        
        file_size = os.path.getsize(downloaded)
        if file_size == 0:
            os.remove(downloaded)
            return None
        
        _download_stats["total_downloads"] += 1
        _download_stats["total_size"] += file_size
        
        # ✅ Cache for 5 minutes
        _file_cache[file_id] = downloaded
        asyncio.create_task(auto_cleanup(file_id, downloaded))
        
        logger.info(f"✅ Downloaded! {file_size/1024/1024:.1f}MB")
        return downloaded
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        _download_stats["active_downloads"] -= 1
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None

# ============================================================
# AUTO CLEANUP
# ============================================================
async def auto_cleanup(file_id, file_path):
    """Auto delete after 5 minutes"""
    await asyncio.sleep(300)  # ✅ 5 minutes (pehle 10 tha)
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            if file_id in _file_cache:
                del _file_cache[file_id]
            logger.info(f"🗑️ Auto cleaned: {file_path}")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

# ============================================================
# GET FILE INFO
# ============================================================
async def get_file_info(file_id):
    """Get file information from Telegram"""
    cache_key = f"info_{file_id}"
    if cache_key in _file_cache:
        return _file_cache[cache_key]
    
    try:
        client = await get_client()
        if not client:
            return None
        
        msg = await client.get_messages(
            chat_id='me',
            message_ids=file_id
        )
        
        if msg and msg.media:
            media_type = msg.media.value
            media = getattr(msg, media_type)
            
            info = {
                'file_id': media.file_id,
                'file_unique_id': media.file_unique_id,
                'file_name': getattr(media, 'file_name', 'unknown'),
                'file_size': getattr(media, 'file_size', 0),
                'mime_type': getattr(media, 'mime_type', 'video/mp4'),
                'duration': getattr(media, 'duration', 0),
                'width': getattr(media, 'width', 0),
                'height': getattr(media, 'height', 0)
            }
            
            _file_cache[cache_key] = info
            return info
        else:
            logger.error("❌ No media found!")
            return None
            
    except Exception as e:
        logger.error(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CHECK FILE EXISTS - ❌ REMOVED FOR SPEED (Use only if needed)
# ============================================================
async def file_exists(file_id):
    """Check if file exists in Telegram - SLOW, use sparingly"""
    try:
        client = await get_client()
        if not client:
            return False
        
        msg = await client.get_messages(
            chat_id='me',
            message_ids=file_id
        )
        
        return bool(msg and msg.media)
        
    except Exception as e:
        logger.error(f"❌ Check file error: {e}")
        return False

# ============================================================
# GET DOWNLOAD STATS
# ============================================================
def get_download_stats():
    """Get download statistics"""
    global _download_stats
    return {
        "total_downloads": _download_stats["total_downloads"],
        "total_size": _download_stats["total_size"],
        "total_size_mb": round(_download_stats["total_size"] / (1024 * 1024), 2),
        "active_downloads": _download_stats["active_downloads"],
        "cached_files": len(_file_cache)
    }

# ============================================================
# CLOSE CLIENT
# ============================================================
async def close_client():
    """Close the download client"""
    global _download_client, _download_client_started, _file_cache, _download_stats
    
    if _download_client and _download_client_started:
        try:
            await _download_client.stop()
            _download_client = None
            _download_client_started = False
            _file_cache.clear()
            _download_stats = {"total_downloads": 0, "total_size": 0, "active_downloads": 0}
            logger.info("❌ Download Client Closed!")
        except Exception as e:
            logger.error(f"❌ Error closing client: {e}")

# ============================================================
# CLEANUP FUNCTION
# ============================================================
def cleanup_temp_file(file_path):
    """Delete temporary file safely"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
    return False

# ============================================================
# CLEAR CACHE
# ============================================================
def clear_cache():
    """Clear download cache"""
    global _file_cache
    _file_cache.clear()
    logger.info("🗑️ Cache cleared!")

# ============================================================
# GET CACHE SIZE
# ============================================================
def get_cache_size():
    """Get number of cached files"""
    return len(_file_cache)
