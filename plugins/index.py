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
# 📥 INDEX COMMAND HANDLER
# =================================================
@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def send_for_index(bot, message: Message):
    user_id = message.from_user.id
    
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process completes.')
    
    # Step 1: Get channel message
    msg1 = await message.reply(
        "**📌 Step 1/2:**\n\n"
        "Send me a channel message in ANY of these ways:\n\n"
        "1️⃣ Forward ANY message from the channel\n"
        "2️⃣ Send message link (e.g., https://t.me/channel/123)\n\n"
        "⏱️ You have 60 seconds."
    )
    
    try:
        response = await bot.listen(user_id, timeout=60)
    except asyncio.TimeoutError:
        await msg1.delete()
        return await message.reply("❌ Timeout! Please send /index again.")
    except Exception as e:
        await msg1.delete()
        return await message.reply(f"❌ Error: {e}")
    
    await msg1.delete()
    
    last_msg_id = 0
    chat_id = None
    
    # Parse message link
    if response.text and "https://t.me/" in response.text:
        try:
            parts = response.text.split("/")
            last_msg_id = int(parts[-1])
            chat_id_str = parts[-2]
            if chat_id_str.isdigit():
                chat_id = int(f"-100{chat_id_str}")
            else:
                chat_id = chat_id_str
        except:
            await message.reply('❌ Invalid message link!')
            return
    # Parse forwarded message
    elif response.forward_from_chat:
        if response.forward_from_chat.type == enums.ChatType.CHANNEL:
            last_msg_id = response.forward_from_message_id
            chat_id = response.forward_from_chat.id
        else:
            await message.reply('❌ Please forward from a CHANNEL, not a group!')
            return
    else:
        await message.reply('❌ Please forward a channel message or send a valid message link!')
        return

    # Verify channel
    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply("❌ This is not a channel!")
    except Exception as e:
        return await message.reply(f'❌ Cannot access channel: {e}')

    # Step 2: Get skip number
    msg2 = await message.reply(
        f"**📌 Step 2/2:**\n\n"
        f"📢 Channel: {chat.title}\n"
        f"📨 Last Message ID: {last_msg_id}\n\n"
        f"Send skip number (0 = start from first message):\n\n"
        f"⏱️ You have 60 seconds."
    )
    
    try:
        skip_response = await bot.listen(user_id, timeout=60)
        skip = int(skip_response.text.strip())
    except asyncio.TimeoutError:
        await msg2.delete()
        return await message.reply("❌ Timeout! Please send /index again.")
    except ValueError:
        await msg2.delete()
        return await message.reply("❌ Invalid number! Please send a number like 0, 100, 500.")
    except Exception as e:
        await msg2.delete()
        return await message.reply(f"❌ Error: {e}")
    
    await msg2.delete()

    # Store in Cache
    INDEX_CACHE[user_id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip,
        'chat_title': chat.title
    }

    # 🔥 DIRECT DATABASE SELECTION - NO YES BUTTON 🔥
    buttons = [
        [InlineKeyboardButton('🎬 MAIN VIDEOS', callback_data='index_start_main')],
        [InlineKeyboardButton('🔞 BRAZZERS VIDEOS', callback_data='index_start_brazzers')],
        [InlineKeyboardButton('❌ CANCEL', callback_data='index_cancel')]
    ]
    
    await message.reply(
        f"**📊 Channel Ready for Indexing**\n\n"
        f"📢 Channel: {chat.title}\n"
        f"🆔 ID: `{chat.id}`\n"
        f"📨 Total Messages: `{last_msg_id}`\n"
        f"⏭ Skip First: `{skip}` messages\n"
        f"📁 Will scan: `{last_msg_id - skip}` messages\n\n"
        f"**Select where to save videos:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# =================================================
# 📥 CALLBACK QUERY HANDLER
# =================================================
@Client.on_callback_query()
async def index_callback(bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    print(f"DEBUG: Callback received: {data}")  # Debug
    
    # Cancel button
    if data == 'index_cancel':
        temp.CANCEL = True
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.message.edit("🛑 Indexing Cancelled.")
        return
    
    # Start Main Indexing
    if data == 'index_start_main':
        if user_id not in INDEX_CACHE:
            await query.message.edit("❌ Session expired! Send /index again.")
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
    if data == 'index_start_brazzers':
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
# ⚙️ INDEXING FUNCTION
# =================================================
async def index_files_to_db(lst_msg_id, chat_id, msg_obj, bot, skip, target_db):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = skip + 1 
    BATCH_SIZE = 20

    async with lock:
        try:
            temp.CANCEL = False
            
            while current <= lst_msg_id:
                
                if temp.CANCEL:
                    time_taken = get_readable_time(time.time()-start_time)
                    await msg_obj.edit(f"🛑 Cancelled!\n⏱ Time: {time_taken}\n✅ Saved: {total_files}")
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
                    print(f"Get messages error: {e}")
                    errors += len(ids)
                    current += BATCH_SIZE
                    continue

                for message in messages:
                    if temp.CANCEL: 
                        break
                    
                    try:
                        if not message or message.empty:
                            deleted += 1
                            current += 1
                            continue
                        
                        if not message.media:
                            no_media += 1
                            current += 1
                            continue
                        
                        if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                            unsupported += 1
                            current += 1
                            continue
                        
                        media = getattr(message, message.media.value, None)
                        if not media:
                            unsupported += 1
                            current += 1
                            continue
                        
                        file_id = media.file_id
                        file_unique_id = media.file_unique_id
                        
                        # DB SELECTION
                        if target_db == "brazzers":
                            is_new = await db.add_brazzers_video(file_unique_id, file_id)
                            if is_new is None: 
                                is_new = True 
                        else:
                            is_new = await db.add_video(file_unique_id, file_id)
                        
                        if is_new:
                            total_files += 1
                        else:
                            duplicate += 1

                    except Exception as e:
                        print(f"Error processing: {e}")
                        errors += 1
                    
                    current += 1

                # Update Progress
                scanned = min(current, lst_msg_id)
                percentage = (scanned / lst_msg_id) * 100
                prog_bar = get_progress_bar(percentage)
                elapsed_time = get_readable_time(time.time() - start_time)
                
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main Video"

                btn = [[InlineKeyboardButton('🛑 CANCEL', callback_data='index_cancel')]]
                
                try:
                    await msg_obj.edit(
                        f"📊 **{db_label} Indexing Progress**\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📥 Scanned: `{scanned}/{lst_msg_id}`\n"
                        f"✅ Saved: `{total_files}`\n"
                        f"♻️ Duplicates: `{duplicate}`\n"
                        f"🚫 No Media: `{no_media}`\n"
                        f"⚠️ Errors: `{errors}`\n"
                        f"⏱ Elapsed: `{elapsed_time}`",
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value) 
                except Exception as e:
                    print(f"Progress update error: {e}")

            # Final Message
            time_taken = get_readable_time(time.time() - start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main Video"
            
            await msg_obj.edit(
                f"✅ **{db_label} Indexing Completed!**\n\n"
                f"⏱ Time: `{time_taken}`\n"
                f"📥 Scanned: `{lst_msg_id - skip}`\n"
                f"✅ Saved: `{total_files}`\n"
                f"♻️ Duplicates: `{duplicate}`\n"
                f"🚫 Non-Media: `{no_media + unsupported}`\n"
                f"⚠️ Errors: `{errors}`"
            )

        except Exception as e:
            print(f"Critical error: {e}")
            await msg_obj.edit(f"❌ Critical Error: {str(e)[:200]}")
