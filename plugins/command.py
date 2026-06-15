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
    
    # ✅ INLINE BUTTONS
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("💢𝗚𝗘𝗧 𝗩𝗜𝗗𝗘𝗢𝗦💢", callback_data='get_video')],
            [
                InlineKeyboardButton("ℹ️ ʜᴇʟᴘ", callback_data='help'),
                InlineKeyboardButton("🧑‍💻 ᴀʙᴏᴜᴛ", callback_data='about')
            ],
            [InlineKeyboardButton("✨ɢᴇᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴄᴇꜱꜱ✨", callback_data='subscription')],
        ]
    )

    sent_msg = await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,
        has_spoiler=True
    )
    
    # ✅ 5 MINUTE BAAD AUTO DELETE
    asyncio.create_task(auto_delete_message(message, sent_msg, 300))


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
async def legal_help(client, message: Message):
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
# 🔙 AUTO DELETE FUNCTION
# =========================================================
async def auto_delete_message(original_msg, sent_msg, delay=30):
    await asyncio.sleep(delay)
    try:
        await sent_msg.delete()
        await original_msg.delete()
    except:
        pass


# =========================================================
# 🔙 CALLBACK QUERY HANDLER - COMPLETE FIXED VERSION
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    
    await query.answer()
    
    # Close button
    if data == "close_data":
        try:
            await query.message.delete()
        except:
            pass
        return
    
    # Get Video button
    if data == "get_video":
        from plugins.get_video import handle_video_request
        try:
            await handle_video_request(client, query.message)
        except Exception as e:
            print(f"Get Video Error: {e}")
            await query.message.reply_text("❌ Error getting video. Please try /getvideo command.")
        return
    
    # Help button
    if data == "help":
        text = script.HELP_TXT
        btn = [[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]]
        await query.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(btn),
            disable_web_page_preview=True
        )
        return
    
    # About button
    if data == "about":
        text = script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK)
        btn = [[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]]
        await query.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(btn),
            disable_web_page_preview=True
        )
        return
    
    # Subscription button
    if data == "subscription":
        from plugins.premium import buy_handler
        await buy_handler(client, query.message)
        return
    
    # My Plan button
    if data == "myplan":
        from plugins.premium import myplan_handler
        await myplan_handler(client, query.message)
        return
    
    # Delete Main Video button
    if data == "delete_main":
        await query.answer("🗑 Deleting Main Videos...", show_alert=True)
        result = await db.delete_all_main_videos()
        await query.message.edit_text(f"✅ {result} Main Videos Deleted Successfully!")
        return
    
    # Delete Brazzers button
    if data == "delete_brazzers":
        await query.answer("🗑 Deleting Brazzers Videos...", show_alert=True)
        result = await db.delete_all_brazzers_videos()
        await query.message.edit_text(f"✅ {result} Brazzers Videos Deleted Successfully!")
        return
    
    # Cancel delete button
    if data == "cancel_delete":
        await query.answer("❌ Delete Cancelled!")
        await query.message.delete()
        return
    
    # Existing get callback
    if data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        if QR_CODE_IMAGE:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        return
