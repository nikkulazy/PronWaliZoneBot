import asyncio
from database.users_db import db
from utils import temp, auto_delete_message

async def send_requested_file(client, message, user_id, search_id):
    try:
        print(f"🔍 [SEND_FILE] Searching for: {search_id}")
        
        # ✅ FIX: Pehle file_unique_id se search karo
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        
        # ✅ FIX: Agar nahi mila toh file_id se search karo
        if not file_data:
            print(f"⚠️ [SEND_FILE] Not found by unique_id, trying file_id...")
            file_data = await db.videos.find_one({"file_id": search_id})
            
        if not file_data:
            print(f"❌ [SEND_FILE] File not found: {search_id}")
            return await message.reply("❌ File not found. It may have been deleted.")
        
        print(f"✅ [SEND_FILE] File found: {file_data.get('file_id')}")

        dlt = await message.reply_video(
            video=file_data['file_id'],
            caption=(
                f"<i>𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.U_NAME}</i>\n\n"
                f"<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ. ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>"
            )
        )
        asyncio.create_task(auto_delete_message(message, dlt))

    except Exception as e:
        print(f"❌ Error sending file: {e}")
        await message.reply("❌ Error: File might be deleted or inaccessible.")
