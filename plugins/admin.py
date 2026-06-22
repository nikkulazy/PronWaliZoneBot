from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from info import ADMINS

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

# Add this temporary command to generate short IDs for existing videos
@Client.on_message(filters.command("gen_ids") & filters.private)
async def generate_short_ids(client, message):
    """Generate short IDs for all existing videos"""
    count = 0
    # For main videos
    async for video in db.videos.find({}):
        if "short_id" not in video:
            short_id = await db.generate_short_id()
            while await db.videos.find_one({"short_id": short_id}):
                short_id = await db.generate_short_id()
            await db.videos.update_one(
                {"_id": video["_id"]},
                {"$set": {"short_id": short_id}}
            )
            count += 1
    
    # For Brazzers videos
    async for video in db.brazzers.find({}):
        if "short_id" not in video:
            short_id = await db.generate_short_id()
            while await db.brazzers.find_one({"short_id": short_id}):
                short_id = await db.generate_short_id()
            await db.brazzers.update_one(
                {"_id": video["_id"]},
                {"$set": {"short_id": short_id}}
            )
            count += 1
    
    await message.reply(f"✅ Generated {count} short IDs!")
