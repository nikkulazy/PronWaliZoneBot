# download_client.py - Ultra Fast Download Client

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
_download_client_starting = False  # ✅ Prevent multiple starts
_file_cache = {}  # ✅ Cache for file info

# ============================================================
# CLIENT START / GET - ✅ FAST START
# ============================================================
async def get_client():
    """
    Get or create download client - Ultra Fast
    """
    global _download_client, _download_client_started, _download_client_starting
    
    # ✅ Already started - Return instantly
    if _download_client and _download_client_started:
        return _download_client
    
    # ✅ Already starting - Wait for it
    if _download_client_starting:
        while _download_client_starting:
            await asyncio.sleep(0.1)
        return _download_client
    
    # ✅ Start new client
    _download_client_starting = True
    try:
        logger.info("⚡ Creating new download client...")
        _download_client = Client(
            name="download_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True,  # ✅ Fast start
            sleep_threshold=5,  # ✅ Less sleep = Fast
            workers=10,  # ✅ More workers = Fast
        )
        
        # ✅ Start with timeout
        try:
            await asyncio.wait_for(_download_client.start(), timeout=10)
            _download_client_started = True
            logger.info("✅ Download Client Started Successfully!")
        except asyncio.TimeoutError:
            logger.error("❌ Client start timeout!")
            _download_client = None
            _download_client_started = False
            
    except Exception as e:
        logger.error(f"❌ Error starting download client: {e}")
        _download_client = None
        _download_client_started = False
    finally:
        _download_client_starting = False
    
    return _download_client

# ============================================================
# INIT CLIENT ON START - ✅ PRE-START FOR FAST DOWNLOAD
# ============================================================
async def init_download_client():
    """
    Initialize download client on bot start
    So download starts instantly when user clicks
    """
    global _download_client, _download_client_started
    
    if not _download_client or not _download_client_started:
        logger.info("🚀 Pre-initializing download client...")
        client = await get_client()
        if client:
            logger.info("✅ Download client ready for fast downloads!")
        return client
    return _download_client

# ============================================================
# DOWNLOAD FILE FUNCTION - ✅ FASTEST
# ============================================================
async def download_file(file_id, custom_name=None):
    """
    Download file from Telegram - Ultra Fast
    """
    temp_path = None
    try:
        # ✅ Get client (already started = instant)
        client = await get_client()
        if not client:
            logger.error("❌ No client available!")
            return None
        
        # ✅ Check cache first
        if file_id in _file_cache:
            logger.info(f"📦 Cache hit for: {file_id[:20]}...")
            return _file_cache[file_id]
        
        # ✅ Create temp file - Fast
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
        
        logger.info(f"📥 Downloading: {file_id[:20]}...")
        
        # ✅ Download with progress
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path,
            progress=None  # ✅ No progress = Fast
        )
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            logger.info(f"✅ Downloaded! Size: {file_size/1024/1024:.2f} MB")
            
            # ✅ Cache for future
            _file_cache[file_id] = downloaded
            
            # ✅ Auto cleanup after 10 minutes
            asyncio.create_task(auto_cleanup(file_id, downloaded))
            
            return downloaded
        else:
            logger.error("❌ Download failed!")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return None
            
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None

# ============================================================
# AUTO CLEANUP - ✅ PREVENT DISK FULL
# ============================================================
async def auto_cleanup(file_id, file_path):
    """
    Auto delete cached file after 10 minutes
    """
    await asyncio.sleep(600)  # 10 minutes
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            if file_id in _file_cache:
                del _file_cache[file_id]
            logger.info(f"🗑️ Auto cleaned: {file_path}")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

# ============================================================
# GET FILE INFO - ✅ WITH CACHE
# ============================================================
async def get_file_info(file_id):
    """
    Get file information from Telegram - With Cache
    """
    # ✅ Check cache first
    cache_key = f"info_{file_id}"
    if cache_key in _file_cache:
        return _file_cache[cache_key]
    
    try:
        client = await get_client()
        if not client:
            return None
        
        # ✅ Fast get
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
            
            # ✅ Cache it
            _file_cache[cache_key] = info
            return info
        else:
            logger.error("❌ No media found!")
            return None
            
    except Exception as e:
        logger.error(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CHECK FILE EXISTS - ✅ FAST
# ============================================================
async def file_exists(file_id):
    """
    Check if file exists in Telegram - Fast
    """
    try:
        client = await get_client()
        if not client:
            return False
        
        # ✅ Quick check with get_messages
        msg = await client.get_messages(
            chat_id='me',
            message_ids=file_id
        )
        
        return bool(msg and msg.media)
        
    except Exception as e:
        logger.error(f"❌ Check file error: {e}")
        return False

# ============================================================
# CLOSE CLIENT
# ============================================================
async def close_client():
    """
    Close the download client
    """
    global _download_client, _download_client_started, _file_cache
    
    if _download_client and _download_client_started:
        try:
            await _download_client.stop()
            _download_client = None
            _download_client_started = False
            _file_cache.clear()  # ✅ Clear cache on close
            logger.info("❌ Download Client Closed!")
        except Exception as e:
            logger.error(f"❌ Error closing client: {e}")

# ============================================================
# CLEANUP FUNCTION - ✅ SAFE
# ============================================================
def cleanup_temp_file(file_path):
    """
    Delete temporary file safely
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
    return False

# ============================================================
# CLEAR CACHE - ✅ FORCE CLEAN
# ============================================================
def clear_cache():
    """
    Clear download cache
    """
    global _file_cache
    _file_cache.clear()
    logger.info("🗑️ Cache cleared!")

# ============================================================
# GET CACHE SIZE - ✅ MONITOR
# ============================================================
def get_cache_size():
    """
    Get number of cached files
    """
    return len(_file_cache)
