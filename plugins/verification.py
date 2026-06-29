import asyncio
import logging
import random
import string
import pytz
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import enums
from info import (
    VERIFIED_LOG, TIMEZONE, VERIFY_IMG,
    TUTORIAL_LINK, IS_VERIFY, OWNER_USERNAME
)
from database.users_db import db
from utils import temp, get_shortlink_av, auto_delete_message
from Script import script

logger = logging.getLogger(__name__)

# --- MAIN VERIFICATION CHECKER ---
async def av_x_verification(client, message):
    try:
        user_id = message.from_user.id
        
        if IS_VERIFY:
            user_verified = await db.is_user_verified(user_id)
        else:
            user_verified = True 
        
        if user_verified:
            return True
            
        file_id = None
        
        # ✅ FIX: Command se file_id lo
        if hasattr(message, 'command') and message.command and len(message.command) > 1:
            file_id = message.command[1]
            print(f"🔍 [VERIFICATION] File ID from command: {file_id}")
        
        verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        
        # ✅ FIX: File ID save karo
        await db.create_verify_id(user_id, verify_id, file_id)
        print(f"✅ [VERIFICATION] Saved - Verify ID: {verify_id} | File ID: {file_id}")
        
        # Link Generation
        long_url = f"https://telegram.me/{temp.U_NAME}?start=avbotz_{user_id}_{verify_id}"
        
        verify_url = long_url
        try:
            short_url = await get_shortlink_av(long_url)
            if short_url and short_url.startswith("http"):
                verify_url = short_url
                print(f"✅ Shortlink generated: {verify_url}")
            else:
                verify_url = long_url
        except Exception as e:
            print(f"⚠️ Shortlink failed: {e}")
            verify_url = long_url
        
        tutorial_url = TUTORIAL_LINK if TUTORIAL_LINK and TUTORIAL_LINK.startswith("http") else "https://t.me"
        
        buttons = [
            [InlineKeyboardButton("💎 Upgrade To Premium", callback_data="get_subscription")],
            [InlineKeyboardButton(text="⚠️ Verify ⚠️", url=verify_url)],
            [InlineKeyboardButton(text="❓ How to Verify ❓", url=tutorial_url)]
        ]
        
        user_name = message.from_user.first_name or "User"
        
        try:
            bin_text = script.VERIFICATION_TEXT.format(user_name, "1/1")
        except:
            bin_text = f"⚠️ **Verification Required** {user_name}!\n\nPlease verify to continue."
        
        try:
            dlt = await message.reply_text(
                text=bin_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
            asyncio.create_task(auto_delete_message(message, dlt))
        except Exception as e:
            print(f"❌ Failed to send verification message: {e}")
            try:
                fallback_buttons = [
                    [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"https://t.me/{OWNER_USERNAME}")]
                ]
                await message.reply_text(
                    text="⚠️ **Verification system is temporarily unavailable.**\n\nPlease contact admin for support.",
                    reply_markup=InlineKeyboardMarkup(fallback_buttons),
                    parse_mode=enums.ParseMode.HTML
                )
            except:
                await message.reply_text("⚠️ Verification failed. Please contact admin.")
            return False
        
        return False
        
    except Exception as e:
        print(f"❌ av_x_verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- VERIFICATION SUCCESS HANDLER ---
async def verify_user_on_start(client, message):
    try:
        if not message.command or len(message.command) < 2:
            return False

        data = message.command[1].split("_")       
        if len(data) < 3:
            return False           
        user_id = int(data[1])
        verify_id = data[2]
        
        if message.from_user.id != user_id:
            await message.reply("<b>This link is not for you!</b>")
            return True
            
        verify_id_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_id_info or verify_id_info["verified"]:
            await message.reply("<b>Lɪɴᴋ Exᴘɪʀᴇᴅ ᴏʀ Aʟʀᴇᴀᴅʏ Usᴇᴅ... Tʀʏ Aɢᴀɪɴ.</b>")
            return True
            
        ist_timezone = pytz.timezone(TIMEZONE)     
        current_time = datetime.now(tz=ist_timezone)
        
        await db.update_notcopy_user(user_id, {"last_verified": current_time})
        await db.update_verify_id_info(user_id, verify_id, {"verified": True})
        
        stored_file_id = verify_id_info.get("file_id")
        print(f"🔍 [VERIFY COMPLETE] Stored File ID: {stored_file_id}")
        
        # ✅ FIX: avx- prefix add karo
        if stored_file_id:
            file_link = f"https://t.me/{temp.U_NAME}?start=avx-{stored_file_id}"
            print(f"🔗 [VERIFY COMPLETE] File Link: {file_link}")
        else:
            file_link = f"https://t.me/{temp.U_NAME}?start=help"
            print(f"⚠️ [VERIFY COMPLETE] No file_id")
            
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("📂 ɢᴇᴛ ʀᴇǫᴜᴇsᴛᴇᴅ ғɪʟᴇ 📂", url=file_link)
        ]])
        
        txt = script.VERIFY_COMPLETE_TEXT
        
        if VERIFIED_LOG:
            try:
                await client.send_message(
                    VERIFIED_LOG, 
                    script.VERIFIED_TXT.format(
                        message.from_user.mention, 
                        user_id, 
                        datetime.now(ist_timezone).strftime('%d_%B_%Y'), 
                        "1" 
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send log: {e}")
                
        await message.reply_photo(
            photo=VERIFY_IMG, 
            caption=txt.format(message.from_user.mention), 
            reply_markup=btn, 
            parse_mode=enums.ParseMode.HTML
        )
        return True
        
    except Exception as e:
        logger.error(f"Verify Error: {e}")
        return False
