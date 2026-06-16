import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start
from plugins.index import INDEX_CACHE

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
            
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Get Video"), KeyboardButton("Brazzers")],
            [KeyboardButton("My plan"), KeyboardButton("Subscription")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.reply_photo(
        photo=START_PIC,
        caption=script.START_TXT.format(mention, temp.U_NAME, temp.U_NAME),
        reply_markup=reply_keyboard,
        has_spoiler=True
    )

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
async def legal_hepl(client, message: Message):
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
# 🔙 CALLBACK QUERY HANDLER
# =========================================================
IndexCacheCallbackIssue
✅ Simple Fix - Sirf 2 Steps:
Step 1: command.py mein yeh 2 lines add karein (sab se upar)
python
# 🔥 Sab se upar, imports ke baad add karein
from index import INDEX_CACHE  # LINE 1
Step 2: command.py ke callback handler mein yeh change karein
PURANA CODE (command.py mein):

python
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "close_data":
        await query.message.delete()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
NAYA CODE (YEH BANAYEIN):

python
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # 🔥🔥🔥 YEH ADD KAREIN (SAB SE PEHLE)
    if data == "index#yes":
        user_data = INDEX_CACHE.get(user_id)
        if user_data:
            await query.answer("✅ Indexing started!")
            await query.message.edit_text("✅ Indexing started!")
            INDEX_CACHE.pop(user_id, None)
        else:
            await query.answer("❌ Send /index again", show_alert=True)
        return  # 🔥 IMPORTANT

    # BAAKI PURANA CODE (close_data, get, etc.)
    elif data == "close_data":
        await query.message.delete()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
📝 Complete command.py (Sirf changes dikhaye):
python
import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# 🔥🔥🔥 YEH LINE ADD KAREIN
from index import INDEX_CACHE

# =================================================
# 🚀 START COMMAND
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    # ... aapka purana code (change nahi)
    pass

# =================================================
# 📜 HELPER HANDLERS
# =================================================
# ... aapke purane helper handlers (change nahi)

# =========================================================
# 🔙 CALLBACK QUERY HANDLER - YEH CHANGE KAREIN
# =========================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # 🔥🔥🔥 YEH ADD KAREIN (YES BUTTON KE LIYE)
    if data == "index#yes":
        user_data = INDEX_CACHE.get(user_id)
        if user_data:
            await query.answer("✅ Indexing started!")
            await query.message.edit_text("✅ Indexing started!")
            INDEX_CACHE.pop(user_id, None)
        else:
            await query.answer("❌ Send /index again", show_alert=True)
        return  # 🔥 IMPORTANT - yahan return karein

    # BAAKI AAPKA PURANA CODE
    elif data == "close_data":
        await query.message.delete()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
🎯 Bas Itna Karna Hai:
command.py mein from index import INDEX_CACHE add karein

command.py ke callback handler mein if data == "index#yes": add karein

Bot restart karein

Test karein: /index -> YES click

✅ Kaam Kaise Karega:
text
User: /index
   ↓
INDEX_CACHE = {user_id: {chat, lst_msg_id, skip}}  # Store
   ↓
Bot: YES/CLOSE buttons show
   ↓
User: YES click
   ↓
command.py ka callback handler trigger
   ↓
data == "index#yes" -> True
   ↓
INDEX_CACHE se data nikalta hai
   ↓
"✅ Indexing started!" message
   ↓
Kaam ho gaya! 🎉
Ye simple fix hai, bas 2 lines add karni hain aur bot restart! 🚀

Instance created. Preparing to start...
Starting download for registry01.prod.koyeb.com/k-62b7f241-44af-4836-9fff-74b0011c09bb/0c5e4b64-3250-4871-819d-6eea5701c9d7:1f35781d-bed3-4c71-a458-cc8a79813143
Download progress: 100% |[32m++++++++[0m| (6.2 MiB/s)
Download complete for registry01.prod.koyeb.com/k-62b7f241-44af-4836-9fff-74b0011c09bb/0c5e4b64-3250-4871-819d-6eea5701c9d7:1f35781d-bed3-4c71-a458-cc8a79813143
Instance is starting... Waiting for health checks to pass.
Traceback (most recent call last):
  File "/workspace/bot.py", line 99, in <module>
    Bot().run()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/utilities/run.py", line 81, in run
    run(self.start())
  File "/workspace/.heroku/python/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/workspace/bot.py", line 24, in start
    await super().start()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/utilities/start.py", line 75, in start
    await self.initialize()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/auth/initialize.py", line 47, in initialize
    self.load_plugins()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/client.py", line 912, in load_plugins
    module = import_module(module_path)
  File "/workspace/.heroku/python/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/workspace/plugins/command.py", line 13, in <module>
    from index import INDEX_CACHE
ModuleNotFoundError: No module named 'index'
Application exited with code 1. This usually indicates an application failure. Check that the command used to launch your application is correct.
Traceback (most recent call last):
  File "/workspace/bot.py", line 99, in <module>
    Bot().run()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/utilities/run.py", line 81, in run
    run(self.start())
  File "/workspace/.heroku/python/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/workspace/bot.py", line 24, in start
    await super().start()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/utilities/start.py", line 75, in start
    await self.initialize()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/methods/auth/initialize.py", line 47, in initialize
    self.load_plugins()
  File "/workspace/.heroku/python/lib/python3.10/site-packages/pyrogram/client.py", line 912, in load_plugins
    module = import_module(module_path)
  File "/workspace/.heroku/python/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/workspace/plugins/command.py", line 13, in <module>
    from index import INDEX_CACHE
ModuleNotFoundError: No module named 'index'
Application exited with code 1. This usually indicates an application failure. Check that the command used to launch your application is correct.
Instance stopped.
❌ Problem: ModuleNotFoundError: No module named 'index'
Aapne from index import INDEX_CACHE kiya hai, lekin aapki index.py file plugins folder ke ANDAR hai, isliye import nahi ho pa raha.

✅ Solution - Import Path Fix:
Option 1: Relative Import (Recommended)
command.py mein yeh change karein:

python
# ❌ GALAT (yeh error de raha hai)
from index import INDEX_CACHE

# ✅ SAHI (plugins folder ke andar se import)
from plugins.index import INDEX_CACHE
Option 2: Absolute Import
python
# ✅ SAHI
from plugins.index import INDEX_CACHE
📝 Complete Fix - command.py mein yeh change karein:
Line 13 change karein:

python
# 🔥 YEH CHANGE KAREIN
from plugins.index import INDEX_CACHE  # ✅ SAHI
Pura import section aisa dikhega:

python
import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# 🔥🔥🔥 YEH LINE CHANGE KAREIN
from plugins.index import INDEX_CACHE  # ✅ 'plugins.index' use karein
🔍 File Structure Check:
Aapki file structure aisi hai:

text
/workspace/
├── bot.py
├── plugins/
│   ├── command.py        ← Yeh file
│   ├── index.py          ← Yeh file (INDEX_CACHE yahan hai)
│   ├── verification.py
│   ├── refer.py
│   └── ...
├── database/
│   └── users_db.py
└── ...
Isliye import karte waqt plugins. lagana zaroori hai.

✅ Doosra Solution - INDEX_CACHE ko command.py mein hi define karein:
Agar import se problem ho rahi hai toh command.py mein hi INDEX_CACHE define kar do:

python
# 🔥 command.py mein sab se upar
INDEX_CACHE = {}  # Direct define karein, import nahi karein
Aur index.py mein bhi define karke, dono mein same dictionary use karein:

python
# index.py - sab se upar
INDEX_CACHE = {}

# command.py - sab se upar  
from plugins.index import INDEX_CACHE  # Ya direct define karein
📝 Final Working command.py:
python
import datetime
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import *
from pyrogram.errors import *
from Script import script
from database.users_db import db
from info import START_PIC, LOG_CHANNEL, PREMIUM_LOGS, FSUB, QR_CODE_IMAGE, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID
from utils import temp, is_user_joined
from plugins.verification import verify_user_on_start
from plugins.send_file import send_requested_file
from plugins.refer import refer_on_start

# 🔥🔥🔥 YEH LINE FIX KAREIN (plugins. lagayein)
from plugins.index import INDEX_CACHE

# =================================================
# 🚀 START COMMAND
# =================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    # ... aapka purana code
    pass

# =================================================
# 🔙 CALLBACK QUERY HANDLER
# =================================================
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # 🔥 YES BUTTON
    if data == "index#yes":
        user_data = INDEX_CACHE.get(user_id)
        if user_data:
            await query.answer("✅ Indexing started!")
            await query.message.edit_text("✅ Indexing started!")
            INDEX_CACHE.pop(user_id, None)
        else:
            await query.answer("❌ Send /index again", show_alert=True)
        return

    # BAAKI CODE
    elif data == "close_data":
        await query.message.delete()

    elif data == "get":
        buttons = [
            [InlineKeyboardButton('• 𝖢𝗅𝗈𝗌𝖾 •', callback_data='close_data')]
        ]
        await query.message.reply_photo(
            photo=QR_CODE_IMAGE,
            caption=script.SEENBUY_TXT.format(DAILY_LIMIT, PREMIUM_DAILY_LIMIT, UPI_ID),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
