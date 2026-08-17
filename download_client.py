# download_client.py - FINAL FIXED VERSION (COPY PASTE THIS)

import os
import tempfile
import time
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait
from info import API_ID, API_HASH, BOT_TOKEN

# ============================================================
# GLOBALS - SINGLETON CLIENT (Sirf ek baar create hoga)
# ============================================================

_download_client = None
_client_started = False
_file_cache = {}
_file_info_cache = {}

# ============================================================
# GET CLIENT - ONLY ONCE! (Reused for all downloads)
# ============================================================

async def get_client():
    """
    Get or create download client - ONLY ONCE!
    """
    global _download_client, _client_started
    
    # ✅ Agar client already hai to wahi return karo
    if _client_started and _download_client:
        return _download_client
    
    # ✅ Sirf pehli baar client create karo
    if not _client_started:
        print("🚀 Creating download client (ONLY ONCE)...")
        try:
            _download_client = Client(
                name="download_bot",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True,
                workers=20,
                sleep_threshold=30
            )
            await _download_client.start()
            _client_started = True
            print("✅ Download Client Started Successfully!")
            print("ℹ️ Client will be reused for all downloads!")
        except Exception as e:
            print(f"❌ Error starting download client: {e}")
            return None
    
    return _download_client

# ============================================================
# SAFE DOWNLOAD WITH RETRY
# ============================================================

async def safe_download(client, file_id, temp_path, max_retries=2):
    """Download with flood handling"""
    
    for attempt in range(max_retries):
        try:
            return await client.download_media(
                message=file_id,
                file_name=temp_path,
                progress=None
            )
        except FloodWait as e:
            wait = e.value + 1
            print(f"🌊 FloodWait: Waiting {wait}s...")
            await asyncio.sleep(wait)
        except Exception as e:
            if "flood" in str(e).lower() or "429" in str(e).lower():
                wait = 5 * (attempt + 1)
                print(f"🌊 Flood detected, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"❌ Download error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise e
    
    return None

# ============================================================
# DOWNLOAD FILE - FAST WITH CACHE
# ============================================================

async def download_file(file_id, custom_name=None):
    """
    Download file from Telegram - FAST!
    Client is reused, not created each time.
    """
    start_time = time.time()
    
    try:
        # ✅ Check cache first
        if file_id in _file_cache:
            cached_path = _file_cache[file_id]
            if os.path.exists(cached_path):
                print(f"⚡ Cache hit! ({time.time() - start_time:.2f}s)")
                return cached_path
            else:
                del _file_cache[file_id]
        
        # ✅ Get client (reused, not new)
        client = await get_client()
        if not client:
            print("❌ No client available!")
            return None
        
        # ✅ Create temp file
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
        
        print(f"📥 Downloading: {file_id[:20]}...")
        print(f"📁 Temp path: {temp_path}")
        
        # ✅ Safe download
        downloaded = await safe_download(client, file_id, temp_path)
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            # ✅ Save to cache
            _file_cache[file_id] = downloaded
            print(f"✅ Downloaded {file_size/1024/1024:.2f} MB in {time.time() - start_time:.2f}s")
            return downloaded
        else:
            print("❌ Download failed! File not found.")
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# GET FILE INFO WITH CACHE
# ============================================================

async def get_file_info(file_id):
    """
    Get file information from Telegram
    """
    if file_id in _file_info_cache:
        return _file_info_cache[file_id]
    
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
            
            _file_info_cache[file_id] = info
            return info
        else:
            print("❌ No media found in message!")
            return None
            
    except Exception as e:
        print(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CLOSE CLIENT
# ============================================================

async def close_client():
    """
    Close the download client
    """
    global _download_client, _client_started, _file_cache, _file_info_cache
    
    if _download_client and _client_started:
        try:
            await _download_client.stop()
            _download_client = None
            _client_started = False
            _file_cache.clear()
            _file_info_cache.clear()
            print("❌ Download Client Closed!")
        except Exception as e:
            print(f"❌ Error closing client: {e}")

# ============================================================
# CLEANUP
# ============================================================

def cleanup_temp_file(file_path):
    """
    Delete temporary file
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            # Remove from cache
            for key, value in list(_file_cache.items()):
                if value == file_path:
                    del _file_cache[key]
                    break
            print(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    return False
