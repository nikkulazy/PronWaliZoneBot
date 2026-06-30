# download_client.py - Apna Khud Ka Download Client

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

# ============================================================
# CLIENT START / GET
# ============================================================
async def get_client():
    """
    Get or create download client
    Yeh function client ko start karega agar already start nahi hai
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
                in_memory=True  # Memory mein store, file nahi banegi
            )
            await _download_client.start()
            _download_client_started = True
            print("✅ Download Client Started Successfully!")
        except Exception as e:
            print(f"❌ Error starting download client: {e}")
            return None
    
    return _download_client

# ============================================================
# DOWNLOAD FILE FUNCTION
# ============================================================
async def download_file(file_id, custom_name=None):
    """
    Download file from Telegram
    
    Parameters:
    - file_id: Telegram file ID
    - custom_name: Custom file name (optional)
    
    Returns:
    - Downloaded file path (string) or None if failed
    """
    try:
        # Get client
        client = await get_client()
        if not client:
            print("❌ No client available!")
            return None
        
        # Create temp file
        suffix = '.mp4'
        if custom_name:
            # Get extension from custom name
            ext = os.path.splitext(custom_name)[1]
            if ext:
                suffix = ext
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
        
        print(f"📥 Downloading file: {file_id[:20]}...")
        print(f"📁 Temp path: {temp_path}")
        
        # Download the file
        downloaded = await client.download_media(
            message=file_id,
            file_name=temp_path
        )
        
        # Check if download was successful
        if downloaded and os.path.exists(downloaded):
            file_size = os.path.getsize(downloaded)
            print(f"✅ Download successful! Size: {file_size} bytes")
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
# GET FILE INFO FUNCTION
# ============================================================
async def get_file_info(file_id):
    """
    Get file information from Telegram
    
    Parameters:
    - file_id: Telegram file ID
    
    Returns:
    - Dictionary with file info or None
    """
    try:
        client = await get_client()
        if not client:
            return None
        
        # Get message with file
        msg = await client.get_messages(
            chat_id='me',  # 'me' means bot itself
            message_ids=file_id
        )
        
        if msg and msg.media:
            # Get media type
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
            print("❌ No media found in message!")
            return None
            
    except Exception as e:
        print(f"❌ Get file info error: {e}")
        return None

# ============================================================
# CLOSE CLIENT FUNCTION
# ============================================================
async def close_client():
    """
    Close the download client
    Clean up resources
    """
    global _download_client, _download_client_started
    
    if _download_client and _download_client_started:
        try:
            await _download_client.stop()
            _download_client = None
            _download_client_started = False
            print("❌ Download Client Closed!")
        except Exception as e:
            print(f"❌ Error closing client: {e}")

# ============================================================
# SEND FILE TO USER FUNCTION
# ============================================================
async def send_file_to_user(chat_id, file_path, caption=""):
    """
    Send file to a user/chat
    
    Parameters:
    - chat_id: User or chat ID
    - file_path: File path to send
    - caption: Optional caption
    
    Returns:
    - Sent message object or None
    """
    try:
        client = await get_client()
        if not client:
            return None
        
        msg = await client.send_document(
            chat_id=chat_id,
            document=file_path,
            caption=caption,
            protect_content=True
        )
        
        print(f"✅ File sent to {chat_id}")
        return msg
        
    except Exception as e:
        print(f"❌ Send file error: {e}")
        return None

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
# FOR ROUTE.PY - DIRECT DOWNLOAD FUNCTION
# ============================================================
async def download_and_serve(file_id, user_id):
    """
    Download and serve file - One function for everything
    
    Parameters:
    - file_id: Telegram file ID
    - user_id: User ID for naming
    
    Returns:
    - (file_content, file_name, file_size) or (None, None, None)
    """
    try:
        # Download file
        downloaded_path = await download_file(file_id)
        
        if not downloaded_path:
            return None, None, None
        
        # Read file
        with open(downloaded_path, 'rb') as f:
            file_content = f.read()
        
        file_size = len(file_content)
        file_name = f"video_{user_id}.mp4"
        
        # Cleanup temp file
        cleanup_temp_file(downloaded_path)
        
        return file_content, file_name, file_size
        
    except Exception as e:
        print(f"❌ Download and serve error: {e}")
        return None, None, None

# ============================================================
# TEST FUNCTION (Optional - For Testing)
# ============================================================
async def test_download(file_id):
    """
    Test function to check if download works
    Usage: asyncio.run(test_download("BA..."))
    """
    print(f"🧪 Testing download for: {file_id[:20]}...")
    
    result = await download_file(file_id)
    
    if result:
        print(f"✅ Test passed! File saved at: {result}")
        # Cleanup
        cleanup_temp_file(result)
    else:
        print("❌ Test failed!")
    
    # Close client
    await close_client()

# ============================================================
# AUTO CLEANUP ON EXIT
# ============================================================
import atexit

def auto_cleanup():
    """Auto cleanup when program exits"""
    print("🔄 Running auto cleanup...")
    # Client ko close karne ke liye async function call nahi kar sakte,
    # isliye sirf print karte hain
    print("⚠️ Please run: asyncio.run(close_client()) to close properly")

atexit.register(auto_cleanup)
