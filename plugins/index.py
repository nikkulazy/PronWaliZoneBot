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
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process completes.')
        
    i = await message.reply("Forward last message from channel OR send last message link.")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except asyncio.TimeoutError:
        await i.delete()
        return await message.reply("❌ Timeout! Please send /index again.")
    except Exception as e:
        await i.delete()
        return await message.reply(f"Listener Error: {e}")
    
    await i.delete()
    
    last_msg_id = 0
    chat_id = None
    
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            parts = msg.text.split("/")
            last_msg_id = int(parts[-1])
            chat_id_str = parts[-2]
            if chat_id_str.isdigit():
                chat_id = int(f"-100{chat_id_str}")
            else:
                chat_id = chat_id_str
        except:
            await message.reply('❌ Invalid message link!')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.id
    else:
        await message.reply('❌ Forward a channel message or send valid link.')
        return

    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply("I can index only channels.")
    except Exception as e:
        return await message.reply(f'Error: {e}')

    s = await message.reply("Send skip number (0 means start from first):")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
        skip = int(msg.text)
    except asyncio.TimeoutError:
        await s.delete()
        return await message.reply("❌ Timeout!")
    except ValueError:
        await s.delete()
        return await message.reply("❌ Send a valid number!")
    
    await s.delete()

    # Store in Cache
    INDEX_CACHE[message.from_user.id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip,
        'chat_title': chat.title
    }

    buttons = [
        [InlineKeyboardButton('✅ YES', callback_data='index_yes')],
        [InlineKeyboardButton('🔚 CLOSE', callback_data='close_data')]
    ]
    
    await message.reply(
        f'<b>Do you want to index?</b>\n\n'
        f'📢 Channel: {chat.title}\n'
        f'🆔 ID: <code>{chat.id}</code>\n'
        f'📨 Total Msg: <code>{last_msg_id}</code>\n'
        f'⏭ Skip: <code>{skip}</code>',
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='HTML'
    )

# =================================================
# 📥 CALLBACK QUERY HANDLER (Index ke liye)
# =================================================
@Client.on_callback_query()
async def index_callback(bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    # Close button
    if data == 'close_data':
        try:
            await query.message.delete()
        except:
            pass
        return
    
    # YES button
    if data == 'index_yes':
        if user_id not in INDEX_CACHE:
            await query.message.edit("❌ Session expired! Send /index again.")
            return
        
        cache = INDEX_CACHE[user_id]
        
        buttons = [
            [InlineKeyboardButton('🎬 Main Videos', callback_data='index_start_main')],
            [InlineKeyboardButton('🔞 Brazzers Videos', callback_data='index_start_brazzers')],
            [InlineKeyboardButton('❌ Cancel', callback_data='index_cancel')]
        ]
        
        await query.message.edit(
            "<b>📂 Select Database:</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
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
            await query.message.edit("❌ Session expired!")
            return
        
        cache = INDEX_CACHE[user_id]
        await query.message.edit("🚀 Main Video Indexing started...")
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
        await query.message.edit("🚀 Brazzers Indexing started...")
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
                    errors += len(ids)
                    current += BATCH_SIZE
                    continue

                for message in messages:
                    if temp.CANCEL: break
                    
                    try:
                        if not message or message.empty:
                            deleted += 1
                            continue
                        
                        if not message.media:
                            no_media += 1
                            continue
                        
                        if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                            unsupported += 1
                            continue
                        
                        media = getattr(message, message.media.value, None)
                        if not media:
                            unsupported += 1
                            continue
                        
                        file_id = media.file_id
                        file_unique_id = media.file_unique_id
                        
                        # DB SELECTION
                        if target_db == "brazzers":
                            is_new = await db.add_brazzers_video(file_unique_id, file_id)
                            if is_new is None: is_new = True 
                        else:
                            is_new = await db.add_video(file_unique_id, file_id)
                        
                        if is_new:
                            total_files += 1
                        else:
                            duplicate += 1

                    except Exception as e:
                        print(f"Error: {e}")
                        errors += 1
                    
                    current += 1

                # Update Progress
                percentage = (min(current, lst_msg_id) / lst_msg_id) * 100
                prog_bar = get_progress_bar(percentage)
                elapsed_time = get_readable_time(time.time() - start_time)
                
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Video"

                btn = [[InlineKeyboardButton('🛑 CANCEL', callback_data='index_cancel')]]
                
                try:
                    await msg_obj.edit(
                        f"📊 <b>{db_label} Indexing</b>\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📥 Scanned: <code>{min(current, lst_msg_id)}/{lst_msg_id}</code>\n"
                        f"✅ Saved: <code>{total_files}</code>\n"
                        f"♻️ Duplicates: <code>{duplicate}</code>\n"
                        f"⚠️ Errors: <code>{errors}</code>\n"
                        f"⏱ Elapsed: <code>{elapsed_time}</code>",
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value) 
                except:
                    pass

            # Final Message
            time_taken = get_readable_time(time.time()-start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Video"
            
            await msg_obj.edit(
                f"✅ <b>{db_label} Indexing Completed!</b>\n"
                f"⏱ Time: {time_taken}\n"
                f"📥 Scanned: <code>{lst_msg_id - skip}</code>\n"
                f"✅ Saved: <code>{total_files}</code>\n"
                f"♻️ Duplicates: <code>{duplicate}</code>\n"
                f"⚠️ Errors: <code>{errors}</code>"
            )

        except Exception as e:
            await msg_obj.edit(f"❌ Error: {e}")
