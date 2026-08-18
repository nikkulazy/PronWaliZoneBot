# download_client.py - Ultra Fast Download System with Cache (FIXED)

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
POOL_SIZE = 2  # Reduced from 3 to avoid connection issues
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
            'cache_hits': 0,
            'file_info_cache_hits': 0
        }
        
    async def initialize(self):
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
                    in_memory=True,  # ✅ Fixed: Use in_memory to avoid SQLite lock
                    sleep_threshold=30,
                    max_concurrent_transmissions=5,  # Reduced
                    no_updates=True  # ✅ Add this
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
                    in_memory=True,
                    no_updates=True
                )
                await client.start()
                self.clients.append(client)
                return client
                
            client = self.available.popleft()
            return client
            
    async def return_client(self, client):
        async with self._lock:
            self.available.append(client)
            
    async def get_stats(self):
        return {
            'total_clients': len(self.clients),
            'available': len(self.available),
            'busy': len(self.clients) - len(self.available),
            'downloads': self._stats
        }
        
    async def close_all(self):
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
# FILE INFO CACHE - ULTRA FAST
# ============================================================
class FileInfoCache:
    """Multi-layer file info cache - Memory only (no disk to avoid lock)"""
    
    def __init__(self):
        self.memory_cache = {}
        self._lock = asyncio.Lock()
        
    def get(self, file_id):
        if file_id in self.memory_cache:
            return self.memory_cache[file_id]
        return None
        
    def set(self, file_id, info):
        self.memory_cache[file_id] = info
        
    def clear(self):
        self.memory_cache.clear()
        
    def get_stats(self):
        return {
            'memory_size': len(self.memory_cache)
        }

# ============================================================
# CACHE MANAGER - FILE CACHE
# ============================================================
class CacheManager:
    def __init__(self, cache_dir=CACHE_DIR, max_age_hours=MAX_CACHE_AGE_HOURS, max_size_gb=MAX_CACHE_SIZE_GB):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_age = timedelta(hours=max_age_hours)
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
        self._lock = asyncio.Lock()
        
    def _load_metadata(self):
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def _save_metadata(self):
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"❌ Metadata save error: {e}")
            
    def get_cached_path(self, file_id):
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
        try:
            file_hash = hashlib.md5(file_id.encode()).hexdigest()
            ext = os.path.splitext(file_path)[1] or '.mp4'
            cache_filename = f"{file_hash}{ext}"
            cache_path = self.cache_dir / cache_filename
            
            shutil.copy2(file_path, cache_path)
            
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
                
            return deleted_count, deleted_size
            
    async def cleanup_by_size(self):
        async with self._lock:
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
                    
            if total_size > self.max_size_bytes:
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
        return deleted_count, deleted_size
        
    def get_stats(self):
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
_file_info_cache = FileInfoCache()

# ============================================================
# PROGRESS CALLBACK
# ============================================================
def progress_callback(current, total, file_id):
    if total > 0:
        percent = (current / total) * 100
        mb_downloaded = current / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        
        if int(percent) % 10 == 0 and percent > 0:
            print(f"⬇️ {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)")

# ============================================================
# FAST FILE INFO FUNCTIONS
# ============================================================
async def get_cached_file_info(file_id, force_fetch=False):
    """
    Get file info with caching - FIXED
    """
    # Step 1: Check cache (instant)
    if not force_fetch:
        cached = _file_info_cache.get(file_id)
        if cached:
            _pool._stats['file_info_cache_hits'] += 1
            return cached
            
    # Step 2: Fetch from Telegram (only first time)
    try:
        client = await _pool.get_client()
        if not client:
            return None
            
        try:
            # ✅ FIX: Use get_messages with proper error handling
            try:
                msg = await client.get_messages(
                    chat_id='me',
                    message_ids=int(file_id) if file_id.isdigit() else file_id
                )
            except:
                # If int conversion fails, use as string
                msg = await client.get_messages(
                    chat_id='me',
                    message_ids=file_id
                )
            
            if msg and msg.media:
                media = msg.media
                
                # ✅ FIX: Handle different media types
                if hasattr(media, 'file_id'):
                    info = {
                        'file_id': media.file_id,
                        'file_unique_id': getattr(media, 'file_unique_id', ''),
                        'file_name': getattr(media, 'file_name', 'unknown'),
                        'file_size': getattr(media, 'file_size', 0),
                        'mime_type': getattr(media, 'mime_type', 'video/mp4'),
                        'duration': getattr(media, 'duration', 0),
                        'width': getattr(media, 'width', 0),
                        'height': getattr(media, 'height', 0)
                    }
                    
                    # Cache for future
                    _file_info_cache.set(file_id, info)
                    return info
                else:
                    # Try to get from document
                    if hasattr(media, 'file_id'):
                        info = {
                            'file_id': media.file_id,
                            'file_unique_id': getattr(media, 'file_unique_id', ''),
                            'file_name': getattr(media, 'file_name', 'unknown'),
                            'file_size': getattr(media, 'file_size', 0),
                            'mime_type': getattr(media, 'mime_type', 'video/mp4'),
                            'duration': 0,
                            'width': 0,
                            'height': 0
                        }
                        _file_info_cache.set(file_id, info)
                        return info
                
        finally:
            await _pool.return_client(client)
                
    except Exception as e:
        print(f"❌ File info fetch error: {e}")
        
    return None

# ============================================================
# BULK PRE-FETCH - DISABLED TO AVOID ISSUES
# ============================================================
async def pre_fetch_file_info(file_ids, max_concurrent=2):
    """
    Pre-fetch multiple file infos - LIMITED to avoid issues
    """
    if not file_ids:
        return 0
        
    # ✅ Only fetch first 10 files to avoid overload
    file_ids = file_ids[:10]
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_one(file_id):
        async with semaphore:
            return await get_cached_file_info(file_id)
            
    tasks = [fetch_one(file_id) for file_id in file_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    return success_count

# ============================================================
# ULTRA FAST DOWNLOAD
# ============================================================
async def download_file_fast(file_id, custom_name=None, progress_cb=None):
    """
    ULTRA FAST download with pre-fetched info
    """
    client = None
    temp_path = None
    
    try:
        # Get client
        client = await _pool.get_client()
        
        # Get file info (from cache if available)
        file_info = await get_cached_file_info(file_id)
        
        # Create temp file
        suffix = '.mp4'
        if custom_name:
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
                
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            
        # START DOWNLOAD
        print(f"📥 Downloading: {file_id[:20]}...")
        if file_info:
            file_size_mb = file_info.get('file_size', 0) / (1024 * 1024)
            print(f"📁 Size: {file_size_mb:.2f}MB")
        
        start_time = time.time()
        
        # Download with progress
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path,
            progress=progress_cb or progress_callback,
            progress_args=(file_id,)
        )
        
        elapsed = time.time() - start_time
        
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            _pool._stats['successful'] += 1
            speed = file_size / elapsed / (1024 * 1024) if elapsed > 0 else 0
            print(f"\n✅ Downloaded {file_size/1024/1024:.2f}MB in {elapsed:.2f}s ({speed:.1f}MB/s)")
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

# ============================================================
# MAIN DOWNLOAD FUNCTIONS
# ============================================================
async def download_with_cache(file_id, custom_name=None):
    """
    Download with cache - FASTEST OPTION
    """
    # Check cache
    cached_path = _cache.get_cached_path(file_id)
    if cached_path:
        _pool._stats['cache_hits'] += 1
        print("⚡ Returning from cache!")
        return cached_path
        
    # Download fresh
    downloaded = await download_file_fast(file_id, custom_name)
    
    # Save to cache
    if downloaded and os.path.exists(downloaded):
        _cache.save_to_cache(file_id, downloaded)
        
    return downloaded

# ============================================================
# COMPATIBILITY FUNCTIONS
# ============================================================
async def get_client():
    return await _pool.get_client()

async def download_file(file_id, custom_name=None):
    """Main download function - ULTRA FAST"""
    return await download_with_cache(file_id, custom_name)

async def get_file_info(file_id):
    """Get file info with cache"""
    return await get_cached_file_info(file_id)

async def close_client():
    await _pool.close_all()

def cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Temp file deleted: {file_path}")
            return True
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    return False

async def init_download_system():
    """Initialize download system - Call at bot start"""
    await _pool.initialize()
    asyncio.create_task(_cache.auto_cleanup_loop())
    
    # ✅ Skip pre-fetch to avoid issues
    print("✅ Download System Initialized (Pre-fetch disabled)")
    
    return _pool, _cache

async def get_download_stats():
    pool_stats = await _pool.get_stats()
    cache_stats = _cache.get_stats()
    file_info_stats = _file_info_cache.get_stats()
    
    return {
        'pool': pool_stats,
        'cache': cache_stats,
        'file_info_cache': file_info_stats
    }
