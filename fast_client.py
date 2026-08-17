# fast_client.py - Simple Fast Single Client

from pyrogram import Client
from pyrogram.errors import FloodWait
from info import API_ID, API_HASH, BOT_TOKEN
import time
import asyncio

# ============================================================
# SINGLE FAST CLIENT
# ============================================================

_client = None
_client_started = False
_last_used = 0
MIN_INTERVAL = 0.3  # 300ms between requests

# ============================================================
# GET CLIENT
# ============================================================

async def get_client():
    """
    Get or create single fast client
    """
    global _client, _client_started, _last_used
    
    # ✅ Create client if not started
    if not _client_started:
        print("\n🚀 Starting Fast Download Client...")
        print("━" * 40)
        try:
            _client = Client(
                name="fast_dl",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True,      # ✅ Fast - no disk I/O
                workers=50,          # ✅ Fast - parallel processing
                sleep_threshold=5,   # ✅ Fast - quick response
                max_concurrent_transmissions=10
            )
            await _client.start()
            _client_started = True
            print("✅ Fast Client Ready!")
            print("━" * 40)
            print("ℹ️ Single client mode - No flood wait\n")
        except FloodWait as e:
            wait = e.value + 1
            print(f"🌊 FloodWait: Waiting {wait}s...")
            await asyncio.sleep(wait)
            return await get_client()
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    # ✅ Rate limiting - minimum gap between requests
    now = time.time()
    time_since_last = now - _last_used
    if time_since_last < MIN_INTERVAL:
        wait_time = MIN_INTERVAL - time_since_last
        await asyncio.sleep(wait_time)
    
    _last_used = time.time()
    return _client

# ============================================================
# SAFE DOWNLOAD WITH RETRY
# ============================================================

async def safe_download(client, file_id, temp_path, max_retries=3):
    """
    Download with flood handling and auto-retry
    """
    for attempt in range(max_retries):
        try:
            return await client.download_media(
                message=file_id,
                file_name=temp_path,
                progress=None  # ✅ Faster without progress
            )
        except FloodWait as e:
            wait = e.value + 1
            print(f"🌊 FloodWait: Waiting {wait}s...")
            await asyncio.sleep(wait)
        except Exception as e:
            error = str(e).lower()
            if "flood" in error or "429" in error:
                wait = (2 ** (attempt + 1)) * 2
                print(f"🌊 Flood detected, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"❌ Download error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise e
    
    return None

# ============================================================
# PRE-START FUNCTION (Bot Start Pe Call Karein)
# ============================================================

async def init_fast_clients():
    """Initialize client on bot start"""
    client = await get_client()
    if client:
        print("✅ Fast Client Pre-Started!")
    return client

async def close_all_clients():
    """Close client"""
    global _client, _client_started
    if _client and _client_started:
        try:
            await _client.stop()
        except:
            pass
    _client = None
    _client_started = False
    print("❌ Client closed!")

def get_client_count():
    """Get client count (always 1)"""
    return 1 if _client_started else 0

async def pre_start():
    """Pre-start client on bot boot"""
    print("⚡ Pre-starting fast client...")
    await init_fast_clients()
