# download_client.py - OPTIMIZED VERSION (Faster than before)

import os
import tempfile
import asyncio
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN

# ============================================================
# GLOBAL VARIABLES
# ============================================================
_download_client = None
_download_client_started = False
_download_queue = {}
_downloading = set()

# ============================================================
# CLIENT START / GET
# ============================================================
async def get_client():
    """
    Get or create download client
    """
    global _download_client, _download_client_started
    
    if not _download_client:
        try:
            print("🔄 Creating new download client...")
            _download_client = Client(
                name="download_bot",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True,
                workers=20,  # More workers for faster downloads
            )
            await _download_client.start()
            _download_client_started = True
            print("✅ Download Client Started Successfully!")
        except Exception as e:
            print(f"❌ Error starting download client: {e}")
            return None
    
    return _download_client

# ============================================================
# DOWNLOAD FILE WITH PROGRESS
# ============================================================
async def download_file(file_id, custom_name=None, progress_callback=None):
    """
    Download file from Telegram with progress tracking
    """
    try:
        # Check if already downloading
        if file_id in _downloading:
            print(f"⏳ File {file_id[:20]} already downloading...")
            # Wait for it to complete
            while file_id in _downloading:
                await asyncio.sleep(1)
            # Return cached path
            if file_id in _download_queue:
                return _download_queue[file_id]
            return None
        
        _downloading.add(file_id)
        
        client = await get_client()
        if not client:
            _downloading.remove(file_id)
            return None
        
        # Create temp file with better naming
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
        
        temp_path = f"/tmp/{file_id[:10]}_{int(asyncio.get_event_loop().time())}{suffix}"
        
        print(f"📥 Downloading file: {file_id[:20]}...")
        print(f"📁 Temp path: {temp_path}")
        
        # Download with progress
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path,
            progress=progress_callback if progress_callback else None
        )
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            print(f"✅ Download successful! Size: {file_size} bytes")
            _download_queue[file_id] = downloaded
            _downloading.remove(file_id)
            return downloaded
        else:
            print("❌ Download failed! File not found.")
            _downloading.remove(file_id)
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        if file_id in _downloading:
            _downloading.remove(file_id)
        return None

# ============================================================
# STREAM DOWNLOAD (Chunk by Chunk)
# ============================================================
async def stream_file(file_id, chunk_size=1024*1024):
    """
    Stream file from Telegram in chunks (For direct streaming)
    """
    try:
        client = await get_client()
        if not client:
            yield b""
            return
        
        # Get the message
        msg = await client.get_messages('me', ids=file_id)
        if not msg or not msg.media:
            yield b""
            return
        
        # Get media info
        media_type = msg.media.value
        media = getattr(msg, media_type)
        file_size = getattr(media, 'file_size', 0)
        
        if file_size == 0:
            yield b""
            return
        
        # Download in chunks and yield
        downloaded = 0
        while downloaded < file_size:
            chunk = await client.download_media(
                message=file_id,
                file_name=None,
                in_memory=True,
                chunk_size=chunk_size
            )
            if chunk:
                yield chunk.getvalue() if hasattr(chunk, 'getvalue') else chunk
                downloaded += len(chunk)
            else:
                break
                
    except Exception as e:
        print(f"❌ Stream error: {e}")
        yield b""

# ============================================================
# GET FILE INFO (Cached)
# ============================================================
_file_info_cache = {}

async def get_file_info(file_id):
    """
    Get file information from Telegram with caching
    """
    try:
        # Check cache
        if file_id in _file_info_cache:
            return _file_info_cache[file_id]
        
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
            
            # Cache for 5 minutes
            _file_info_cache[file_id] = info
            asyncio.create_task(clear_cache_after(file_id, 300))
            
            return info
        else:
            print("❌ No media found in message!")
            return None
            
    except Exception as e:
        print(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CLEAR CACHE
# ============================================================
async def clear_cache_after(file_id, seconds):
    await asyncio.sleep(seconds)
    if file_id in _file_info_cache:
        del _file_info_cache[file_id]

# ============================================================
# CLOSE CLIENT
# ============================================================
async def close_client():
    """
    Close the download client
    """
    global _download_client, _download_client_started, _download_queue
    
    if _download_client and _download_client_started:
        try:
            await _download_client.stop()
            _download_client = None
            _download_client_started = False
            _download_queue.clear()
            print("❌ Download Client Closed!")
        except Exception as e:
            print(f"❌ Error closing client: {e}")

# ============================================================
# CLEANUP FUNCTION
# ============================================================
def cleanup_temp_file(file_path):
    """
    Delete temporary file
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    return False

# ============================================================
# PROGRESS CALLBACK
# ============================================================
async def progress_callback(current, total):
    """Simple progress callback"""
    percent = (current / total) * 100 if total else 0
    if int(percent) % 10 == 0:  # Log every 10%
        print(f"⬇️ Download progress: {percent:.1f}%")
