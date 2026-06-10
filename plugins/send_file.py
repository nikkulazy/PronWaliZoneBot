import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from utils import temp, auto_delete_message

async def send_requested_file(client, message, user_id, search_id):
    try:
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        if not file_data:
            file_data = await db.videos.find_one({"file_id": search_id})
        if not file_data:
            return await message.reply("❌ File not found.")

        video_id = file_data['file_id']
        prev_obj = await db.get_prev_video_id(video_id)
        next_obj = await db.get_next_video_id(video_id)

        nav_buttons = []
        if prev_obj:
            nav_buttons.append(InlineKeyboardButton("◀ Previous", callback_data=f"nav_{prev_obj}"))
        if next_obj:
            nav_buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"nav_{next_obj}"))

        row1 = nav_buttons if nav_buttons else []
        row2 = [
            InlineKeyboardButton("📁 Category", callback_data="category"),
            InlineKeyboardButton("❓ Help", callback_data="help_me")
        ]
        row3 = [InlineKeyboardButton("❌ Close", callback_data="close_data")]

        reply_markup = InlineKeyboardMarkup([row1, row2, row3] if row1 else [row2, row3])

        dlt = await message.reply_video(
            video=video_id,
            caption=(
                f"<i>𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.U_NAME}</i>\n\n"
                f"<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ. ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>"
            ),
            reply_markup=reply_markup
        )
        asyncio.create_task(auto_delete_message(message, dlt))

    except Exception as e:
        print(f"❌ Error sending file: {e}")
        await message.reply("❌ Error: File might be deleted or inaccessible.")
