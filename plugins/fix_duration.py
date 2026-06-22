from pyrogram import Client, filters
from pyrogram.types import Message
from database.users_db import db
from info import ADMINS

@Client.on_message(filters.command("fixduration") & filters.user(ADMINS))
async def fix_duration_command(client, message: Message):
    """
    Admin command to fix missing duration in old videos
    Usage: /fixduration
    """
    msg = await message.reply("🔄 **Fixing video durations... Please wait.**")
    
    try:
        # Get all videos without duration field
        cursor = db.videos.find({"duration": {"$exists": False}})
        videos = await cursor.to_list(length=None)
        
        if not videos:
            return await msg.edit("✅ No videos found without duration field.")
        
        total = len(videos)
        updated = 0
        failed = 0
        
        await msg.edit(f"🔄 Found {total} videos without duration. Fixing...")
        
        for video in videos:
            try:
                file_id = video["file_id"]
                # Note: Video duration fetch nahi kar sakte directly without message
                # Isliye hum default value 0 set kar rahe hain
                # Aap chahe toh manually update kar sakte hain
                await db.videos.update_one(
                    {"_id": video["_id"]},
                    {"$set": {"duration": 0}}  # Default 0 means free video
                )
                updated += 1
            except Exception as e:
                failed += 1
                print(f"Error updating video {video.get('file_id', 'unknown')}: {e}")
        
        await msg.edit(
            f"✅ **Duration Fix Completed!**\n\n"
            f"📊 Total videos found: {total}\n"
            f"✅ Updated: {updated}\n"
            f"❌ Failed: {failed}\n\n"
            f"⚠️ Note: All old videos have been set to duration 0 (FREE).\n"
            f"To change, manually update in database or re-index videos."
        )
        
    except Exception as e:
        await msg.edit(f"❌ Error: {str(e)}")
