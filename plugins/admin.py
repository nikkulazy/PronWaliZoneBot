from pyrogram.types import Message
from database.users_db import db
from info import ADMINS
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

@Client.on_message(filters.command("owner_cmd") & filters.user(ADMINS))
async def admin_cmd(client, message):
    # Define the buttons - Original Reply Keyboard
    buttons = [
        [KeyboardButton("/remove_premium"), KeyboardButton("/add_premium")],
        [KeyboardButton("/premium_user"), KeyboardButton("/check_user")],
        [KeyboardButton("/blocked"), KeyboardButton("/broadcast")],
        [KeyboardButton("/ban"), KeyboardButton("/unban")],
        [KeyboardButton("/all_users_stats"), KeyboardButton("/stats")],
        [KeyboardButton("/code"), KeyboardButton("/delete_redeem")],
        [KeyboardButton("/allcodes"), KeyboardButton("/clearcodes")],
        [KeyboardButton("/deleteall"), KeyboardButton("/index")]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    
    # Send the reply message with the admin commands
    sent_message = await message.reply(
        "<b>Admin All Commands 👇</b>",
        reply_markup=reply_markup,
    )

@Client.on_message(filters.command("fixduration") & filters.user(ADMINS))
async def fix_duration_command(client, message: Message):
    msg = await message.reply("🔄 Fixing video durations...")
    result = await db.videos.update_many(
        {"duration": {"$exists": False}},
        {"$set": {"duration": 0}}
    )
    await msg.edit(f"✅ Updated {result.modified_count} videos")
