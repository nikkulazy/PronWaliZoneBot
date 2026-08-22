# download_client.py - Replace with FAST version

import os
import tempfile
import asyncio
import logging
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN

logger = logging.getLogger(__name__)

# ✅ Pre-started client
_download_client = None
_download_client_started = False
_file_cache = {}
_download_stats = {"total_downloads": 0, "total_size": 0, "active_downloads": 0}

# ✅ Client ko bot start pe hi initialize karo
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

async def get_client():
    """Get download client - Already started"""
    global _download_client, _download_client_started
    if _download_client and _download_client_started:
        return _download_client
    # Fallback: Try to start
    return await init_download_client()

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
        
        # ✅ Fast download
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

async def auto_cleanup(file_id, file_path):
    """Auto delete after 5 minutes"""
    await asyncio.sleep(300)  # ✅ 5 minutes (pehle 10 tha)
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            if file_id in _file_cache:
                del _file_cache[file_id]
    except:
        pass

def cleanup_temp_file(file_path):
    """Delete temp file"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except:
        pass
    return False
