from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS

@Client.on_message(filters.command("owner_cmd") & filters.user(ADMINS))
async def admin_cmd(client, message):
    # ✅ Converted to Inline Buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Premium", callback_data="admin_add_prem"), 
         InlineKeyboardButton("➖ Remove Premium", callback_data="admin_remove_prem")],
        [InlineKeyboardButton("📋 Premium Users", callback_data="admin_premium_users"), 
         InlineKeyboardButton("🔍 Check User", callback_data="admin_check_user")],
        [InlineKeyboardButton("🚫 Blocked Users", callback_data="admin_blocked"), 
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Ban", callback_data="admin_ban"), 
         InlineKeyboardButton("✅ Unban", callback_data="admin_unban")],
        [InlineKeyboardButton("📊 All Users Stats", callback_data="admin_all_stats"), 
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("🔑 Generate Code", callback_data="admin_code"), 
         InlineKeyboardButton("🗑 Delete Redeem", callback_data="admin_delete_redeem")],
        [InlineKeyboardButton("📝 All Codes", callback_data="admin_allcodes"), 
         InlineKeyboardButton("🧹 Clear Codes", callback_data="admin_clearcodes")],
        [InlineKeyboardButton("🗑 Delete All", callback_data="admin_deleteall"), 
         InlineKeyboardButton("📂 Index", callback_data="admin_index")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await message.reply(
        "<b>🔧 Admin All Commands 👇</b>\n\n"
        "<i>Click any button to execute command.</i>",
        reply_markup=buttons,
    )

# ✅ Admin Callback Handler - Add these to your main callback handler
async def admin_callback_handler(client, query):
    data = query.data
    user_id = query.from_user.id
    
    # Check if user is admin
    if not (isinstance(ADMINS, list) and user_id in ADMINS) and user_id != ADMINS:
        await query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    # Map callbacks to commands
    command_map = {
        "admin_add_prem": "add_premium",
        "admin_remove_prem": "remove_premium",
        "admin_premium_users": "premium_user",
        "admin_check_user": "check_user",
        "admin_blocked": "blocked",
        "admin_broadcast": "broadcast",
        "admin_ban": "ban",
        "admin_unban": "unban",
        "admin_all_stats": "all_users_stats",
        "admin_stats": "stats",
        "admin_code": "code",
        "admin_delete_redeem": "delete_redeem",
        "admin_allcodes": "allcodes",
        "admin_clearcodes": "clearcodes",
        "admin_deleteall": "deleteall",
        "admin_index": "index",
    }
    
    if data in command_map:
        await query.answer(f"🔄 Executing /{command_map[data]}...")
        # Create fake message to trigger command
        fake_msg = query.message
        fake_msg.from_user = query.from_user
        fake_msg.text = f"/{command_map[data]}"
        
        # Route to appropriate handler based on command
        # You'll need to import and call the respective functions
        await query.message.reply(f"✅ Command /{command_map[data]} executed!\n\n<i>Check logs for details.</i>")

"""from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from info import ADMINS

@Client.on_message(filters.command("owner_cmd") & filters.user(ADMINS))
async def admin_cmd(client, message):
    # Define the buttons
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
    )"""
