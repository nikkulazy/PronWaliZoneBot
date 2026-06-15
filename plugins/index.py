import asyncio
import time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import ADMINS
from database.users_db import db  
from utils import temp, get_progress_bar, get_readable_time

lock = asyncio.Lock()
INDEX_CACHE = {}

# =================================================
# 📥 CALLBACK QUERY HANDLER
# =================================================
@Client.on_callback_query(filters.regex(r'^index_'))
async def index_callback(bot, query: CallbackQuery):
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    print(f"DEBUG: Callback data = {data}")  # Debug
    
    # Cancel indexing
    if data == "index_cancel":
        temp.CANCEL = True
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.message.edit("🛑 Indexing Cancelled!")
        return
    
    # Close button
    if data == "close_data":
        try:
            await query.message.delete()
        except:
            pass
        return
    
    # YES button - show database selection
    if data == "index_yes":
        if user_id not in INDEX_CACHE:
            await query.message.edit("❌ Session expired! Send /index again.")
            return
        
        buttons = [
            [InlineKeyboardButton("🎬 Main Videos", callback_data="index_start_main")],
            [InlineKeyboardButton("🔞 Brazzers Videos", callback_data="index_start_brazzers")],
            [InlineKeyboardButton("❌ Cancel", callback_data="index_cancel")]
        ]
        
        await query.message.edit(
            "📂 **Select Database to save videos:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # Start Main Video Indexing
    if data == "index_start_main":
        if user_id not in INDEX_CACHE:
            await query.message.edit("❌ Session expired!")
            return
        
        cache = INDEX_CACHE[user_id]
        await query.message.edit("🚀 **Main Video Indexing Started...**")
        
        await index_files_to_db(
            cache['lst_msg_id'], 
            cache['chat'], 
            query.message, 
            bot, 
            cache['skip'], 
            "main"
        )
        
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return
    
    # Start Brazzers Indexing
    if data == "index_start_brazzers":
        if user_id not in INDEX_CACHE:
            await query.message.edit("❌ Session expired!")
            return
        
        cache = INDEX_CACHE[user_id]
        await query.message.edit("🚀 **Brazzers Indexing Started...**")
        
        await index_files_to_db(
            cache['lst_msg_id'], 
            cache['chat'], 
            query.message, 
            bot, 
            cache['skip'], 
            "brazzers"
        )
        
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return

# =================================================
# 📥 INDEX COMMAND
# =================================================
@Client.on_message(filters.command("index") & filters.private & filters.user(ADMINS))
async def index_command(bot, message: Message):
    user_id = message.from_user.id
    
    if lock.locked():
        await message.reply("⚠️ Another indexing process is running! Please wait.")
        return
    
    # Step 1: Get channel message
    msg1 = await message.reply(
        "📌 **Step 1/3:**\n\n"
        "Send me a message from the channel in one of these ways:\n\n"
        "1️⃣ Forward any message from the channel\n"
        "2️⃣ Send message link (e.g., https://t.me/channel/123)\n\n"
        "⏱️ You have 60 seconds."
    )
    
    try:
        response = await bot.listen(chat_id=user_id, timeout=60)
    except asyncio.TimeoutError:
        await msg1.delete()
        await message.reply("❌ Timeout! Please send /index again.")
        return
    except Exception as e:
        await msg1.delete()
        await message.reply(f"❌ Error: {e}")
        return
    
    await msg1.delete()
    
    # Parse channel and message ID
    chat_id = None
    last_msg_id = None
    
    # Check if it's a forwarded message
    if response.forward_from_chat:
        chat_id = response.forward_from_chat.id
        last_msg_id = response.forward_from_message_id
    # Check if it's a message link
    elif response.text and "https://t.me/" in response.text:
        try:
            parts = response.text.split("/")
            last_msg_id = int(parts[-1])
            chat_id_str = parts[-2]
            if chat_id_str.isdigit():
                chat_id = int(f"-100{chat_id_str}")
            else:
                chat_id = chat_id_str
        except:
            await message.reply("❌ Invalid message link!")
            return
    else:
        await message.reply("❌ Please forward a channel message or send a valid message link!")
        return
    
    # Verify channel
    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            await message.reply("❌ This is not a channel!")
            return
    except Exception as e:
        await message.reply(f"❌ Cannot access channel: {e}")
        return
    
    # Step 2: Get skip number
    msg2 = await message.reply(
        f"📌 **Step 2/3:**\n\n"
        f"Channel: {chat.title}\n"
        f"Last Message ID: {last_msg_id}\n\n"
        f"Send skip count (number of messages to skip from start):\n"
        f"Example: `0` = start from first message\n"
        f"`100` = skip first 100 messages\n\n"
        f"⏱️ You have 60 seconds."
    )
    
    try:
        response = await bot.listen(chat_id=user_id, timeout=60)
        skip = int(response.text)
    except asyncio.TimeoutError:
        await msg2.delete()
        await message.reply("❌ Timeout! Please send /index again.")
        return
    except ValueError:
        await msg2.delete()
        await message.reply("❌ Please send a valid number!")
        return
    except Exception as e:
        await msg2.delete()
        await message.reply(f"❌ Error: {e}")
        return
    
    await msg2.delete()
    
    # Save to cache
    INDEX_CACHE[user_id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip
    }
    
    # Step 3: Confirmation
    buttons = [
        [InlineKeyboardButton("✅ YES, Start Indexing", callback_data="index_yes")],
        [InlineKeyboardButton("🔚 CLOSE", callback_data="close_data")]
    ]
    
    await message.reply(
        f"📊 **Index Confirmation**\n\n"
        f"📢 Channel: {chat.title}\n"
        f"🆔 ID: `{chat.id}`\n"
        f"📨 Total Messages: `{last_msg_id}`\n"
        f"⏭ Skip First: `{skip}` messages\n\n"
        f"⚠️ Estimated videos to scan: `{last_msg_id - skip}`\n\n"
        f"Start indexing?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# =================================================
# ⚙️ INDEXING FUNCTION
# =================================================
async def index_files_to_db(lst_msg_id, chat_id, msg_obj, bot, skip, target_db):
    start_time = time.time()
    total_saved = 0
    duplicate = 0
    errors = 0
    no_media = 0
    current = skip + 1
    BATCH_SIZE = 20
    
    async with lock:
        try:
            temp.CANCEL = False
            
            while current <= lst_msg_id:
                if temp.CANCEL:
                    await msg_obj.edit("🛑 Indexing Cancelled!")
                    return
                
                end_id = min(current + BATCH_SIZE, lst_msg_id + 1)
                ids = list(range(current, end_id))
                
                if not ids:
                    break
                
                try:
                    messages = await bot.get_messages(chat_id, ids)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    messages = await bot.get_messages(chat_id, ids)
                except Exception as e:
                    print(f"Error getting messages: {e}")
                    errors += len(ids)
                    current += BATCH_SIZE
                    continue
                
                for message in messages:
                    if temp.CANCEL:
                        break
                    
                    try:
                        if not message or message.empty:
                            current += 1
                            continue
                        
                        # Check for video
                        video = message.video or message.document
                        if not video:
                            no_media += 1
                            current += 1
                            continue
                        
                        file_id = video.file_id
                        file_unique_id = video.file_unique_id
                        
                        # Add to database
                        if target_db == "brazzers":
                            is_new = await db.add_brazzers_video(file_unique_id, file_id)
                        else:
                            is_new = await db.add_video(file_unique_id, file_id)
                        
                        if is_new:
                            total_saved += 1
                        else:
                            duplicate += 1
                            
                    except Exception as e:
                        print(f"Error: {e}")
                        errors += 1
                    
                    current += 1
                
                # Update progress
                scanned = min(current, lst_msg_id)
                percentage = (scanned / lst_msg_id) * 100
                prog_bar = get_progress_bar(percentage)
                elapsed = get_readable_time(time.time() - start_time)
                
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main"
                
                try:
                    await msg_obj.edit(
                        f"📊 **{db_label} Indexing Progress**\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📥 Scanned: `{scanned}/{lst_msg_id}`\n"
                        f"✅ Saved: `{total_saved}`\n"
                        f"♻️ Duplicate: `{duplicate}`\n"
                        f"🚫 No Media: `{no_media}`\n"
                        f"⚠️ Errors: `{errors}`\n"
                        f"⏱ Time: `{elapsed}`",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Cancel", callback_data="index_cancel")]])
                    )
                except:
                    pass
            
            # Final message
            elapsed = get_readable_time(time.time() - start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main"
            
            await msg_obj.edit(
                f"✅ **{db_label} Indexing Completed!**\n\n"
                f"⏱ Time: `{elapsed}`\n"
                f"📥 Scanned: `{lst_msg_id - skip}`\n"
                f"✅ Saved: `{total_saved}`\n"
                f"♻️ Duplicate: `{duplicate}`\n"
                f"🚫 No Media: `{no_media}`\n"
                f"⚠️ Errors: `{errors}`"
            )
            
        except Exception as e:
            print(f"Indexing error: {e}")
            await msg_obj.edit(f"❌ Error: {str(e)[:200]}")
