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
    
    # ✅ INLINE BUTTONS - BILKUL SAHI TAREEKA
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("💢𝗚𝗘𝗧 𝗩𝗜𝗗𝗘𝗢𝗦💢", callback_data='get_video')],
            [
                InlineKeyboardButton("ℹ️ ʜᴇʟᴘ", callback_data='help'),
                InlineKeyboardButton("🧑‍💻 ᴀʙᴏᴜᴛ", callback_data='about')
            ],
            [InlineKeyboardButton("✨ɢᴇᴛ  ꜱᴜʙᴄᴏɴꜱᴄɪᴏᴜꜱ ᴀᴄᴄᴇꜱꜱ✨", callback_data='subscription')],
        ]
    )

    sent_msg = await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,
        has_spoiler=True
    )
    
    # ✅ 30 SECOND BAAD AUTO DELETE
    asyncio.create_task(auto_delete_message(message, sent_msg, 30))


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
# 🔙 CALLBACK QUERY HANDLER
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    # Close button
    if data == "close_data":
        try:
            await query.message.delete()
        except:
            pass
        return
    
    # Get Video button
    elif data == "get_video":
        # Call existing get_video handler
        from plugins.get_video import handle_video_request
        
        # Create fake message object
        class FakeMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
                self.id = query.message.id
                self._query = query
            
            async def reply(self, text, **kwargs):
                return await self._query.message.reply(text, **kwargs)
            
            async def reply_video(self, **kwargs):
                return await self._query.message.reply_video(**kwargs)
        
        fake_msg = FakeMessage(query)
        await handle_video_request(client, fake_msg)
    
    # Help button
    elif data == "help":
        await send_legal_text(client, query.message, script.HELP_TXT)
    
    # About button
    elif data == "about":
        await send_about_text(client, query.message)
    
    # My Plan button
    elif data == "myplan":
        from plugins.premium import myplan_handler
        
        class FakePlanMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
                self.reply = query.message.reply
                self.id = query.message.id
        
        fake_plan_msg = FakePlanMessage(query)
        await myplan_handler(client, fake_plan_msg)
    
    # Subscription button
    elif data == "subscription":
        from plugins.premium import buy_handler
        
        class FakeBuyMessage:
            def __init__(self, query):
                self.from_user = query.from_user
                self.chat = query.message.chat
                self.reply = query.message.reply
                self.reply_photo = query.message.reply_photo
                self.reply_text = query.message.reply_text
                self.id = query.message.id
        
        fake_buy_msg = FakeBuyMessage(query)
        await buy_handler(client, fake_buy_msg)
    
    # Existing get callback
    elif data == "get":
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
