import asyncio
import time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from info import ADMINS
from database.users_db import db  
from utils import temp, get_progress_bar, get_readable_time

lock = asyncio.Lock()
INDEX_CACHE = {}

# =================================================
# 📥 CALLBACK QUERY HANDLER
# =================================================
@Client.on_callback_query()
async def index_files(bot, query):
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
    
    # Sirf index wale callbacks handle karo
    if not data.startswith('index#'):
        return
    
    action = data.split("#")[1]
    
    # Cancel
    if action == 'cancel':
        temp.CANCEL = True
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.message.edit("🛑 Indexing Cancelled.")
        return

    # Check cache
    if user_id not in INDEX_CACHE:
        await query.answer("⚠️ Session Expired. Please use /index again.", show_alert=True)
        await query.message.delete()
        return

    data_cache = INDEX_CACHE[user_id]
    chat = data_cache['chat']
    lst_msg_id = data_cache['lst_msg_id']
    skip = data_cache['skip']

    # YES button - Show menu
    if action == 'yes':
        buttons = [
            [
                InlineKeyboardButton('🎬 Video Index', callback_data='index#start_main'),
                InlineKeyboardButton('🔞 Brazzers Index', callback_data='index#start_brazzers')
            ],
            [InlineKeyboardButton('❌ Cancel', callback_data='index#cancel')]
        ]
        await query.message.edit(
            text="<b>📂 Select Database to Save Files:</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Start Main Indexing
    elif action == 'start_main':
        await query.message.edit("<b>🚀 Main Video Indexing started...</b>")
        await index_files_to_db(lst_msg_id, chat, query.message, bot, skip, "main")
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return
    
    # Start Brazzers Indexing
    elif action == 'start_brazzers':
        await query.message.edit("<b>🚀 Brazzers Indexing started...</b>")
        await index_files_to_db(lst_msg_id, chat, query.message, bot, skip, "brazzers")
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return

# =================================================
# 📥 COMMAND HANDLER (/index)
# =================================================
@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def send_for_index(bot, message: Message):
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process completes.')
        
    i = await message.reply("Forward last message from channel OR send last message link.")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except Exception as e:
        await i.delete()
        return await message.reply(f"Timeout/Error: {e}")
    
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
        await message.reply('❌ Forward a message or send a valid link.')
        return

    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply("I can index only channels.")
    except Exception as e:
        return await message.reply(f'Error: {e}')

    s = await message.reply("Send skip number (e.g., 0):")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=30)
        skip = int(msg.text)
    except:
        await s.delete()
        return await message.reply("❌ Invalid Number.")
    
    await s.delete()

    # Store in Cache
    INDEX_CACHE[message.from_user.id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip
    }

    buttons = [[InlineKeyboardButton('✅ YES', callback_data='index#yes')]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply(
        f'Do you want to index <b>{chat.title}</b>?\n\n'
        f'🆔 ID: <code>{chat.id}</code>\n'
        f'📨 Total Messages: <code>{last_msg_id}</code>\n'
        f'⏭ Skip: <code>{skip}</code>',
        reply_markup=reply_markup
    )

# =================================================
# ⚙️ INDEXING LOGIC
# =================================================
async def index_files_to_db(lst_msg_id, chat, msg, bot, skip, target_db):
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
                    await msg.edit("🛑 Indexing Cancelled!")
                    return

                end_id = min(current + BATCH_SIZE, lst_msg_id + 1)
                ids = list(range(current, end_id))
                
                try:
                    messages = await bot.get_messages(chat, ids)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    messages = await bot.get_messages(chat, ids)
                except Exception as e:
                    errors += len(ids)
                    current += BATCH_SIZE
                    continue

                for message in messages:
                    if temp.CANCEL:
                        break
                    
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
                        print(f"Error: {e}")
                        errors += 1

                current += BATCH_SIZE
                
                # Progress update
                                percentage = (min(current, lst_msg_id) / lst_msg_id) * 100
                prog_bar = get_progress_bar(percentage)
                elapsed_time = get_readable_time(time.time() - start_time)
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Video"
                
                # 🛑 CANCEL BUTTON - YAHI SE CHANGE HUA HAI
                btn = [[InlineKeyboardButton('🛑 CANCEL', callback_data='index#cancel')]]
                
                try:
                    await msg.edit(
                        f"📊 <b>{db_label} Indexing Progress</b>\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📥 Scanned: <code>{min(current, lst_msg_id)}/{lst_msg_id}</code>\n"
                        f"✅ Saved: <code>{total_files}</code>\n"
                        f"♻️ Duplicates: <code>{duplicate}</code>\n"
                        f"⏱ Elapsed: <code>{elapsed_time}</code>",
                        reply_markup=InlineKeyboardMarkup(btn)  # ✅ YEH LINE ADD HUI HAI
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except:
                    pass

            time_taken = get_readable_time(time.time() - start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Video"
            
            await msg.edit(
                f"✅ <b>{db_label} Indexing Completed!</b>\n"
                f"⏱ Time: {time_taken}\n"
                f"✅ Saved: <code>{total_files}</code>\n"
                f"♻️ Duplicates: <code>{duplicate}</code>"
            )

        except Exception as e:
            await msg.edit(f"❌ Error: {e}")
