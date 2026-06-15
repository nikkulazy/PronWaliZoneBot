import asyncio
import time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import ADMINS, VIDEO_CHANNEL
from database.users_db import db  
from utils import temp, get_progress_bar, get_readable_time

lock = asyncio.Lock()

# Temporary Storage for Index Data
INDEX_CACHE = {}

# =================================================
# 📥 CALLBACK QUERY HANDLER (FIXED)
# =================================================
@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query: CallbackQuery):
    await query.answer()
    
    parts = query.data.split("#")
    if len(parts) < 2:
        return
    
    action = parts[1]
    user_id = query.from_user.id
    
    print(f"DEBUG: Action = {action}, User = {user_id}")  # Debug ke liye

    # Cancel Action
    if action == 'cancel':
        temp.CANCEL = True
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.message.edit("🛑 Indexing Cancelled.")
        return

    # Check if data exists in cache
    if user_id not in INDEX_CACHE:
        await query.answer("⚠️ Session Expired. Please use /index again.", show_alert=True)
        await query.message.delete()
        return

    # Fetch Data from Cache
    data = INDEX_CACHE[user_id]
    chat = data['chat']
    lst_msg_id = data['lst_msg_id']
    skip = data['skip']

    # Step 1: Selection Menu (YES ke baad)
    if action == 'yes':
        buttons = [
            [
                InlineKeyboardButton('🎬 Video Index', callback_data='index#start_main'),
                InlineKeyboardButton('🔞 Brazzers Index', callback_data='index#start_brazzers')
            ],
            [
                InlineKeyboardButton('❌ Cancel', callback_data='index#cancel')
            ]
        ]
        
        await query.message.edit(
            text="<b>📂 Select Database to Save Files:</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Start Indexing
    elif action == 'start_main':
        db_name = "Main Video"
        target_db = "main"
        await query.message.edit(f"<b>🚀 {db_name} Indexing started...</b>")
        
        # Start Indexing
        await index_files_to_db(lst_msg_id, chat, query.message, bot, skip, target_db)
        
        # Cleanup Cache after finish
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
    
    elif action == 'start_brazzers':
        db_name = "Brazzers"
        target_db = "brazzers"
        await query.message.edit(f"<b>🚀 {db_name} Indexing started...</b>")
        
        # Start Indexing
        await index_files_to_db(lst_msg_id, chat, query.message, bot, skip, target_db)
        
        # Cleanup Cache after finish
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]

# =================================================
# 📥 COMMAND HANDLER (/index)
# =================================================
@Client.on_message(filters.command('index') & filters.private & filters.incoming & filters.user(ADMINS))
async def send_for_index(bot, message: Message):
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process completes.')
        
    i = await message.reply("📌 Forward last message from channel OR send last message link.")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except asyncio.TimeoutError:
        await i.delete()
        return await message.reply("❌ Timeout! Please send /index again.")
    except Exception as e:
        await i.delete()
        return await message.reply(f"❌ Error: {e}")
    
    await i.delete()
    
    last_msg_id = 0
    chat_id = None
    
    # Parse message link or forwarded message
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            parts = msg.text.split("/")
            last_msg_id = int(parts[-1])
            chat_id_str = parts[-2]
            if chat_id_str.isdigit():
                chat_id = int(f"-100{chat_id_str}")
            else:
                chat_id = chat_id_str
        except Exception as e:
            await message.reply(f'❌ Invalid message link! Error: {e}')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.id
    else:
        await message.reply('❌ Please forward a message from channel OR send a valid message link.')
        return

    # Get channel info
    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply("❌ I can only index channels.")
    except Exception as e:
        return await message.reply(f'❌ Error getting channel: {e}')

    # Get skip number
    s = await message.reply("📝 Send skip message number (e.g., 0 means start from first):")
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
        skip = int(msg.text)
    except asyncio.TimeoutError:
        await s.delete()
        return await message.reply("❌ Timeout! Please send /index again.")
    except ValueError:
        await s.delete()
        return await message.reply("❌ Invalid Number! Please send a valid integer.")
    except Exception as e:
        await s.delete()
        return await message.reply(f"❌ Error: {e}")
    await s.delete()

    # Store in Cache
    INDEX_CACHE[message.from_user.id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip
    }

    buttons = [
        [InlineKeyboardButton('✅ YES, Start Indexing', callback_data='index#yes')],
        [InlineKeyboardButton('🔚 CLOSE', callback_data='close_data')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply(
        f'📊 <b>Channel Index Confirmation</b>\n\n'
        f'📢 Channel: <b>{chat.title}</b>\n'
        f'🆔 ID: <code>{chat.id}</code>\n'
        f'📨 Total Messages: <code>{last_msg_id}</code>\n'
        f'⏭ Skip First: <code>{skip}</code> messages\n\n'
        f'Do you want to start indexing?',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# =================================================
# ⚙️ MAIN INDEXING LOGIC (FIXED)
# =================================================
async def index_files_to_db(lst_msg_id, chat, msg_obj, bot, skip, target_db):
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
                    time_taken = get_readable_time(time.time() - start_time)
                    await msg_obj.edit(f"🛑 Indexing Cancelled!\n⏱ Time: {time_taken}\n✅ Saved: {total_files}")
                    return

                end_id = min(current + BATCH_SIZE, lst_msg_id + 1)
                ids = list(range(current, end_id))
                
                if not ids:
                    break

                try:
                    messages = await bot.get_messages(chat, ids)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    messages = await bot.get_messages(chat, ids)
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
                            continue
                        
                        if not message.media:
                            no_media += 1
                            continue
                        
                        # Check for VIDEO or DOCUMENT
                        if message.video:
                            media = message.video
                        elif message.document:
                            media = message.document
                        else:
                            unsupported += 1
                            continue
                        
                        if not media:
                            unsupported += 1
                            continue
                        
                        file_id = media.file_id
                        file_unique_id = media.file_unique_id
                        
                        # DB SELECTION LOGIC
                        if target_db == "brazzers":
                            result = await db.add_brazzers_video(file_unique_id, file_id)
                            is_new = result if result is not None else True
                        else:
                            result = await db.add_video(file_unique_id, file_id)
                            is_new = result if result is not None else True
                        
                        if is_new:
                            total_files += 1
                        else:
                            duplicate += 1

                    except Exception as e:
                        print(f"Error processing message: {e}")
                        errors += 1

                # Update Progress
                current += BATCH_SIZE
                
                # Live Update Progress Bar
                percentage = min((current / lst_msg_id) * 100, 100)
                prog_bar = get_progress_bar(percentage)
                elapsed_time = get_readable_time(time.time() - start_time)
                
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main Video"

                btn = [[InlineKeyboardButton('🛑 CANCEL', callback_data='index#cancel')]]
                
                try:
                    await msg_obj.edit(
                        f"📊 <b>{db_label} Indexing Progress</b>\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📥 Scanned: <code>{min(current, lst_msg_id)}/{lst_msg_id}</code>\n"
                        f"✅ Saved: <code>{total_files}</code>\n"
                        f"♻️ Duplicates: <code>{duplicate}</code>\n"
                        f"🗑 Invalid/Empty: <code>{deleted}</code>\n"
                        f"🚫 No Media: <code>{no_media}</code>\n"
                        f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                        f"⚠️ Errors: <code>{errors}</code>\n"
                        f"⏱ Elapsed: <code>{elapsed_time}</code>",
                        reply_markup=InlineKeyboardMarkup(btn),
                        parse_mode='HTML'
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value) 
                except Exception as e:
                    print(f"Progress update error: {e}")

            # Final Message
            time_taken = get_readable_time(time.time() - start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main Video"
            
            final_buttons = [[InlineKeyboardButton('🔚 CLOSE', callback_data='close_data')]]
            
            await msg_obj.edit(
                f"✅ <b>{db_label} Indexing Completed!</b>\n\n"
                f"⏱ Time Taken: <code>{time_taken}</code>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📥 Total Scanned: <code>{lst_msg_id - skip}</code>\n"
                f"✅ New Saved: <code>{total_files}</code>\n"
                f"♻️ Duplicates: <code>{duplicate}</code>\n"
                f"🗑 Invalid/Empty: <code>{deleted}</code>\n"
                f"🚫 Non-Media: <code>{no_media}</code>\n"
                f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                f"⚠️ Errors: <code>{errors}</code>",
                reply_markup=InlineKeyboardMarkup(final_buttons),
                parse_mode='HTML'
            )

        except Exception as e:
            print(f"Critical Indexing Error: {e}")
            await msg_obj.edit(f"❌ Critical Error: {str(e)[:200]}")
