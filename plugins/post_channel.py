from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import VIDEO_CHANNEL, BRAZZER_CHANNEL, NO_IMG, POST_CHANNEL, POST_SHORTLINK, SEND_POST, DEFAULT_THUMB  # ✅ Import DEFAULT_THUMB
from database.users_db import db
from utils import temp, get_shortlink, generate_weird_name

# -----------------------
# BRAZZERS INDEX
# -----------------------
@Client.on_message(filters.video & filters.chat(BRAZZER_CHANNEL))
async def index_brazzers_videos(_, m: Message):
    file_id = m.video.file_id
    file_unique_id = m.video.file_unique_id
    await db.add_brazzers_video(file_unique_id, file_id)

# -----------------------
# NORMAL VIDEO INDEX
# -----------------------
@Client.on_message(filters.video & filters.chat(VIDEO_CHANNEL))
async def index_normal_videos(client, m: Message):
    try:
        file_id = m.video.file_id
        file_unique_id = m.video.file_unique_id

        # Random name
        file_name = generate_weird_name() + ".mp4"

        # Save to DB
        status = await db.add_video(file_unique_id, file_id)

        if status:
            print(f"✅ New Video Added: {file_name}")
        else:
            print(f"♻️ Duplicate: {file_name}")

        if not SEND_POST:
            return

        # Bot username
        if not temp.U_NAME:
            me = await client.get_me()
            temp.U_NAME = me.username

        link = f"https://t.me/{temp.U_NAME}?start=avx-{file_unique_id}"

        # Shortlink
        if POST_SHORTLINK:
            try:
                shortlink = await get_shortlink(link)
            except Exception as e:
                print("Shortlink Error:", e)
                shortlink = link
        else:
            shortlink = link

        caption = (
            f"<b>{file_name}</b>\n\n"
            f"<i>Click the button below to watch the video.</i>"
        )

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Get Video 📂", url=shortlink)]
        ])

        # -----------------------
        # 🖼️ SAME THUMBNAIL FOR ALL VIDEOS (FIXED)
        # -----------------------
        thumb_to_send = DEFAULT_THUMB  # ✅ Directly use DEFAULT_THUMB

        # -----------------------
        # 📤 Send Video
        # -----------------------
        try:
            await client.send_video(
                chat_id=POST_CHANNEL,
                video=file_id,
                caption=caption,
                reply_markup=btn,
                thumb=thumb_to_send,  # 🔥 DEFAULT_THUMB will be applied here
                supports_streaming=True,
                width=m.video.width if m.video.width else 0,
                height=m.video.height if m.video.height else 0,
                duration=m.video.duration if m.video.duration else 0
            )
            print("✅ Video sent with DEFAULT_THUMB")

        except Exception as e:
            print(f"❌ Error sending video: {e}")
            # Fallback: send without thumbnail
            await client.send_video(
                chat_id=POST_CHANNEL,
                video=file_id,
                caption=caption,
                reply_markup=btn,
                supports_streaming=True
            )

    except Exception as e:
        print(f"❌ Error: {e}")
