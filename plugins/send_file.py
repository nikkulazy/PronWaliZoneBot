import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from utils import temp, auto_delete_message
from info import PROTECT_CONTENT


async def send_requested_file(client, message, user_id, search_id):
    try:
        loading = await message.reply("🔄 **Processing your request...**")
        
        # वीडियो ढूंढें
        file_data = await db.videos.find_one({"file_unique_id": search_id})
        if not file_data:
            file_data = await db.brazzers_videos.find_one({"file_unique_id": search_id})
        
        if not file_data:
            await loading.delete()
            return await message.reply("❌ File not found or expired!")
        
        # डाउनलोड लिंक
        bot_username = temp.U_NAME
        download_link = f"https://t.me/{bot_username}?start=avx-{search_id}"
        
        # डाउनलोड बटन
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Video", url=download_link)],
            [InlineKeyboardButton("🎬 Get Another Video", callback_data="get_another")]
        ])
        
        # वीडियो भेजें
        sent = await client.send_video(
            chat_id=message.chat.id,
            video=file_data['file_id'],
            protect_content=PROTECT_CONTENT,
            caption=(
                f"🎬 **Your Requested Video**\n\n"
                f"📥 **Click below to download**\n\n"
                f"⚠️ Auto-deletes in 10 minutes\n"
                f"Powered by: {temp.B_LINK}"
            ),
            reply_markup=reply_markup,
            reply_to_message_id=message.id
        )
        
        await loading.delete()
        asyncio.create_task(auto_delete_message(message, sent))

    except Exception as e:
        print(f"❌ Error: {e}")
        await message.reply(f"❌ Error: {str(e)}")
