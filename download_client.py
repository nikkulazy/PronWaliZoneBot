# download_client.py - Flood-Safe Download

import os
import tempfile
import time
from fast_client import get_client, safe_download, manager, close_all_clients

# ============================================================
# CACHE FOR FAST ACCESS
# ============================================================

_file_cache = {}
_file_info_cache = {}

# ============================================================
# DOWNLOAD WITH FLOOD PROTECTION
# ============================================================

async def download_file(file_id, custom_name=None):
    """
    Download file with flood protection
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
        
        # ✅ Get client
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
        
        # ✅ Safe download with flood handling
        print(f"📥 Downloading: {file_id[:20]}...")
        downloaded = await safe_download(client, file_id, temp_path)
        
        # ✅ Release client
        manager.release_client(client)
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            # ✅ Save to cache
            _file_cache[file_id] = downloaded
            print(f"✅ Downloaded {file_size/1024/1024:.2f} MB in {time.time() - start_time:.2f}s")
            return downloaded
        
        print("❌ Download failed!")
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
    Get file information with caching
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
        
        manager.release_client(client)
        
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
            
            # ✅ Save to cache
            _file_info_cache[file_id] = info
            return info
        
        return None
        
    except Exception as e:
        print(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CLEANUP FUNCTION
# ============================================================

def cleanup_temp_file(file_path):
    """
    Delete temporary file and remove from cache
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            # Remove from cache
            for key, value in list(_file_cache.items()):
                if value == file_path:
                    del _file_cache[key]
                    break
            print(f"🗑️ Cleaned: {os.path.basename(file_path)}")
            return True
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    return False

# ============================================================
# CLOSE FUNCTIONS
# ============================================================

async def close_client():
    """Close all download clients"""
    await close_all_clients()
    _file_cache.clear()
    _file_info_cache.clear()
    print("✅ All clients and cache cleared!")

def clear_cache():
    """Clear download cache"""
    _file_cache.clear()
    _file_info_cache.clear()
    print("🗑️ Cache cleared!")
