import re
from os import environ
import random  # ← Add this

# -------------------------
# Helper
# -------------------------
def str_to_bool(val, default=False):
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")

# =========================================================
# 🤖 BOT BASIC INFORMATION
# =========================================================
API_ID = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")
PORT = int(environ.get("PORT", "8080"))
TIMEZONE = environ.get("TIMEZONE", "Asia/Kolkata")
OWNER_USERNAME = environ.get("OWNER_USERNAME", "WOLVERIN_P")

# =========================================================
# 💾 DATABASE CONFIGURATION
# =========================================================
DB_URL = environ.get("DATABASE_URI", "mongodb+srv://mastitime:mastitime@cluster0.tohbael.mongodb.net/?appName=Cluster0")
DB_NAME = environ.get("DATABASE_NAME", "testing")

# =========================================================
# 📢 CHANNELS & ADMINS
# =========================================================
ADMINS = [int(x) for x in environ.get("ADMINS", "0").split() if x.strip().isdigit()]

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1002016227618"))
PREMIUM_LOGS = int(environ.get("PREMIUM_LOGS", "-1002016227618"))
VERIFIED_LOG = int(environ.get("VERIFIED_LOG", "-1002016227618"))

POST_CHANNEL = int(environ.get("POST_CHANNEL", "-1001866287032"))
VIDEO_CHANNEL = int(environ.get("VIDEO_CHANNEL", "-1001866287032"))
BRAZZER_CHANNEL = int(environ.get("BRAZZER_CHANNEL", "-1001866287032"))

# Auth channels list
auth_channel_str = environ.get("AUTH_CHANNEL", "-1002072782451")
AUTH_CHANNEL = [int(x) for x in auth_channel_str.split() if x.strip().lstrip("-").isdigit()]

# =========================================================
# ⚙️ FEATURES & TOGGLES
# =========================================================
FSUB = str_to_bool(environ.get("FSUB"), True)
IS_VERIFY = str_to_bool(environ.get("IS_VERIFY"), True)
POST_SHORTLINK = str_to_bool(environ.get("POST_SHORTLINK"), False)
SEND_POST = str_to_bool(environ.get("SEND_POST"), False)
PROTECT_CONTENT = str_to_bool(environ.get("PROTECT_CONTENT"), True)

# =========================================================
# 🔢 LIMITS
# =========================================================
DAILY_LIMIT = int(environ.get("DAILY_LIMIT", "5"))
VERIFICATION_DAILY_LIMIT = int(environ.get("VERIFICATION_DAILY_LIMIT", "20"))
PREMIUM_DAILY_LIMIT = int(environ.get("PREMIUM_DAILY_LIMIT", "50"))
FREE_VIDEO_DURATION = int(environ.get("FREE_VIDEO_DURATION", "60"))
FREE_VIDEO_DURATION = 60

# =========================================================
# 🔗 SHORTLINK & VERIFICATION
# =========================================================
SHORTLINK_URL = environ.get("SHORTLINK_URL", "https://omegalinks.in")
SHORTLINK_API = environ.get("SHORTLINK_API", "a7ac9b3012c67d7491414cf272d82593c75f6cbb")
POST_SHORTLINK_URL = environ.get("POST_SHORTLINK_URL", "https://omegalinks.in")
POST_SHORTLINK_API = environ.get("POST_SHORTLINK_API", "a7ac9b3012c67d7491414cf272d82593c75f6cbb")
VERIFY_EXPIRE = int(environ.get("VERIFY_EXPIRE", "3600"))
TUTORIAL_LINK = environ.get("TUTORIAL_LINK", "")
# ✅ Debug print
print(f"🔗 SHORTLINK_URL: {SHORTLINK_URL}")
print(f"🔑 SHORTLINK_API: {SHORTLINK_API[:10] if SHORTLINK_API else 'NOT SET'}")
# =========================================================
# 💳 PAYMENT SETTINGS
# =========================================================
UPI_ID = environ.get("UPI_ID", "Not Found")
QR_CODE_IMAGE = environ.get("QR_CODE_IMAGE", "https://i.ibb.co/kWtBcgx/photo-2025-08-04-09-11-58-7534655638404595732.jpg")

# =========================================================
# 🖼️ IMAGES
# =========================================================
START_PIC = environ.get("START_PIC", "https://i.ibb.co/Xn2b08M/photo-2026-06-28-12-30-38-7656422767314599952.jpg")
AUTH_PICS = environ.get("AUTH_PICS", "http://ibb.co/zCGSdbR")
VERIFY_IMG = environ.get("VERIFY_IMG", "http://ibb.co/zCGSdbR")
NO_IMG = environ.get("NO_IMG", "http://ibb.co/zCGSdbR")

# 🎯 RANDOM PICS LIST (Multiple images for random display)
PICS = [
    START_PIC,  # Default start pic
    "https://i.ibb.co/HfkPW3Xc/photo-2026-06-28-12-25-46-7656421521774084124.jpg",
    "https://i.ibb.co/SDVNR24F/photo-2026-06-28-12-26-58-7656421826716762128.jpg",
    "https://i.ibb.co/hRXPR4bh/photo-2026-06-28-12-27-56-7656422084414799876.jpg",
    "https://i.ibb.co/KpthX4Kh/photo-2026-06-28-12-32-53-7656423377199955984.jpg",
    "https://i.ibb.co/Xn2b08M/photo-2026-06-28-12-30-38-7656422767314599952.jpg",
    "https://i.ibb.co/v6jJqLCR/photo-2026-06-28-12-31-19-7656422951998193672.jpg",
]

# =========================================================
# 🌐 WEB APP
# =========================================================
WEB_APP_URL = environ.get("WEB_APP_URL", "https://protestant-lulu-misslazy-c67202fa.koyeb.app/")
