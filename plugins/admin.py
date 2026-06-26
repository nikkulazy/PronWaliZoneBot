from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import ADMINS
from database.users_db import db

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


# =============================================
# 🗑️ DELETE ALL COMMAND HANDLER (NEW)
# =============================================
@Client.on_message(filters.command("deleteall") & filters.user(ADMINS))
async def delete_all_handler(client, message):
    """Handle /deleteall command with confirmation buttons"""
    
    # Confirmation buttons with proper callback data
    buttons = [
        [
            InlineKeyboardButton("🗑️ Delete Main Videos", callback_data="delete_main_confirm"),
            InlineKeyboardButton("🗑️ Delete Brazzers", callback_data="delete_brazzers_confirm")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel")
        ]
    ]
    
    await message.reply(
        "⚠️ **Delete All Data**\n\n"
        "Select which database you want to delete:\n\n"
        "🔴 This action is **IRREVERSIBLE**!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =============================================
# DELETE CALLBACK HANDLER (NEW)
# =============================================
@Client.on_callback_query(filters.regex(r"^delete_"))
async def delete_callback_handler(client, query: CallbackQuery):
    """Handle delete confirmations"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "delete_cancel":
        await query.message.edit_text("❌ Deletion cancelled.")
        await query.answer("Cancelled")
        return
    
    if data == "delete_main_confirm":
        await query.message.edit_text("⏳ Deleting all main videos and history...")
        await query.answer("Processing...")
        
        try:
            # Delete main videos and history
            result = await db.delete_main_data()
            if result:
                total = await db.total_files_count()
                await query.message.edit_text(
                    f"✅ **Main Videos and History Deleted Successfully!**\n\n"
                    f"📊 Total videos remaining: {total}"
                )
            else:
                await query.message.edit_text("❌ Failed to delete main data.")
        except Exception as e:
            await query.message.edit_text(f"❌ Error: {str(e)}")
        return
    
    if data == "delete_brazzers_confirm":
        await query.message.edit_text("⏳ Deleting all Brazzers videos and history...")
        await query.answer("Processing...")
        
        try:
            # Delete Brazzers videos and history
            result = await db.delete_brazzers_data()
            if result:
                total = await db.total_brazzers_videos()
                await query.message.edit_text(
                    f"✅ **Brazzers Videos and History Deleted Successfully!**\n\n"
                    f"📊 Total Brazzers videos remaining: {total}"
                )
            else:
                await query.message.edit_text("❌ Failed to delete Brazzers data.")
        except Exception as e:
            await query.message.edit_text(f"❌ Error: {str(e)}")
        return
