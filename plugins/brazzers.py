import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") | filters.regex(r"(?i)brazzers"))
async def handle_brazzers_request(client, m: Message):
    if not m.from_user:
        return
    if FSUB and not await is_user_joined(client, m):
        return
    
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    if await ban_manager.check_ban(client, m):
        return

    try:
        is_premium = await db.has_premium_access(user_id)
        
        # ✅ FREE USER - Show message (not popup)
        if not is_premium:
            return await m.reply(
                "🔞 <b>Brazzers is only for Premium Users!</b>\n\n"
                "💎 Buy subscription and get access to 900+ Brazzers videos per month.\n\n"
                "✨ <b>Premium Benefits:</b>\n"
                f"• {PREMIUM_DAILY_LIMIT} Videos per day\n"
                "• Access to Brazzers content\n"
                "• Priority support\n\n"
                "💰 <b>Click below to buy:</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('💎 Purchase Subscription', callback_data='get_subscription')],
                    [InlineKeyboardButton('❌ Close', callback_data='close_data')]
                ])
            )

        # ✅ PREMIUM USER - Check daily limit
        used_today = await db.get_video_count(user_id) or 0
        if used_today >= PREMIUM_DAILY_LIMIT:
            return await m.reply(
                f"⚠️ <b>Daily Limit Reached!</b>\n\n"
                f"You've used {used_today}/{PREMIUM_DAILY_LIMIT} files today.\n"
                f"⏳ Try again tomorrow!"
            )
        
        # Get unseen Brazzers video
        video_id = await db.get_unseen_brazzers(user_id)
        if not video_id:
            return await m.reply(
                "❌ <b>No Unseen Videos!</b>\n\n"
                "📢 You've watched all Brazzers videos.\n"
                "🆕 New videos will be added soon.\n\n"
                "🔄 Check back later!"
            )
        
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
        await m.reply(f"❌ Error: {str(e)}")

"""import asyncio
import string
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.users_db import db
from info import LOG_CHANNEL, PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager 

@Client.on_message(filters.command("brazzers") | filters.regex(r"(?i)brazzers"))
async def handle_brazzers_request(client, m: Message):
    if not m.from_user:
        return
    if FSUB and not await is_user_joined(client, m):
        return
    
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    
    if await ban_manager.check_ban(client, m):
        return

    try:
        is_premium = await db.has_premium_access(user_id)
        if not is_premium:
            return await m.reply(
                "💎 𝖡𝗎𝗒 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 𝖠𝗇𝖽 𝖦𝖾𝗍 900+ 𝖡𝖺𝗋𝗓𝗓𝖾𝗋𝗌 𝖵𝗂𝖽𝖾𝗈 𝖯𝖾𝗋 𝖬𝗈𝗇𝗍𝗁.", 
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •', callback_data='get')
                ]])
            )

        used_today = await db.get_video_count(user_id)
        if used_today >= PREMIUM_DAILY_LIMIT:
            return await m.reply(f"⚠️ 𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖣𝖺𝗂𝗅𝗒 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {PREMIUM_DAILY_LIMIT} 𝖥𝗂𝗅𝖾𝗌. 𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐")
        
        video_id = await db.get_unseen_brazzers(user_id)
        if not video_id:
            return await m.reply("❌ No unseen videos found!")

        # Fix: Using client.send_video to support protect_content
        dlt = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ. ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>",
            reply_to_message_id=m.id
        )
        
        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, dlt))

    except Exception as e:
        print(f"Error: {e}")"""
        
