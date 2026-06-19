import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") | filters.regex(r"(?i)brazzers"))
async def handle_brazzers_request(client, m: Message):
    try:
        if not m.from_user:
            return
            
        if FSUB and not await is_user_joined(client, m):
            return
        
        user_id = m.from_user.id
        username = m.from_user.username or m.from_user.first_name or "Unknown"
        
        if await ban_manager.check_ban(client, m):
            return

        is_premium = await db.has_premium_access(user_id)
        
        # FREE USER - Show message
        if not is_premium:
            await m.reply(
                "🔞 <b>Brazzers केवल Premium Users के लिए!</b>\n\n"
                "💎 सब्सक्रिप्शन खरीदें और 900+ Brazzers वीडियो हर महीने देखें।\n\n"
                "✨ <b>Premium Benefits:</b>\n"
                f"• {PREMIUM_DAILY_LIMIT} Videos per day\n"
                "• Access to Brazzers content\n"
                "• Priority support\n\n"
                "💰 <b>नीचे क्लिक करें खरीदने के लिए:</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('💎 Subscription खरीदें', callback_data='get_subscription')],
                    [InlineKeyboardButton('❌ बंद करें', callback_data='close_data')]
                ])
            )
            return

        # PREMIUM USER - Check daily limit
        used_today = await db.get_video_count(user_id) or 0
        if used_today >= PREMIUM_DAILY_LIMIT:
            await m.reply(
                f"⚠️ <b>Daily Limit Reached!</b>\n\n"
                f"You've used {used_today}/{PREMIUM_DAILY_LIMIT} files today.\n"
                f"⏳ Try again tomorrow!"
            )
            return
        
        # Get unseen Brazzers video
        video_id = await db.get_unseen_brazzers(user_id)
        if not video_id:
            await m.reply(
                "❌ <b>No Unseen Videos!</b>\n\n"
                "📢 You've watched all Brazzers videos.\n"
                "🆕 New videos will be added soon.\n\n"
                "🔄 Check back later!"
            )
            return
        
        # Send video to premium user
        dlt = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=(
                f"🔞 <b>Brazzers Exclusive</b>\n\n"
                f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                "<blockquote>"
                "ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ "
                "ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ."
                "</blockquote>"
            ),
            reply_to_message_id=m.id
        )
        
        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, dlt))

    except Exception as e:
        print(f"Brazzers Error: {e}")
        try:
            await m.reply(f"❌ Error: {str(e)}")
        except:
            pass
