from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
import asyncio
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, auto_delete_message, is_user_joined


@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):

    if not m.from_user:
        return
    if FSUB and not await is_user_joined(client, m):
        return
    if await ban_manager.check_ban(client, m):
        return

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"
    is_premium = await db.has_premium_access(user_id)
    current_limit = PREMIUM_DAILY_LIMIT if is_premium else DAILY_LIMIT
    used = await db.get_video_count(user_id) or 0

    # Limit & verification logic
    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(f"⚠️ Premium limit reached: {PREMIUM_DAILY_LIMIT}/day")
    else:
        if used >= VERIFICATION_DAILY_LIMIT:
            buy_btn = InlineKeyboardMarkup([[InlineKeyboardButton("• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •", callback_data="get")]])
            return await m.reply(f"❌ Daily limit reached. Buy premium to continue.", reply_markup=buy_btn)
        if used >= DAILY_LIMIT:
            if IS_VERIFY:
                verified = await av_x_verification(client, m)
                if not verified:
                    return
            else:
                buy_btn = InlineKeyboardMarkup([[InlineKeyboardButton("• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •", callback_data="get")]])
                return await m.reply(f"❌ Free limit ({DAILY_LIMIT}) used up.", reply_markup=buy_btn)

    # Get video
    video_id = await db.get_unseen_video(user_id)
    if not video_id:
        video_id = await db.get_random_video()
    if not video_id:
        return await m.reply("❌ No videos found.")

    # ✅ Next button (inline keyboard)
    next_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏩ Next", callback_data="next_video")]
    ])

    try:
        sent = await client.send_video(
            chat_id=m.chat.id,
            video=video_id,
            protect_content=PROTECT_CONTENT,
            caption=f"𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘉𝘺: {temp.B_LINK}\n\n"
                    "<blockquote>ᴛʜɪꜱ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ.\n"
                    "ᴘʟᴇᴀꜱᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪꜱ ꜰɪʟᴇ ꜱᴏᴍᴇᴡʜᴇʀᴇ ᴇʟꜱᴇ ᴏʀ ꜱᴀᴠᴇ ɪɴ ꜱᴀᴠᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ.</blockquote>",
            reply_to_message_id=m.id,
            reply_markup=next_button
        )
        await db.increase_video_count(user_id, username)
        asyncio.create_task(auto_delete_message(m, sent))
    except Exception as e:
        print(f"Error in send_video: {e}")
        await m.reply(f"❌ Failed to send video: {str(e)}")
