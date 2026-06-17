import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# =================================================
# 🚀 START COMMAND
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention
    
    if FSUB and not await is_user_joined(client, message):
        return
        
    argument = message.command[1] if len(message.command) > 1 else None

    if argument and argument.startswith('avbotz'):
        await verify_user_on_start(client, message)
        return

    if argument == "terms":
        await send_legal_text(client, message, script.TERMS_TXT)
        return
    elif argument == "disclaimer":
        await send_legal_text(client, message, script.DISCLAIMER_TXT)
        return
    elif argument == "help":
        await send_legal_text(client, message, script.HELP_TXT)
        return
    elif argument == "about":
        await send_about_text(client, message)
        return

    if argument and argument.startswith("reff_"):
        try:
            await refer_on_start(client, message)
            return 
        except Exception as e:
            print(f"Referral Error: {e}")

    if argument and argument.startswith("avx-"):
        search_id = argument.replace("avx-", "")
        await send_requested_file(client, message, user_id, search_id)
        return

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        try:
            await client.send_message(
                LOG_CHANNEL,
                script.LOG_TEXT.format(me2, user_id, mention)
            )
        except Exception:
            pass

    # ✅ ALL INLINE BUTTONS (Reply Keyboard HATAYA)
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Get Video", callback_data="inline_get_video")],
        [InlineKeyboardButton("🔞 Brazzers", callback_data="brazzers")],
        [InlineKeyboardButton("📱 My Plan", callback_data="my_plan")],
        [InlineKeyboardButton("💳 Subscription", callback_data="subscription")]
    ])

    # ✅ Photo + Caption + All Inline Buttons (Ek Saath)
    await client.send_photo(
        chat_id=message.chat.id,
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard
    )

# =================================================
# 📜 HELPER HANDLERS
# =================================================

@Client.on_message(filters.command("disclaimer") & filters.private)
async def legal_disclaimer(client, message: Message):
    await send_legal_text(client, message, script.DISCLAIMER_TXT)

@Client.on_message(filters.command("terms") & filters.private)
async def legal_terms(client, message: Message):
    await send_legal_text(client, message, script.TERMS_TXT)

@Client.on_message(filters.command("about") & filters.private)
async def legal_about(client, message: Message):
    await send_about_text(client, message)

@Client.on_message(filters.command("help") & filters.private)
async def legal_hepl(client, message: Message):
    await send_legal_text(client, message, script.HELP_TXT)
    
async def send_legal_text(client, message, text):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )

async def send_about_text(client, message):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )

# =========================================================
# 🔙 CALLBACK QUERY HANDLER (ALL BUTTONS)
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # ✅ Close button
    if data == "close_data":
        await query.message.delete()
        await query.answer()

    # ✅ Get/Subscription button (existing)
    elif data == "get":
        await query.answer()
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    # ✅ Get Video button
    elif data == "inline_get_video":
        await query.answer()
        from plugins.get_video import handle_video_request_from_callback
        await handle_video_request_from_callback(client, query)

    # ✅ Brazzers button
    elif data == "brazzers":
        await query.answer()
        await query.message.reply_text(
            "🔞 *Brazzers Content*\n\n"
            "This section is for premium users only.\n"
            "Please subscribe to access.",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    # ✅ My Plan button
    elif data == "my_plan":
        await query.answer()
        is_premium = await db.has_premium_access(user_id)
        if is_premium:
            plan_text = "🌟 *Premium User*\n\nYou have unlimited access!"
        else:
            plan_text = "📱 *Free User*\n\n"
            plan_text += f"Daily Limit: {DAILY_LIMIT} videos\n"
            plan_text += "Upgrade to Premium for unlimited access!"
        
        await query.message.reply_text(
            plan_text,
            parse_mode=enums.ParseMode.MARKDOWN
        )

    # ✅ Subscription button
    elif data == "subscription":
        await query.answer()
        buttons = [
            [InlineKeyboardButton('• 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 •', callback_data='get')],
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_text(
            f"💳 *Subscription Plans*\n\n"
            f"UPI ID: `{UPI_ID}`\n\n"
            f"Daily Limit: {DAILY_LIMIT} videos (Free)\n"
            f"Premium Limit: {PREMIUM_DAILY_LIMIT} videos\n\n"
            f"Contact @admin for more details.",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.MARKDOWN
        )
