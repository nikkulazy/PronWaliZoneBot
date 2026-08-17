# fast_client.py - Flood-Safe Multi-Client

from pyrogram import Client
from pyrogram.errors import FloodWait
from info import API_ID, API_HASH, BOT_TOKEN
import random
import time
import asyncio
from collections import defaultdict

# ============================================================
# SMART RATE LIMITER
# ============================================================

class SmartRateLimiter:
    def __init__(self):
        self.usage = defaultdict(list)  # {client_id: [timestamps]}
        self.max_per_minute = 15  # Safe limit to avoid flood
        self.min_interval = 0.5  # 500ms between requests
    
    async def can_use(self, client_id):
        """Check if client can be used"""
        now = time.time()
        timestamps = self.usage[client_id]
        
        # Clean old timestamps (older than 60 seconds)
        timestamps = [t for t in timestamps if now - t < 60]
        self.usage[client_id] = timestamps
        
        # Check if we're at limit
        if len(timestamps) >= self.max_per_minute:
            wait_time = 60 - (now - timestamps[0]) + 1
            if wait_time > 0:
                print(f"⏳ Rate limit: Waiting {wait_time:.1f}s for client {client_id}")
                await asyncio.sleep(wait_time)
                return await self.can_use(client_id)
        
        # Check minimum interval
        if timestamps:
            last = timestamps[-1]
            diff = now - last
            if diff < self.min_interval:
                await asyncio.sleep(self.min_interval - diff)
        
        # Add timestamp
        self.usage[client_id].append(time.time())
        return True

rate_limiter = SmartRateLimiter()

# ============================================================
# CLIENT MANAGER
# ============================================================

class ClientManager:
    def __init__(self):
        self.clients = []
        self.ready = False
        self.loads = {}
        self.client_count = 2  # 2 clients to avoid flood
    
    async def init(self):
        """Initialize clients"""
        if self.ready:
            return
        
        print("\n🚀 Initializing Fast Clients...")
        print("━" * 40)
        
        for i in range(self.client_count):
            try:
                client = Client(
                    name=f"fc_{i}",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN,
                    in_memory=True,
                    workers=10,  # Reduced to avoid flood
                    sleep_threshold=15
                )
                await client.start()
                self.clients.append(client)
                self.loads[i] = 0
                print(f"✅ Client {i+1} Ready!")
            except Exception as e:
                print(f"❌ Client {i+1} failed: {e}")
        
        # Fallback - if no clients created
        if not self.clients:
            print("⚠️ Creating single client as fallback...")
            client = Client(
                name="fallback",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True
            )
            await client.start()
            self.clients.append(client)
            self.loads[0] = 0
        
        self.ready = True
        print("━" * 40)
        print(f"🔥 {len(self.clients)} Clients Ready!\n")
    
    async def get_client(self):
        """Get least loaded client"""
        await self.init()
        
        if not self.clients:
            return None
        
        # Find client with minimum load
        min_load = min(self.loads.values()) if self.loads else 0
        available = [idx for idx, load in self.loads.items() if load <= min_load + 2]
        
        if not available:
            available = list(self.loads.keys())
        
        chosen = random.choice(available)
        
        # Check rate limit
        await rate_limiter.can_use(chosen)
        
        # Update load
        self.loads[chosen] = self.loads.get(chosen, 0) + 1
        
        return self.clients[chosen]
    
    def release_client(self, client):
        """Release client after use"""
        for idx, cl in enumerate(self.clients):
            if cl == client:
                if self.loads.get(idx, 0) > 0:
                    self.loads[idx] -= 1
                break
    
    async def close_all(self):
        """Close all clients"""
        for client in self.clients:
            try:
                await client.stop()
            except:
                pass
        self.clients = []
        self.ready = False
        self.loads.clear()
        rate_limiter.usage.clear()
        print("❌ All clients closed!")

# Global manager instance
manager = ClientManager()

# ============================================================
# SAFE DOWNLOAD WRAPPER
# ============================================================

async def safe_download(client, file_id, temp_path, max_retries=3):
    """Download with flood handling and retry"""
    
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
            error = str(e).lower()
            if "flood" in error or "429" in error:
                wait = (2 ** (attempt + 1)) * 2  # 4, 8, 16 seconds
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
# EXPORT FUNCTIONS
# ============================================================

async def get_client():
    """Get client from manager"""
    return await manager.get_client()

async def init_fast_clients():
    """Initialize clients on bot start"""
    await manager.init()

async def close_all_clients():
    """Close all clients"""
    await manager.close_all()

def get_client_count():
    """Get total clients"""
    return len(manager.clients)

# ============================================================
# PRE-START FUNCTION (Bot Start Pe Call Karein)
# ============================================================

async def pre_start():
    """Pre-start clients on bot boot"""
    print("⚡ Pre-starting fast clients...")
    await init_fast_clients()
