import os
import sys
import logging
import asyncio
from pyrogram import Client
from info import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT, ADMINS, URL, WEB_APP_URL
from aiohttp import web
from route import web_server, ping_server, check_expired_premium, start_scheduler, set_bot_client
import pytz
from datetime import date, datetime
from utils import temp 
from download_client import init_download_client, clear_cache, get_cache_size

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# BOT CLASS
# ============================================================
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
        self.start_time = None
        self.web_app = None
        self.web_runner = None

    # ============================================================
    # START METHOD - ✅ COMPLETE
    # ============================================================
    async def start(self):
        """Start the bot and all services"""
        try:
            # ✅ Start pyrogram client
            await super().start()
            self.start_time = datetime.now()
            
            # ✅ Get bot info
            me = await self.get_me()
            temp.ME = me.id
            temp.U_NAME = me.username
            temp.B_NAME = me.first_name
            temp.B_LINK = me.mention
            self.username = '@' + me.username

            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"🤖 Bot: {me.first_name} (@{me.username})")
            logger.info(f"🆔 Bot ID: {me.id}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # ✅ Set bot client for route.py
            set_bot_client(self)

            # ----------------- PLUGINS LOADING -----------------
            logger.info("🛠  LOADING PLUGINS...")
            
            plugin_count = 0
            if os.path.exists("plugins"):
                for root, dirs, files in os.walk("plugins"):
                    for file in files:
                        if file.endswith(".py") and not file.startswith("__"):
                            logger.info(f"✅ Loaded: {file}")
                            plugin_count += 1
            else:
                logger.warning("⚠️ Plugins folder not found!")
            
            logger.info(f"🎉 Total {plugin_count} Plugins Loaded!")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            # --------------------------------------------------

            # ============================================================
            # 🚀 PRE-START DOWNLOAD CLIENT - FAST DOWNLOAD के लिए
            # ============================================================
            logger.info("⚡ Pre-starting download client for fast downloads...")
            try:
                download_client = await init_download_client()
                if download_client:
                    logger.info("✅ Download client pre-started successfully!")
                    logger.info("⚡ Downloads will start in 1-2 seconds!")
                else:
                    logger.warning("⚠️ Download client pre-start failed, will start on demand")
            except Exception as e:
                logger.error(f"❌ Error pre-starting download client: {e}")
            
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # ============================================================
            # 🌐 START WEB SERVER
            # ============================================================
            try:
                logger.info(f"🌐 Starting web server on port {PORT}...")
                app_instance = await web_server()
                self.web_runner = web.AppRunner(app_instance)
                await self.web_runner.setup()
                site = web.TCPSite(self.web_runner, "0.0.0.0", int(PORT))
                await site.start()
                logger.info(f"✅ Web server started on port {PORT}")
                logger.info(f"🌐 Web URL: {WEB_APP_URL or URL}")
            except Exception as e:
                logger.error(f"❌ Failed to start web server: {e}")

            # ============================================================
            # 🔄 BACKGROUND TASKS
            # ============================================================
            logger.info("🔄 Starting background tasks...")
            
            # ✅ Premium expiry checker
            self.loop.create_task(check_expired_premium(self))
            logger.info("✅ Premium expiry checker started")
            
            # ✅ Scheduler
            self.loop.create_task(start_scheduler(self))
            logger.info("✅ Scheduler started")
            
            # ✅ Keep alive ping
            self.loop.create_task(ping_server())
            logger.info("✅ Keep alive ping started")
            
            # ✅ Cache cleaner (every 30 minutes)
            self.loop.create_task(self.clean_cache_periodically())
            logger.info("✅ Cache cleaner started")

            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"✅ {me.first_name} STARTED SUCCESSFULLY! ⚡")
            logger.info(f"📅 Date: {date.today()}")
            logger.info(f"⏰ Time: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S %p')}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # ============================================================
            # 📨 SEND START NOTIFICATIONS
            # ============================================================
            tz = pytz.timezone('Asia/Kolkata')
            today = date.today()
            now = datetime.now(tz)
            time_str = now.strftime("%H:%M:%S %p")
            
            # ✅ Send to LOG_CHANNEL
            try:
                await self.send_message(
                    LOG_CHANNEL,
                    text=(
                        f"<b>✅ Bot Restarted Successfully!</b>\n\n"
                        f"🤖 <b>Bot:</b> {me.mention}\n"
                        f"🆔 <b>ID:</b> <code>{me.id}</code>\n"
                        f"📆 <b>Date:</b> <code>{today}</code>\n"
                        f"⏰ <b>Time:</b> <code>{time_str}</code>\n"
                        f"🌍 <b>Timezone:</b> <code>Asia/Kolkata</code>\n"
                        f"🌐 <b>Web URL:</b> <code>{WEB_APP_URL or URL}</code>\n"
                        f"⚡ <b>Download Speed:</b> <code>1-2 seconds</code>"
                    )
                )
                logger.info("✅ Log channel notification sent")
            except Exception as e:
                logger.error(f"❌ Failed to send log channel message: {e}")
            
            # ✅ Send to ADMINS
            admin_list = ADMINS if isinstance(ADMINS, list) else [ADMINS]
            for admin_id in admin_list:
                try:
                    await self.send_message(
                        admin_id,
                        f"<b>✅ {me.first_name} Started Successfully!</b>\n\n"
                        f"⚡ <b>Download Speed:</b> 1-2 seconds\n"
                        f"🌐 <b>Web URL:</b> <code>{WEB_APP_URL or URL}</code>"
                    )
                    logger.info(f"✅ Admin notification sent to {admin_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send admin message to {admin_id}: {e}")

        except Exception as e:
            logger.error(f"❌ Error in start method: {e}")
            import traceback
            traceback.print_exc()
            raise

    # ============================================================
    # PERIODIC CACHE CLEANER - 🧹
    # ============================================================
    async def clean_cache_periodically(self):
        """Clean download cache every 30 minutes"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                cache_size = get_cache_size()
                if cache_size > 0:
                    clear_cache()
                    logger.info(f"🧹 Cache cleaned! {cache_size} files removed")
            except Exception as e:
                logger.error(f"❌ Cache clean error: {e}")

    # ============================================================
    # STOP METHOD
    # ============================================================
    async def stop(self, *args):
        """Stop the bot and cleanup"""
        try:
            logger.info("🛑 Stopping bot...")
            
            # ✅ Stop web server
            if self.web_runner:
                try:
                    await self.web_runner.cleanup()
                    logger.info("✅ Web server stopped")
                except Exception as e:
                    logger.error(f"❌ Web server stop error: {e}")
            
            # ✅ Clear cache
            clear_cache()
            logger.info("✅ Cache cleared")
            
            # ✅ Stop pyrogram client
            await super().stop()
            logger.info("✅ Bot stopped successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error in stop method: {e}")

    # ============================================================
    # RUN METHOD - WITH AUTO RESTART
    # ============================================================
    async def run_with_auto_restart(self):
        """Run bot with auto restart on crash"""
        while True:
            try:
                await self.start()
                logger.info("🤖 Bot is running... Press Ctrl+C to stop")
                
                # ✅ Keep running until stopped
                while True:
                    await asyncio.sleep(60)
                    # ✅ Health check
                    if not self.is_connected:
                        logger.warning("⚠️ Bot disconnected! Restarting...")
                        break
                        
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Bot crashed: {e}")
                logger.info("🔄 Restarting in 5 seconds...")
                await asyncio.sleep(5)
            finally:
                try:
                    await self.stop()
                except:
                    pass

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    try:
        bot = Bot()
        
        # ✅ Check if running on supported platform
        logger.info("🚀 Starting PronWaliZoneBot...")
        logger.info(f"📡 PORT: {PORT}")
        logger.info(f"🌐 WEB_APP_URL: {WEB_APP_URL or URL}")
        
        # ✅ Run bot
        asyncio.run(bot.run_with_auto_restart())
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
