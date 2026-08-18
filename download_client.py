# download_client.py - Fast Download Client with Pool + Cache

import os
import tempfile
import asyncio
import time
import shutil
import hashlib
import json
from pathlib import Path
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN
from collections import deque
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
POOL_SIZE = 3  # Number of concurrent clients
CACHE_DIR = "download_cache"
MAX_CACHE_AGE_HOURS = 24
MAX_CACHE_SIZE_GB = 5
CLEANUP_INTERVAL_HOURS = 6

# ============================================================
# CLIENT POOL CLASS
# ============================================================
class ClientPool:
    def __init__(self, pool_size=POOL_SIZE):
        self.pool_size = pool_size
        self.clients = []
        self.available = deque()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._stats = {
            'total_downloads': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0
        }
        
    async def initialize(self):
        """Initialize all clients in pool"""
        if self._initialized:
            return
            
        print(f"🔄 Creating {self.pool_size} download clients...")
        start_time = time.time()
        
        for i in range(self.pool_size):
            try:
                client = Client(
                    name=f"download_bot_{i}",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN,
                    in_memory=False,
                    sleep_threshold=30,
                    max_concurrent_transmissions=10
                )
                
                await client.start()
                self.clients.append(client)
                self.available.append(client)
                print(f"✅ Client {i+1}/{self.pool_size} ready")
                
            except Exception as e:
                print(f"❌ Client {i+1} failed: {e}")
                
        self._initialized = True
        elapsed = time.time() - start_time
        print(f"✅ All clients ready in {elapsed:.2f}s")
        return True
        
    async def get_client(self):
        """Get available client from pool"""
        async with self._lock:
            if not self._initialized:
                await self.initialize()
                
            retry_count = 0
            while not self.available and retry_count < 30:
                await asyncio.sleep(0.1)
                retry_count += 1
                
            if not self.available:
                print("⚠️ No client available, creating new one...")
                client = Client(
                    name=f"download_bot_temp",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN,
                    in_memory=False
                )
                await client.start()
                self.clients.append(client)
                return client
                
            client = self.available.popleft()
            return client
            
    async def return_client(self, client):
        """Return client to pool"""
        async with self._lock:
            self.available.append(client)
            
    async def get_stats(self):
        """Get pool statistics"""
        return {
            'total_clients': len(self.clients),
            'available': len(self.available),
            'busy': len(self.clients) - len(self.available),
            'downloads': self._stats
        }
        
    async def close_all(self):
        """Close all clients"""
        print("🔄 Closing all clients...")
        for client in self.clients:
            try:
                await client.stop()
            except:
                pass
        self.clients.clear()
        self.available.clear()
        self._initialized = False
        print("✅ All clients closed")

# ============================================================
# CACHE MANAGER CLASS
# ============================================================
class CacheManager:
    def __init__(self, cache_dir=CACHE_DIR, max_age_hours=MAX_CACHE_AGE_HOURS, max_size_gb=MAX_CACHE_SIZE_GB):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_age = timedelta(hours=max_age_hours)
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
        self._cleanup_running = False
        self._lock = asyncio.Lock()
        
    def _load_metadata(self):
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def _save_metadata(self):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"❌ Metadata save error: {e}")
            
    def get_cached_path(self, file_id):
        """Get file path from cache"""
        if file_id in self.metadata:
            cache_info = self.metadata[file_id]
            cache_path = self.cache_dir / cache_info['filename']
            
            if cache_path.exists():
                age = datetime.now() - datetime.fromisoformat(cache_info['timestamp'])
                if age < self.max_age:
                    self.metadata[file_id]['last_accessed'] = datetime.now().isoformat()
                    self._save_metadata()
                    return str(cache_path)
                else:
                    cache_path.unlink(missing_ok=True)
                    del self.metadata[file_id]
                    self._save_metadata()
        return None
        
    def save_to_cache(self, file_id, file_path):
        """Save file to cache"""
        try:
            file_hash = hashlib.md5(file_id.encode()).hexdigest()
            ext = os.path.splitext(file_path)[1] or '.mp4'
            cache_filename = f"{file_hash}{ext}"
            cache_path = self.cache_dir / cache_filename
            
            # Copy file to cache
            shutil.copy2(file_path, cache_path)
            
            # Save metadata
            file_size = os.path.getsize(cache_path)
            self.metadata[file_id] = {
                'filename': cache_filename,
                'timestamp': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'size': file_size
            }
            self._save_metadata()
            print(f"💾 Cached: {cache_filename} ({file_size/1024/1024:.2f}MB)")
            return True
            
        except Exception as e:
            print(f"❌ Cache save error: {e}")
            return False
            
    async def cleanup_old_files(self):
        """Remove old cache files"""
        async with self._lock:
            print("🧹 Running cache cleanup...")
            deleted_count = 0
            deleted_size = 0
            
            to_delete = []
            for file_id, info in self.metadata.items():
                age = datetime.now() - datetime.fromisoformat(info['timestamp'])
                if age > self.max_age:
                    to_delete.append(file_id)
                    
            for file_id in to_delete:
                info = self.metadata[file_id]
                cache_path = self.cache_dir / info['filename']
                if cache_path.exists():
                    size = os.path.getsize(cache_path)
                    cache_path.unlink()
                    deleted_size += size
                    deleted_count += 1
                del self.metadata[file_id]
                
            if deleted_count > 0:
                self._save_metadata()
                print(f"🗑️ Deleted {deleted_count} old files ({deleted_size/1024/1024:.2f}MB)")
            else:
                print("✅ No old files to delete")
                
            return deleted_count, deleted_size
            
    async def cleanup_by_size(self):
        """Cleanup if cache exceeds max size"""
        async with self._lock:
            print("📊 Checking cache size...")
            total_size = 0
            files = []
            
            for file_id, info in self.metadata.items():
                cache_path = self.cache_dir / info['filename']
                if cache_path.exists():
                    size = os.path.getsize(cache_path)
                    total_size += size
                    files.append({
                        'file_id': file_id,
                        'path': cache_path,
                        'size': size,
                        'timestamp': datetime.fromisoformat(info['timestamp'])
                    })
                    
            print(f"📊 Current cache size: {total_size/1024/1024/1024:.2f}GB")
            
            if total_size > self.max_size_bytes:
                print(f"⚠️ Cache exceeded {self.max_size_bytes/1024/1024/1024:.2f}GB limit")
                
                files.sort(key=lambda x: x['timestamp'])
                deleted_count = 0
                deleted_size = 0
                
                for file in files:
                    if total_size <= self.max_size_bytes * 0.8:
                        break
                        
                    file['path'].unlink(missing_ok=True)
                    del self.metadata[file['file_id']]
                    deleted_size += file['size']
                    total_size -= file['size']
                    deleted_count += 1
                    
                if deleted_count > 0:
                    self._save_metadata()
                    print(f"🗑️ Deleted {deleted_count} files to free {deleted_size/1024/1024:.2f}MB")
                    
            return total_size
            
    async def auto_cleanup_loop(self, interval_hours=CLEANUP_INTERVAL_HOURS):
        """Background auto cleanup task"""
        while True:
            await asyncio.sleep(interval_hours * 3600)
            try:
                print(f"\n🔄 Auto cleanup started at {datetime.now()}")
                await self.cleanup_old_files()
                await self.cleanup_by_size()
                print(f"✅ Auto cleanup completed at {datetime.now()}\n")
            except Exception as e:
                print(f"❌ Auto cleanup error: {e}")
                
    def clear_all_cache(self):
        """Clear entire cache manually"""
        print("🗑️ Clearing all cache...")
        deleted_count = 0
        deleted_size = 0
        
        for info in self.metadata.values():
            cache_path = self.cache_dir / info['filename']
            if cache_path.exists():
                size = os.path.getsize(cache_path)
                cache_path.unlink()
                deleted_size += size
                deleted_count += 1
                
        self.metadata = {}
        self._save_metadata()
        print(f"🗑️ Deleted {deleted_count} files ({deleted_size/1024/1024:.2f}MB)")
        return deleted_count, deleted_size
        
    def get_stats(self):
        """Get cache statistics"""
        total_files = len(self.metadata)
        total_size = 0
        
        for info in self.metadata.values():
            cache_path = self.cache_dir / info['filename']
            if cache_path.exists():
                total_size += os.path.getsize(cache_path)
                
        return {
            'total_files': total_files,
            'total_size_gb': total_size / (1024**3),
            'max_size_gb': self.max_size_bytes / (1024**3),
            'cache_dir': str(self.cache_dir)
        }

# ============================================================
# GLOBAL INSTANCES
# ============================================================
_pool = ClientPool(pool_size=POOL_SIZE)
_cache = CacheManager()

# ============================================================
# FAST DOWNLOAD FUNCTIONS
# ============================================================
async def download_file_fast(file_id, custom_name=None):
    """
    Fast download using client pool
    """
    client = None
    temp_path = None
    
    try:
        client = await _pool.get_client()
        
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
                
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            
        print(f"📥 Downloading: {file_id[:20]}...")
        start_time = time.time()
        
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path
        )
        
        elapsed = time.time() - start_time
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            _pool._stats['successful'] += 1
            print(f"✅ Downloaded {file_size/1024/1024:.2f}MB in {elapsed:.2f}s")
            return downloaded
        else:
            _pool._stats['failed'] += 1
            print("❌ Download failed!")
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        _pool._stats['failed'] += 1
        return None
    finally:
        _pool._stats['total_downloads'] += 1
        if client:
            await _pool.return_client(client)

async def download_with_cache(file_id, custom_name=None):
    """
    Download with cache - Fastest option
    """
    # 1. Check cache first
    cached_path = _cache.get_cached_path(file_id)
    if cached_path:
        _pool._stats['cache_hits'] += 1
        print("⚡ Returning from cache!")
        return cached_path
        
    # 2. Download fresh
    print("📥 Cache miss, downloading...")
    downloaded = await download_file_fast(file_id, custom_name)
    
    # 3. Save to cache
    if downloaded and os.path.exists(downloaded):
        _cache.save_to_cache(file_id, downloaded)
        
    return downloaded

# ============================================================
# ORIGINAL FUNCTIONS (For compatibility with existing code)
# ============================================================
async def get_client():
    """Get client from pool (compatibility)"""
    return await _pool.get_client()

async def download_file(file_id, custom_name=None):
    """Download file with cache (compatibility)"""
    return await download_with_cache(file_id, custom_name)

async def get_file_info(file_id):
    """Get file info from Telegram"""
    try:
        client = await _pool.get_client()
        try:
            msg = await client.get_messages(
                chat_id='me',
                message_ids=file_id
            )
            
            if msg and msg.media:
                media_type = msg.media.value
                media = getattr(msg, media_type)
                
                return {
                    'file_id': media.file_id,
                    'file_unique_id': media.file_unique_id,
                    'file_name': getattr(media, 'file_name', 'unknown'),
                    'file_size': getattr(media, 'file_size', 0),
                    'mime_type': getattr(media, 'mime_type', 'video/mp4'),
                    'duration': getattr(media, 'duration', 0),
                    'width': getattr(media, 'width', 0),
                    'height': getattr(media, 'height', 0)
                }
            else:
                return None
        finally:
            await _pool.return_client(client)
            
    except Exception as e:
        print(f"❌ Get file info error: {e}")
        return None

async def close_client():
    """Close all clients"""
    await _pool.close_all()

def cleanup_temp_file(file_path):
    """Delete temporary file"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    return False

# ============================================================
# INITIALIZATION FUNCTION
# ============================================================
async def init_download_system():
    """Initialize download system - Call this at bot start"""
    await _pool.initialize()
    # Start auto cleanup in background
    asyncio.create_task(_cache.auto_cleanup_loop())
    return _pool, _cache

async def get_download_stats():
    """Get system statistics"""
    pool_stats = await _pool.get_stats()
    cache_stats = _cache.get_stats()
    return {
        'pool': pool_stats,
        'cache': cache_stats
    }
