import asyncio
from database.users_db import db
from utils import temp, auto_delete_message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import PROTECT_CONTENT

async def send_requested_file(client, message, user_id, search_id):
    try:
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        if not file_data:
            return await message.reply("❌ File not found.")

        # Next button add karo
        next_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏩ Next Video", callback_data="next_video")]
        ])

        dlt = await message.reply_video(
            video=file_data['file_id'],
            caption=(
                f"<i>𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.U_NAME}</i>\n\n"
                f"<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ. ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>"
            ),
            reply_markup=next_btn   # 👈 button yahan
        )
        asyncio.create_task(auto_delete_message(message, dlt))

    except Exception as e:
        print(f"❌ Error sending file: {e}")
        await message.reply("❌ Error: File might be deleted or inaccessible.")
