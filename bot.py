# bot.py mein start function mein yeh add karo

import os
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT, ADMINS
from aiohttp import web
from route import web_server, ping_server, check_expired_premium, start_scheduler, set_bot_client
import pytz
from datetime import date, datetime
from utils import temp 
from get_video import start_cache_cleanup
await start_cache_cleanup()

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="avbotz",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=15,
            max_concurrent_transmissions=5,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        temp.B_LINK = me.mention
        self.username = '@' + me.username

        # ✅ Bot client set for route.py
        set_bot_client(self)

        # ✅ PRE-START DOWNLOAD CLIENT - ⚡ FAST (IMPORTANT)
        from download_client import init_download_client
        await init_download_client()  # ✅ Bot start pe hi client ready

        # ----------------- PLUGINS PRINTING LOGIC -----------------
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🛠  LOADING PLUGINS...")
        
        plugin_count = 0
        for root, dirs, files in os.walk("plugins"):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    print(f"✅ Successfully Loaded: {file}")
                    plugin_count += 1
        
        print(f"🎉 Total {plugin_count} Plugins Loaded!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        # ----------------------------------------------------------

        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        
        # --- BACKGROUND TASKS ---
        self.loop.create_task(check_expired_premium(self))
        self.loop.create_task(start_scheduler(self))
        self.loop.create_task(ping_server()) 
        
        app_instance = await web_server()
        app_runner = web.AppRunner(app_instance)
        await app_runner.setup()
        site = web.TCPSite(app_runner, "0.0.0.0", int(PORT))
        await site.start()

        print(f"{me.first_name} 𝚂𝚃𝙰𝚁𝚃𝙴𝙳 ⚡️⚡️⚡️")
  
        # ✅ ADMINS MESSAGE
        if isinstance(ADMINS, list):
            for admin in ADMINS:
                try:
                    await self.send_message(admin, f"**__{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️😅😅😅__**")
                except:
                    pass
        else:
            try:
                await self.send_message(ADMINS, f"**__{me.first_name} Iꜱ Sᴛᴀʀᴛᴇᴅ.....✨️😅😅😅__**")
            except:
                pass
        
        # ✅ LOG CHANNEL MESSAGE
        try:
            await self.send_message(
                LOG_CHANNEL,
                text=(
                    f"<b>ʀᴇsᴛᴀʀᴛᴇᴅ 🤖\n\n"
                    f"📆 ᴅᴀᴛᴇ - <code>{today}</code>\n"
                    f"🕙 ᴛɪᴍᴇ - <code>{time}</code>\n"
                    f"🌍 ᴛɪᴍᴇ ᴢᴏɴᴇ - <code>Asia/Kolkata</code></b>"
                )
            )
        except:
            pass

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped")

if __name__ == "__main__":
    Bot().run()
