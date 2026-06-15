import datetime
import asyncio
import time
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID, ADMINS
from utils import temp, is_user_joined, get_progress_bar, get_readable_time
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# ========== INDEXING CACHE ==========
lock = asyncio.Lock()
INDEX_CACHE = {}

# =================================================
# 🚀 START COMMAND
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention
    
    if FSUB and not await is_user_joined(client, message):
        return
        
    argument = message.command[1] if len(message.command) > 1 else None

    if argument and argument.startswith('avbotz'):
        await verify_user_on_start(client, message)
        return

    if argument == "terms":
        await send_legal_text(client, message, script.TERMS_TXT)
        return
    elif argument == "disclaimer":
        await send_legal_text(client, message, script.DISCLAIMER_TXT)
        return
    elif argument == "help":
        await send_legal_text(client, message, script.HELP_TXT)
        return
    elif argument == "about":
        await send_about_text(client, message)
        return

    if argument and argument.startswith("reff_"):
        try:
            await refer_on_start(client, message)
            return 
        except Exception as e:
            print(f"Referral Error: {e}")

    if argument and argument.startswith("avx-"):
        search_id = argument.replace("avx-", "")
        await send_requested_file(client, message, user_id, search_id)
        return

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        try:
            await client.send_message(
                LOG_CHANNEL,
                script.LOG_TEXT.format(me2, user_id, mention)
            )
        except Exception:
            pass
    
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("💢𝗚𝗘𝗧 𝗩𝗜𝗗𝗘𝗢𝗦💢", callback_data='get_video')],
            [
                InlineKeyboardButton("ℹ️ ʜᴇʟᴘ", callback_data='help'),
                InlineKeyboardButton("🧑‍💻 ᴀʙᴏᴜᴛ", callback_data='about')
            ],
            [InlineKeyboardButton("✨ɢᴇᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴄᴇꜱꜱ✨", callback_data='subscription')],
        ]
    )

    sent_msg = await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=inline_keyboard,
        has_spoiler=True
    )
    
    asyncio.create_task(auto_delete_message(message, sent_msg, 300))


# =================================================
# 📜 HELPER HANDLERS
# =================================================

@Client.on_message(filters.command("disclaimer") & filters.private)
async def legal_disclaimer(client, message: Message):
    await send_legal_text(client, message, script.DISCLAIMER_TXT)

@Client.on_message(filters.command("terms") & filters.private)
async def legal_terms(client, message: Message):
    await send_legal_text(client, message, script.TERMS_TXT)

@Client.on_message(filters.command("about") & filters.private)
async def legal_about(client, message: Message):
    await send_about_text(client, message)

@Client.on_message(filters.command("help") & filters.private)
async def legal_help(client, message: Message):
    await send_legal_text(client, message, script.HELP_TXT)
    
async def send_legal_text(client, message, text):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )

async def send_about_text(client, message):
    inline_buttons = [[
        InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    await message.reply_text(
        text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
        reply_markup=InlineKeyboardMarkup(inline_buttons),
        disable_web_page_preview=True
    )


# =========================================================
# 🔙 AUTO DELETE FUNCTION
# =========================================================
async def auto_delete_message(original_msg, sent_msg, delay=30):
    await asyncio.sleep(delay)
    try:
        await sent_msg.delete()
        await original_msg.delete()
    except:
        pass


# =========================================================
# 📥 INDEX COMMAND HANDLER
# =========================================================
@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def send_for_index(bot, message: Message):
    user_id = message.from_user.id
    
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process completes.')
    
    msg1 = await message.reply(
        "**📌 Step 1/2:**\n\n"
        "Send me a channel message:\n\n"
        "1️⃣ Forward ANY message from the channel\n"
        "2️⃣ Send message link (e.g., https://t.me/channel/123)\n\n"
        "⏱️ You have 60 seconds."
    )
    
    try:
        response = await bot.listen(user_id, timeout=60)
    except asyncio.TimeoutError:
        await msg1.delete()
        return await message.reply("❌ Timeout! Send /index again.")
    except Exception as e:
        await msg1.delete()
        return await message.reply(f"❌ Error: {e}")
    
    await msg1.delete()
    
    last_msg_id = 0
    chat_id = None
    
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
    elif response.forward_from_chat:
        if response.forward_from_chat.type == enums.ChatType.CHANNEL:
            last_msg_id = response.forward_from_message_id
            chat_id = response.forward_from_chat.id
        else:
            await message.reply('❌ Please forward from a CHANNEL!')
            return
    else:
        await message.reply('❌ Forward a channel message or send valid link!')
        return

    try:
        chat = await bot.get_chat(chat_id)
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply("❌ This is not a channel!")
    except Exception as e:
        return await message.reply(f'❌ Error: {e}')

    msg2 = await message.reply(
        f"**📌 Step 2/2:**\n\n"
        f"📢 Channel: {chat.title}\n"
        f"📨 Last Message ID: {last_msg_id}\n\n"
        f"Send skip number (0 = start from first):\n\n"
        f"⏱️ You have 60 seconds."
    )
    
    try:
        skip_response = await bot.listen(user_id, timeout=60)
        skip = int(skip_response.text.strip())
    except asyncio.TimeoutError:
        await msg2.delete()
        return await message.reply("❌ Timeout!")
    except ValueError:
        await msg2.delete()
        return await message.reply("❌ Send a valid number!")
    except Exception as e:
        await msg2.delete()
        return await message.reply(f"❌ Error: {e}")
    
    await msg2.delete()

    INDEX_CACHE[user_id] = {
        'chat': chat.id,
        'lst_msg_id': last_msg_id,
        'skip': skip,
        'chat_title': chat.title
    }

    buttons = [
        [InlineKeyboardButton('🎬 MAIN VIDEOS', callback_data='index_start_main')],
        [InlineKeyboardButton('🔞 BRAZZERS VIDEOS', callback_data='index_start_brazzers')],
        [InlineKeyboardButton('❌ CANCEL', callback_data='index_cancel')]
    ]
    
    await message.reply(
        f"**📊 Channel Ready**\n\n"
        f"📢 {chat.title}\n"
        f"📨 Total: {last_msg_id}\n"
        f"⏭ Skip: {skip}\n"
        f"📁 To scan: {last_msg_id - skip}\n\n"
        f"**Select database:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =========================================================
# 🔙 MAIN CALLBACK QUERY HANDLER (SAB KUCH YAHI HAI)
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    # ========== INDEX CALLBACKS ==========
    if data == 'index_cancel':
        temp.CANCEL = True
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        await query.message.edit("🛑 Indexing Cancelled.")
        return
    
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
            client, 
            cache['skip'], 
            "main"
        )
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return
    
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
            client, 
            cache['skip'], 
            "brazzers"
        )
        if user_id in INDEX_CACHE:
            del INDEX_CACHE[user_id]
        return
    
    # ========== DELETE CALLBACKS ==========
    if data == "del_cancel":
        try:
            await query.message.delete()
        except:
            pass
        return

    if data == "del_ask_main":
        await query.message.edit(
            "⚠️ **CONFIRMATION: MAIN VIDEOS**\n\n"
            "Kya aap sach mein **Main Videos & History** delete karna chahte hain?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete Main", callback_data="del_confirm_main")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data="del_cancel")]
            ])
        )
        return
    
    if data == "del_ask_brazzers":
        await query.message.edit(
            "⚠️ **CONFIRMATION: BRAZZERS**\n\n"
            "Kya aap sach mein **Brazzers Videos & History** delete karna chahte hain?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete Brazzers", callback_data="del_confirm_brazzers")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data="del_cancel")]
            ])
        )
        return

    if data == "del_confirm_main":
        await query.message.edit("⏳ **Deleting Main Videos...**")
        try:
            result = await db.delete_all_main_videos()
            await query.message.edit(f"✅ **Deleted {result} Main Videos!**")
        except Exception as e:
            await query.message.edit(f"❌ Error: {e}")
        return

    if data == "del_confirm_brazzers":
        await query.message.edit("⏳ **Deleting Brazzers...**")
        try:
            result = await db.delete_all_brazzers_videos()
            await query.message.edit(f"✅ **Deleted {result} Brazzers Videos!**")
        except Exception as e:
            await query.message.edit(f"❌ Error: {e}")
        return
    
    # ========== NORMAL CALLBACKS ==========
    if data == "close_data":
        try:
            await query.message.delete()
        except:
            pass
        return
    
    if data == "get_video":
        from plugins.get_video import handle_video_request
        try:
            await handle_video_request(client, query.message)
        except Exception as e:
            print(f"Error: {e}")
            await query.message.reply_text("❌ Error getting video.")
        return
    
    if data == "help":
        await query.message.reply_text(
            text=script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]]),
            disable_web_page_preview=True
        )
        return
    
    if data == "about":
        await query.message.reply_text(
            text=script.ABOUT_TXT.format(temp.B_NAME, temp.B_LINK),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]]),
            disable_web_page_preview=True
        )
        return
    
    if data == "subscription":
        from plugins.premium import buy_handler
        await buy_handler(client, query.message)
        return
    
    if data == "myplan":
        from plugins.premium import myplan_handler
        await myplan_handler(client, query.message)
        return
    
    if data == "get":
        buttons = [[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')]]
        if QR_CODE_IMAGE:
            await query.message.reply_photo(
                photo=QR_CODE_IMAGE,
                caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.reply_text(
                text=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
        return


# =========================================================
# ⚙️ INDEXING FUNCTION
# =========================================================
async def index_files_to_db(lst_msg_id, chat_id, msg_obj, bot, skip, target_db):
    start_time = time.time()
    total_files = 0
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
                    await msg_obj.edit("🛑 Cancelled!")
                    return

                end_id = min(current + BATCH_SIZE, lst_msg_id + 1)
                ids = list(range(current, end_id))
                
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
                            current += 1
                            continue
                        
                        if not message.media:
                            no_media += 1
                            current += 1
                            continue
                        
                        if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                            current += 1
                            continue
                        
                        media = getattr(message, message.media.value, None)
                        if not media:
                            current += 1
                            continue
                        
                        file_id = media.file_id
                        file_unique_id = media.file_unique_id
                        
                        if target_db == "brazzers":
                            is_new = await db.add_brazzers_video(file_unique_id, file_id)
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

                scanned = min(current, lst_msg_id)
                percentage = (scanned / lst_msg_id) * 100
                prog_bar = get_progress_bar(percentage)
                elapsed = get_readable_time(time.time() - start_time)
                db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main"
                
                try:
                    await msg_obj.edit(
                        f"📊 **{db_label} Indexing**\n"
                        f"{prog_bar} {percentage:.1f}%\n"
                        f"━━━━━━━━━━━━\n"
                        f"📥 Scanned: {scanned}/{lst_msg_id}\n"
                        f"✅ Saved: {total_files}\n"
                        f"♻️ Dup: {duplicate}\n"
                        f"⏱ Time: {elapsed}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 CANCEL", callback_data="index_cancel")]])
                    )
                except:
                    pass

            elapsed = get_readable_time(time.time() - start_time)
            db_label = "🔞 Brazzers" if target_db == "brazzers" else "🎬 Main"
            await msg_obj.edit(f"✅ **{db_label} Completed!**\n⏱ {elapsed}\n✅ Saved: {total_files}\n♻️ Dup: {duplicate}")

        except Exception as e:
            await msg_obj.edit(f"❌ Error: {e}")
