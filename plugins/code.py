import time
import asyncio
import random
import string
import hashlib
import re, os
import pytz
from datetime import datetime, timedelta, timezone
from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, PREMIUM_LOGS
from database.users_db import db
from utils import temp, get_seconds

# ==================================================================
# 🔑 CODE GENERATOR LOGIC
# ==================================================================
def hash_code(code):
    return hashlib.sha256(code.encode()).hexdigest()

async def generate_code(duration_str):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"MASTITIME{code}"

# ------------------------------------------------------------------
# 🛠️ ADMIN COMMAND: GENERATE CODES
# ------------------------------------------------------------------
@Client.on_message(filters.command("code") & filters.user(ADMINS))
async def generate_code_cmd(client, message):
    if len(message.command) == 2:
        duration_str = message.command[1]
        count = 1
    elif len(message.command) == 3:
        try:
            count = int(message.command[1])
            duration_str = message.command[2]
        except ValueError:
            return await message.reply_text("❌ Usage: `/code 10 1month`")
    else:
        return await message.reply_text("Usage:\n`/code 1month`\n`/code 10 1month`")
    if count > 10:
        return await message.reply_text("❌ Max 10 codes allowed at once.")
    premium_duration_seconds = await get_seconds(duration_str)
    if not premium_duration_seconds:
        return await message.reply_text("❌ Invalid duration like `1minute`, `2days`, `1month`.")
    codes = []
    for _ in range(count):
        code = await generate_code(duration_str)
        await db.codes.insert_one({
            "code": code,
            "code_hash": hash_code(code),
            "original_code": code,
            "duration": duration_str,
            "expires_in": premium_duration_seconds,
            "used": False,
            "user_id": None,
            "used_at": None,
            "created_at": datetime.now(timezone.utc)
        })
        codes.append(f"🔹 `{code}`")
    codes_text = "\n".join(codes)
    
    await message.reply_text(
        f"✅ **{count} Redeem Codes Generated for {duration_str}**\n\n"
        f"{codes_text}\n\n"
        f"𝐔𝐬𝐚𝐠𝐞 : /redeem xxxxxxxxxx\n\n"
        f"𝐍𝐨𝐭𝐞 : Only one user can use each code."
    )

# ------------------------------------------------------------------
# 📜 ADMIN COMMAND: VIEW ALL CODES
# ------------------------------------------------------------------

@Client.on_message(filters.command("allcodes") & filters.user(ADMINS))
async def all_codes_cmd(client, message):
    msg_status = await message.reply_text("🔄 **Fetching codes...**")
    all_codes = await db.codes.find({}).to_list(length=None)
    if not all_codes:
        return await msg_status.edit("⚠️ No codes found.")
    if len(all_codes) > 10:
        file_path = "All_Redeem_Codes.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("📝 GENERATED REDEEM CODES LIST\n")
            f.write("================================\n\n")
            for code in all_codes:
                status = "Yes" if code.get("used") else "No"
                created_at = code.get("created_at")
                if created_at:
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    created = created_at.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M %p")
                else:
                    created = "N/A"

                user_id = code.get("user_id")
                user_text = str(user_id) if user_id else "Not Redeemed"
                f.write(f"🔑 Code: {code['original_code']}\n")
                f.write(f"⌛ Duration: {code['duration']}\n")
                f.write(f"‼️ Used: {status}\n")  # Fixed: Added f.write(
                f.write(f"🕓 Created: {created}\n") # Fixed: Added f.write(
                f.write(f"🙎 User ID: {user_text}\n") # Fixed: Added f.write(
                f.write("--------------------------------\n")
        try:
            await message.reply_document(
                document=file_path,
                caption=f"📝 **Total Generated Codes:** `{len(all_codes)}`\n\nℹ️ _File sent because codes are more than 10._"
            )
        except Exception as e:
            await message.reply_text(f"❌ Error sending file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        await msg_status.delete()
    else:
        msg = "📝 <b>GENERATED CODES DETAILS:</b>\n\n"
        for code in all_codes:
            status = "Yes ✅" if code.get("used") else "No ⭕"
            created_at = code.get("created_at")
            if created_at:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                created = created_at.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M %p")
            else:
                created = "N/A"
            user_id = code.get("user_id")
            user_text = f"<code>{user_id}</code>" if user_id else "Not Redeemed"
            msg += (
                f"🔑 Code: <code>{code['original_code']}</code>\n"
                f"⌛ Duration: {code['duration']}\n"
                f"‼️ Used: {status}\n"
                f"🕓 Created: {created}\n"
                f"🙎 User: {user_text}\n\n"
                f"──────────────────\n\n"
            )
        await msg_status.edit(msg)
        

# ------------------------------------------------------------------
# 🗑️ ADMIN COMMAND: DELETE REDEEM CODE
# ------------------------------------------------------------------
@Client.on_message(filters.command("delete_redeem") & filters.user(ADMINS))
async def delete_redeem_cmd(client, message):
    if len(message.command) != 2:
        return await message.reply_text("❌ Usage: `/delete_redeem CODE`")
    input_code = message.command[1].strip().upper()
    result = await db.codes.delete_one({"code_hash": hash_code(input_code)})
    if result.deleted_count == 1:
        await message.reply_text(f"✅ Code `{input_code}` deleted successfully.")
    else:
        await message.reply_text(f"❌ Code not found.")

# ------------------------------------------------------------------
# 🧹 ADMIN COMMAND: CLEAR ALL CODES
# ------------------------------------------------------------------
@Client.on_message(filters.command("clearcodes") & filters.user(ADMINS))
async def clear_codes_cmd(client, message):
    result = await db.codes.delete_many({})
    if result.deleted_count > 0:
        await message.reply_text(f"✅ ᴀʟʟ {result.deleted_count} ᴄᴏᴅᴇs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.")
    else:
        await message.reply_text("⚠️ ɴᴏ ᴄᴏᴅᴇs ғᴏᴜɴᴅ ᴛʜᴀᴛ ᴄᴏᴜʟᴅ ʙᴇ ᴄʟᴇᴀʀᴇᴅ.")

# ------------------------------------------------------------------
# 🎁 USER COMMAND: REDEEM
# ------------------------------------------------------------------
@Client.on_message(filters.command("redeem"))
async def redeem_command(client, message):
    user_id = message.from_user.id
    
    if await db.has_premium_access(user_id):
        return await message.reply_text("𝖸𝗈𝗎 𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾𝖽 𝖮𝗎𝗋 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇! 𝖤𝗇𝗃𝗈𝗒 𝖸𝗈𝗎𝗋 𝖡𝖾𝗇𝖾𝖿𝗂𝗍𝗌..")
    
    if len(message.command) != 2:
        return await message.reply_text("Usage: `/redeem CODE`")
    
    code = message.command[1].strip().upper()
    message.text = code
    await redeem_code_handler(client, message)

# ------------------------------------------------------------------
# 🕵️ REGEX HANDLER FOR REDEEM CODES
# ------------------------------------------------------------------
@Client.on_message(filters.regex(r"^PWZONE[A-Z0-9]{10}$"))
async def redeem_code_handler(client, message):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if await db.has_premium_access(user_id):
        return await message.reply_text("𝖸𝗈𝗎 𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾𝖽 𝖮𝗎𝗋 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇!")

    code_data = await db.codes.find_one({"code_hash": hash_code(code)})
    if not code_data:
        return await message.reply_text("🚫 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖮𝗋 𝖤𝗑𝗉𝗂𝗋𝖾𝖽 𝖢𝗈𝖽𝖾.")

    if code_data['used']:
        return await message.reply_text("🚫 𝖳𝗁𝗂𝗌 𝖱𝖾𝖽𝖾𝖾𝗆 𝖢𝗈𝖽𝖾 𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝖴𝗌𝖾𝖽.")

    # ✅ FIX: Yahan parse_duration ki jagah get_seconds use kiya
    premium_duration_seconds = await get_seconds(code_data['duration'])
    
    if premium_duration_seconds is None:
        return await message.reply_text("🚫 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖣𝗎𝗋𝖺𝗍𝗂𝗈𝗇 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗈𝖽𝖾.")

    # Calculating Expiry
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=premium_duration_seconds)
    
    # IST Format for display
    expiry_str_ist = new_expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
        "%d-%m-%Y 𝘈𝘵 : %I:%M:%S %p"
    )

    # Update User in DB
    user_data = {
        "id": user_id,
        "name": user_name,
        "expiry_time": new_expiry
    }
    await db.update_user(user_data)

    # Mark code as used
    await db.codes.update_one(
        {"_id": code_data["_id"]},
        {
            "$set": {
                "used": True,
                "user_id": user_id,
                "user_name": user_name,
                "used_at": datetime.now(timezone.utc)
            }
        }
    )

    # Success Message
    await message.reply_text(
        f"🎉 𝘊𝘰𝘯𝘨𝘳𝘢𝘵𝘶𝘭𝘢𝘵𝘪𝘰𝘯𝘴! 𝘙𝘦𝘥𝘦𝘦𝘮𝘦𝘥 𝘚𝘶𝘤𝘤𝘦𝘴𝘴𝘧𝘶𝘭𝘭𝘺 \n\n"
        f"⏳ 𝘋𝘶𝘳𝘢𝘵𝘪𝘰𝘯 : {code_data['duration']}\n"
        f"📅 𝘌𝘹𝘱𝘪𝘳𝘺 : {expiry_str_ist}\n\n"
        f"✨ 𝘌𝘯𝘫𝘰𝘺 𝘺𝘰𝘶𝘳 𝘱𝘳𝘦𝘮𝘪𝘶𝘮 𝘣𝘦𝘯𝘦𝘧𝘪𝘵𝘴!"
    )

    # Log to Channel
    try:
        log_text = (
            f"#REDEEM_LOG\n\n"
            f"👤 User: {user_name} [{user_id}]\n"
            f"🔑 Code: {code}\n"
            f"⏳ Duration: {code_data['duration']}\n"
            f"📅 Expiry: {expiry_str_ist}\n"
            f"🕒 Redeemed at: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y %I:%M:%S %p')}"
        )
        await client.send_message(
            PREMIUM_LOGS,
            text=log_text
        )
    except Exception as e:
        print(f"Failed to send premium log: {e}")
    
