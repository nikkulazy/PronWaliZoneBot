# bot.py - Updated with Fast Client

import os
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT, ADMINS
from aiohttp import web
from route import web_server, ping_server, check_expired_premium, start_scheduler, set_bot_client
import pytz
from datetime import date, datetime
from utils import temp 

# ✅ Import fast client
from fast_client import pre_start, get_client_count

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="avbotz",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=15,
            max_concurrent_transmissions=3,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        temp.B_LINK = me.mention
        self.username = '@' + me.username

        # ✅ PRE-START FAST CLIENT
        await pre_start()
        print(f"✅ Fast Client Pre-Started! ({get_client_count()} client)")

        # ✅ Set bot client
        set_bot_client(self)

        # ----------------- PLUGINS LOADING -----------------
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

        print(f"\n✅ {me.first_name} STARTED ⚡️⚡️⚡️")
        print(f"🔥 Client: {get_client_count()} Ready!")
        print(f"🛡️ Flood Protection: ✅ Active\n")
  
        # ✅ ADMINS MESSAGE
        if isinstance(ADMINS, list):
            for admin in ADMINS:
                try:
                    await self.send_message(admin, f"**__{me.first_name} Is Started.....✨️😅😅😅__**")
                except:
                    pass
        else:
            try:
                await self.send_message(ADMINS, f"**__{me.first_name} Is Started.....✨️😅😅😅__**")
            except:
                pass
        
        # ✅ LOG CHANNEL MESSAGE
        try:
            await self.send_message(
                LOG_CHANNEL,
                text=(
                    f"<b>Restarted 🤖\n\n"
                    f"📆 Date - <code>{today}</code>\n"
                    f"🕙 Time - <code>{time}</code>\n"
                    f"🔥 Client: ✅ {get_client_count()} Ready\n"
                    f"🛡️ Flood Protection: ✅ Active</b>"
                )
            )
        except:
            pass

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped")

if __name__ == "__main__":
    Bot().run()
