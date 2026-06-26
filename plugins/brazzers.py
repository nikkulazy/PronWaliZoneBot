import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_db import db
from info import LOG_CHANNEL, PREMIUM_DAILY_LIMIT, FSUB, PROTECT_CONTENT
from utils import temp, auto_delete_message, is_user_joined
from plugins.ban_manager import ban_manager
from plugins.get_video import send_video_with_buttons  # Import common function

@Client.on_message(filters.command("brazzers") & filters.private)
async def handle_brazzers_command(client, m: Message):
    await process_brazzers_request(client, m)

async def process_brazzers_request(client, m: Message):
    if not m.from_user:
        return
    if FSUB and not await is_user_joined(client, m):
        return

    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name or "Unknown"

    if await ban_manager.check_ban(client, m):
        return

    is_premium = await db.has_premium_access(user_id)
    if not is_premium:
        await m.reply(
            "💎 𝖡𝗎𝗒 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 𝖠𝗇𝖽 𝖦𝖾𝗍 900+ 𝖡𝖺𝗋𝗓𝗓𝖾𝗋𝗌 𝖵𝗂𝖽𝖾𝗈 𝖯𝖾𝗋 𝖬𝗈𝗇𝗍𝗁.", 
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇 •', callback_data='get')
            ]])
        )
        return

    used_today = await db.get_video_count(user_id)
    if used_today >= PREMIUM_DAILY_LIMIT:
        await m.reply(f"⚠️ Daily limit {PREMIUM_DAILY_LIMIT} reached. Try tomorrow.")
        return

    video_id = await db.get_unseen_brazzers(user_id)
    if not video_id:
        await m.reply("❌ No unseen videos found!")
        return

    # Store last video for previous button
    temp.USER_LAST_VIDEO[user_id] = video_id

    # Use common send function
    await send_video_with_buttons(
        client,
        m,
        user_id,
        video_id,
        is_brazzers=True
    )


# ---------- BRAZZERS CALLBACK ----------
@Client.on_callback_query(filters.regex(r"^get_brazzers$"))
async def brazzers_callback(client, query: CallbackQuery):
    await query.answer("⏳ Processing...", show_alert=False)
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    fake_msg.chat = query.message.chat
    await process_brazzers_request(client, fake_msg)
