import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from utils import temp, auto_delete_message
from info import PROTECT_CONTENT

# ==========================================
# 📥 यह हैंडलर avx- लिंक को प्रोसेस करेगा
# ==========================================
@Client.on_message(filters.private & filters.regex(r"start=avx-"))
async def handle_download_link(client, message):
    try:
        # लिंक से file_unique_id निकालें
        if "start=avx-" not in message.text:
            return
        
        search_id = message.text.split("start=avx-")[-1].strip()
        
        if not search_id:
            await message.reply("❌ Invalid download link!")
            return
        
        # डेटाबेस में वीडियो ढूंढें
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        
        # अगर मेन वीडियो में नहीं मिला तो ब्राज़र्स में ढूंढें
        if not file_data:
            file_data = await db.brazzers_videos.find_one({"file_unique_id": search_id})
        
        if not file_data:
            await message.reply("❌ File not found or expired!")
            return
        
        # ⏳ लोडिंग मैसेज
        loading = await message.reply("🔄 **Processing your download link...**")
        
        # 📥 डाउनलोड बटन के साथ वीडियो भेजें
        sent = await client.send_video(
            chat_id=message.chat.id,
            video=file_data['file_id'],
            protect_content=PROTECT_CONTENT,
            caption=(
                f"🎬 **Your Requested Video**\n\n"
                f"📥 **Download Link:** [Click Here](https://t.me/{temp.U_NAME}?start=avx-{search_id})\n\n"
                f"<blockquote>⚠️ This file will auto-delete after 10 minutes.\n"
                f"💡 Forward to 'Saved Messages' to keep it permanently.</blockquote>\n\n"
                f"Powered by: {temp.B_LINK}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Download Video", url=f"https://t.me/{temp.U_NAME}?start=avx-{search_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]),
            reply_to_message_id=message.id
        )
        
        await loading.delete()
        
        # ऑटो-डिलीट (10 मिनट बाद)
        asyncio.create_task(auto_delete_message(message, sent))
        
    except Exception as e:
        print(f"❌ Send file error: {e}")
        await message.reply(f"❌ Error: {str(e)}")


# ==========================================
# 📥 पुराना फंक्शन (बैकवर्ड कम्पैटिबिलिटी के लिए)
# ==========================================
async def send_requested_file(client, message, user_id, search_id):
    try:
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        if not file_data:
            return await message.reply("❌ File not found.")

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