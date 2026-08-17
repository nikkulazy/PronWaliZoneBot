# download_client.py - पूरा fast version

import os
import tempfile
import asyncio
import time
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN

# ========== GLOBALS ==========
_download_client = None
_client_started = False
_file_cache = {}
DOWNLOAD_WORKERS = 20

# ========== FAST CLIENT ==========
async def get_client():
    global _download_client, _client_started
    
    if not _client_started:
        print("🚀 Starting client...")
        _download_client = Client(
            name="download_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True,
            workers=DOWNLOAD_WORKERS,
            sleep_threshold=30
        )
        await _download_client.start()
        _client_started = True
        print("✅ Client ready!")
    
    return _download_client

# ========== FAST DOWNLOAD ==========
async def download_file(file_id, custom_name=None):
    start = time.time()
    
    # 1. Get client (0.1 sec if already started)
    client = await get_client()
    
    # 2. Check cache
    if file_id in _file_cache:
        return _file_cache[file_id]
    
    # 3. Download (fast)
    suffix = '.mp4'
    if custom_name:
        ext = os.path.splitext(custom_name)[1]
        if ext:
            suffix = ext
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
    
    # 4. Download with progress
    downloaded = await client.download_media(
        message=file_id,
        file_name=temp_path
    )
    
    if downloaded and os.path.exists(downloaded):
        _file_cache[file_id] = downloaded  # Cache
        print(f"✅ Downloaded in {time.time() - start:.2f}s")
        return downloaded
    
    return None

# ========== CLEANUP ==========
def cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            # Remove from cache too
            for key, value in list(_file_cache.items()):
                if value == file_path:
                    del _file_cache[key]
                    break
    except:
        pass
