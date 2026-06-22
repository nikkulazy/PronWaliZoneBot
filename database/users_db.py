import pytz
import random
import string
import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from info import DB_URL, DB_NAME, TIMEZONE, VERIFY_EXPIRE

# Logger Setup
logger = logging.getLogger(__name__)

# Database Connection
client = AsyncIOMotorClient(DB_URL)
mydb = client[DB_NAME]

# ⏰ IST Timezone Helper (Using pytz for accuracy)
def get_ist_now():
    return datetime.now(pytz.timezone(TIMEZONE))

def get_ist_today():
    return get_ist_now().date()

# -------------------- DATABASE CLASS --------------------
class Database:
    def __init__(self):
        self.users = mydb.users
        self.codes = mydb.codes
        self.misc = mydb.misc
        self.videos = mydb.videoz
        self.historys = mydb.historyz
        self.brazzers = mydb.brazzers
        self.verify_id = mydb.verify_id
        self.refer_collection = mydb.referrals
        self.braz_history = mydb.braz_history        
        self.blocked_users = mydb.blocked_users

    # ============================================================
    # USERS
    # ============================================================
    
    async def add_user(self, id, name):
        if not await self.users.find_one({"id": id}):
            await self.users.insert_one({
                "id": id,
                "name": name,
                "video_count": 0,
                "last_date": None,
                "expiry_time": None
            })

    async def is_user_exist(self, id):
        return bool(await self.users.find_one({'id': int(id)}))

    async def total_users_count(self):
        return await self.users.count_documents({})

    async def delete_user(self, user_id):
        await self.users.delete_many({'id': int(user_id)})

    async def get_user(self, user_id):
        return await self.users.find_one({"id": user_id})

    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def get_all_users(self):
        return self.users.find({})
    
    # ============================================================
    # COUNTS
    # ============================================================
        
    async def total_files_count(self):
        return await self.videos.count_documents({})

    async def total_brazzers_videos(self):
        return await self.brazzers.count_documents({})

    async def total_blocked_count(self):
        return await self.blocked_users.count_documents({})

    async def total_redeem_count(self):
        return await self.codes.count_documents({})
    
    # ============================================================
    # REFERRAL SYSTEM
    # ============================================================
    
    async def is_user_in_list(self, user_id):
        user = await self.refer_collection.find_one({"user_id": int(user_id)})
        return True if user else False

    async def get_refer_points(self, user_id: int):
        user = await self.refer_collection.find_one({"user_id": int(user_id)})
        return user.get("points", 0) if user else 0

    async def add_refer_points(self, user_id: int, points: int):
        await self.refer_collection.update_one(
            {"user_id": int(user_id)}, 
            {"$set": {"points": points}}, 
            upsert=True
        )

    async def change_points(self, user_id: int, amount: int):
        current_points = await self.get_refer_points(user_id)
        new_points = current_points + amount
        if new_points < 0:
            new_points = 0
            
        await self.refer_collection.update_one(
            {"user_id": int(user_id)}, 
            {"$set": {"points": new_points}}, 
            upsert=True
        )
        return new_points

    # ============================================================
    # MANUAL PAYMENT (ADD PREMIUM)
    # ============================================================
    
    async def add_premium_access(self, user_id, days):
        user = await self.get_user(user_id)
        now = datetime.now(timezone.utc)
        
        current_expiry = user.get("expiry_time")
        
        if current_expiry and isinstance(current_expiry, datetime):
            if current_expiry.tzinfo is None:
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)
            
            if current_expiry > now:
                new_expiry = current_expiry + timedelta(days=days)
            else:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)

        await self.users.update_one(
            {"id": user_id},
            {"$set": {"expiry_time": new_expiry}}
        )
        return new_expiry
    
    # ============================================================
    # BLOCK SYSTEM
    # ============================================================

    async def unblock_user(self, user_id: int):
        await self.blocked_users.delete_one({"user_id": user_id})

    async def get_all_blocked_users(self):
        return self.blocked_users.find({})

    async def is_user_blocked(self, user_id):
        user = await self.blocked_users.find_one({"user_id": user_id})
        return bool(user)

    async def block_user(self, user_id, reason="Spam"):
        await self.blocked_users.update_one(
            {"user_id": user_id},
            {"$set": {"blocked_at": datetime.now(timezone.utc), "reason": reason}},
            upsert=True
        )

    async def add_temp_ban(self, user_id, duration_seconds):
        expiry = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        await self.users.update_one(
            {"id": user_id},
            {"$set": {"temp_ban_expiry": expiry}}
        )

    async def is_temp_banned(self, user_id):
        user = await self.users.find_one({"id": user_id})
        if not user or "temp_ban_expiry" not in user:
            return False, 0
            
        expiry = user["temp_ban_expiry"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        if now < expiry:
            remaining = int((expiry - now).total_seconds())
            return True, remaining
        else:
            await self.users.update_one({"id": user_id}, {"$unset": {"temp_ban_expiry": ""}})
            return False, 0
    
    # ============================================================
    # PREMIUM / EXPIRY
    # ============================================================
            
    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if not user_data:
            return False

        expiry_time = user_data.get("expiry_time")
        if not expiry_time:
            return False

        now = datetime.now(timezone.utc)
        
        if isinstance(expiry_time, datetime):
            if expiry_time.tzinfo is None:
                expiry_time = expiry_time.replace(tzinfo=timezone.utc)
            return now <= expiry_time
        else:
            await self.users.update_one({"id": user_id}, {"$set": {"expiry_time": None}})
            return False

    async def update_one(self, filter_query, update_data):
        try:
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    async def get_expired(self, current_time):
        expired_users = []
        cursor = self.users.find({"expiry_time": {"$lt": current_time}})
        async for user in cursor:
            expired_users.append(user)
        return expired_users

    async def get_expiring_soon(self, label, delta):
        reminder_key = f"reminder_{label}_sent"
        now = datetime.now(timezone.utc)
        target_time = now + delta
        window = timedelta(seconds=30)
        start_range = target_time - window
        end_range = target_time + window
        reminder_users = []
        cursor = self.users.find({
            "expiry_time": {"$gte": start_range, "$lte": end_range},
            reminder_key: {"$ne": True}
        })
        async for user in cursor:
            reminder_users.append(user)
            await self.users.update_one(
                {"id": user["id"]}, {"$set": {reminder_key: True}}
            )
        return reminder_users

    async def remove_premium_access(self, user_id):
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def premium_users_count(self):
        return await self.users.count_documents({
            "expiry_time": {"$gt": datetime.now(timezone.utc)}
        })

    async def get_db_size(self):
        stats = await mydb.command("dbstats")
        return stats.get("dataSize", 0)

    # ============================================================
    # VIDEOS SYSTEM - MAIN
    # ============================================================
    
    async def add_video(self, file_unique_id, file_id):
        exists = await self.videos.find_one({"file_unique_id": file_unique_id})
        if not exists:
            short_id = await self.generate_short_id()
            while await self.videos.find_one({"short_id": short_id}):
                short_id = await self.generate_short_id()
            
            await self.videos.insert_one({
                "file_unique_id": file_unique_id,
                "file_id": file_id,
                "short_id": short_id,
                "added_at": datetime.now(timezone.utc)
            })
            return True
        return False

    async def total_videos(self):
        return await self.videos.count_documents({})

    async def delete_main_data(self):
        await self.videos.delete_many({})
        await self.historys.delete_many({})
        return True

    async def delete_brazzers_data(self):
        await self.brazzers.delete_many({})
        await self.braz_history.delete_many({})
        return True
    
    # ============================================================
    # VIDEO COUNT & LIMITS
    # ============================================================
        
    async def increase_video_count(self, user_id, username):
        today = get_ist_today()
        today_dt = datetime.combine(today, datetime.min.time())

        user = await self.users.find_one({"id": user_id})

        if user:
            last_date = user.get("last_date")
            
            if isinstance(last_date, datetime):
                if last_date.tzinfo is not None:
                    check_date = last_date.astimezone(pytz.timezone(TIMEZONE)).date()
                else:
                    check_date = last_date.date()
            else:
                check_date = None

            if check_date != today:
                await self.users.update_one(
                    {"id": user_id},
                    {"$set": {
                        "video_count": 1,
                        "last_date": today_dt,
                        "username": username
                    }}
                )
            else:
                await self.users.update_one(
                    {"id": user_id},
                    {"$inc": {"video_count": 1},
                     "$set": {"username": username}}
                )
        else:
            await self.users.insert_one({
                "id": user_id,
                "name": username,
                "video_count": 1,
                "last_date": today_dt,
                "expiry_time": None
            })
            
    async def get_video_count(self, user_id: int):
        today = get_ist_today()
        user = await self.users.find_one({"id": user_id})
        if user:
            last_date = user.get("last_date")
            if isinstance(last_date, datetime):
                if last_date.tzinfo is not None:
                    check_date = last_date.astimezone(pytz.timezone(TIMEZONE)).date()
                else:
                    check_date = last_date.date()
                    
                if check_date == today:
                    return user.get("video_count", 0)
        return 0
    
    # ============================================================
    # MAIN VIDEOS - GET & HISTORY
    # ============================================================
        
    async def get_unseen_video(self, user_id):
        try:
            history = await self.historys.find_one({"user_id": user_id})
            seen_ids = history.get("seen", []) if history else []
            
            all_videos = []
            cursor = self.videos.find({})
            async for video in cursor:
                if video["file_id"] not in seen_ids:
                    all_videos.append(video["file_id"])
            
            if not all_videos:
                cursor = self.videos.aggregate([{"$sample": {"size": 1}}])
                result = await cursor.to_list(length=1)
                if result:
                    video_id = result[0]["file_id"]
                    await self.mark_seen(user_id, video_id)
                    return video_id
                return None
            
            video_id = random.choice(all_videos)
            await self.mark_seen(user_id, video_id)
            return video_id
        except Exception as e:
            print(f"❌ Error in get_unseen_video: {e}")
            return None

    async def get_random_video(self):
        try:
            pipeline = [{"$sample": {"size": 1}}]
            cursor = self.videos.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            if result:
                return result[0]["file_id"]
        except Exception as e:
            print(f"Random video error: {e}")
        return None

    async def mark_seen(self, user_id, file_id):
        try:
            history = await self.historys.find_one({"user_id": user_id})
            if history:
                seen_list = history.get("seen", [])
                if file_id not in seen_list:
                    seen_list.append(file_id)
                    await self.historys.update_one(
                        {"user_id": user_id},
                        {"$set": {"seen": seen_list}}
                    )
            else:
                await self.historys.insert_one({
                    "user_id": user_id,
                    "seen": [file_id]
                })
        except Exception as e:
            print(f"❌ Error marking seen: {e}")

    async def reset_seen_videos(self, user_id: int):
        await self.historys.update_one(
            {"user_id": user_id},
            {"$set": {"seen": []}},
            upsert=True
        )
    
    # ============================================================
    # BRAZZERS VIDEOS - GET & HISTORY
    # ============================================================
        
    async def add_brazzers_video(self, file_unique_id, file_id):
        exists = await self.brazzers.find_one({"file_unique_id": file_unique_id})
        if not exists:
            short_id = await self.generate_short_id()
            while await self.brazzers.find_one({"short_id": short_id}):
                short_id = await self.generate_short_id()
            
            await self.brazzers.insert_one({
                "file_unique_id": file_unique_id,
                "file_id": file_id,
                "short_id": short_id
            })
            return True
        return False

    async def get_unseen_brazzers(self, user_id):
        try:
            history = await self.braz_history.find_one({"user_id": user_id})
            seen_ids = history.get("seen", []) if history else []
            
            all_videos = []
            cursor = self.brazzers.find({})
            async for video in cursor:
                if video["file_id"] not in seen_ids:
                    all_videos.append(video["file_id"])
            
            if not all_videos:
                return None
            
            video_id = random.choice(all_videos)
            await self.mark_brazzers_seen(user_id, video_id)
            return video_id
        except Exception as e:
            print(f"❌ Error in get_unseen_brazzers: {e}")
            return None

    async def mark_brazzers_seen(self, user_id, file_id):
        try:
            history = await self.braz_history.find_one({"user_id": user_id})
            if history:
                seen_list = history.get("seen", [])
                if file_id not in seen_list:
                    seen_list.append(file_id)
                    await self.braz_history.update_one(
                        {"user_id": user_id},
                        {"$set": {"seen": seen_list}}
                    )
            else:
                await self.braz_history.insert_one({
                    "user_id": user_id,
                    "seen": [file_id]
                })
        except Exception as e:
            print(f"❌ Error marking Brazzers seen: {e}")
        
    async def reset_seen_brazzers(self, user_id: int):
        await self.braz_history.update_one(
            {"user_id": user_id},
            {"$set": {"seen": []}},
            upsert=True
        )
    
    # ============================================================
    # SHORT ID SYSTEM - PROPER IMPLEMENTATION
    # ============================================================
    
    async def generate_short_id(self, length=6):
        """Generate unique short ID"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    
    async def get_short_id(self, file_id):
        """Get short ID for a video"""
        video = await self.videos.find_one({"file_id": file_id})
        if video and "short_id" in video:
            return video["short_id"]
        # If no short_id exists, generate one
        short_id = await self.generate_short_id()
        while await self.videos.find_one({"short_id": short_id}):
            short_id = await self.generate_short_id()
        await self.videos.update_one(
            {"file_id": file_id},
            {"$set": {"short_id": short_id}}
        )
        return short_id
    
    async def get_video_by_short_id(self, short_id):
        """Get full video ID from short ID"""
        video = await self.videos.find_one({"short_id": short_id})
        return video["file_id"] if video else None
    
    async def get_brazzers_short_id(self, file_id):
        """Get short ID for a Brazzers video"""
        video = await self.brazzers.find_one({"file_id": file_id})
        if video and "short_id" in video:
            return video["short_id"]
        short_id = await self.generate_short_id()
        while await self.brazzers.find_one({"short_id": short_id}):
            short_id = await self.generate_short_id()
        await self.brazzers.update_one(
            {"file_id": file_id},
            {"$set": {"short_id": short_id}}
        )
        return short_id
    
    async def get_brazzers_by_short_id(self, short_id):
        """Get full Brazzers video ID from short ID"""
        video = await self.brazzers.find_one({"short_id": short_id})
        return video["file_id"] if video else None

    # ============================================================
    # PREVIOUS NAVIGATION - MAIN VIDEOS
    # ============================================================
    
    async def get_previous_video(self, user_id, current_video_id):
        try:
            history = await self.historys.find_one({"user_id": user_id})
            if not history:
                return None
            
            seen_list = history.get("seen", [])
            if len(seen_list) < 2:
                return None
            
            try:
                current_index = seen_list.index(current_video_id)
            except ValueError:
                return None
            
            if current_index > 0:
                return seen_list[current_index - 1]
            return None
        except Exception as e:
            print(f"❌ Error getting previous video: {e}")
            return None

    async def has_previous_video(self, user_id, current_video_id):
        try:
            history = await self.historys.find_one({"user_id": user_id})
            if not history:
                return False
            
            seen_list = history.get("seen", [])
            if len(seen_list) < 2:
                return False
            
            try:
                current_index = seen_list.index(current_video_id)
                return current_index > 0
            except ValueError:
                return False
        except Exception as e:
            print(f"Error checking previous video: {e}")
            return False
    
    # ============================================================
    # PREVIOUS NAVIGATION - BRAZZERS
    # ============================================================

    async def get_previous_brazzers(self, user_id, current_video_id):
        try:
            history = await self.braz_history.find_one({"user_id": user_id})
            if not history:
                return None
            
            seen_list = history.get("seen", [])
            if len(seen_list) < 2:
                return None
            
            try:
                current_index = seen_list.index(current_video_id)
            except ValueError:
                return None
            
            if current_index > 0:
                return seen_list[current_index - 1]
            return None
        except Exception as e:
            print(f"❌ Error getting previous Brazzers: {e}")
            return None

    async def has_previous_brazzers(self, user_id, current_video_id):
        try:
            history = await self.braz_history.find_one({"user_id": user_id})
            if not history:
                return False
            
            seen_list = history.get("seen", [])
            if len(seen_list) < 2:
                return False
            
            try:
                current_index = seen_list.index(current_video_id)
                return current_index > 0
            except ValueError:
                return False
        except Exception as e:
            print(f"Error checking previous Brazzers: {e}")
            return False
            
    # ============================================================
    # VERIFICATION SYSTEM
    # ============================================================
            
    async def get_notcopy_user(self, user_id):
        user_id = int(user_id)
        user = await self.misc.find_one({"user_id": user_id})
        
        default_date = datetime(2020, 5, 17, 0, 0, 0, tzinfo=timezone.utc)

        if not user:
            res = {
                "user_id": user_id,
                "last_verified": default_date,
            }
            await self.misc.insert_one(res)
            return res
        return user

    async def update_notcopy_user(self, user_id, value: dict):
        user_id = int(user_id)
        myquery = {"user_id": user_id}
        newvalues = {"$set": value}
        return await self.misc.update_one(myquery, newvalues)

    async def is_user_verified(self, user_id):
        user = await self.get_notcopy_user(user_id)
        
        pastDate = user.get("last_verified")
        
        if not pastDate:
             pastDate = datetime(2020, 5, 17, 0, 0, 0, tzinfo=timezone.utc)

        if pastDate.tzinfo is None:
             pastDate = pastDate.replace(tzinfo=timezone.utc)
        
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - pastDate
        
        if time_diff < timedelta(seconds=VERIFY_EXPIRE):
            return True
            
        return False

    async def create_verify_id(self, user_id: int, hash, file_id=None):
        res = {"user_id": user_id, "hash": hash, "verified": False, "file_id": file_id}
        return await self.verify_id.insert_one(res)

    async def get_verify_id_info(self, user_id: int, hash):
        return await self.verify_id.find_one({"user_id": user_id, "hash": hash})

    async def update_verify_id_info(self, user_id, hash, value: dict):
        myquery = {"user_id": user_id, "hash": hash}
        newvalues = {"$set": value}
        return await self.verify_id.update_one(myquery, newvalues)

    async def get_verification_stats(self):
        midnight_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        level1_count = await self.misc.count_documents({
            "last_verified": {"$gte": midnight_utc}
        })
        return level1_count

# Initialize
db = Database()
