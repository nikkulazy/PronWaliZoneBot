import asyncio
import pytz
import random
import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from info import DB_URL, DB_NAME, TIMEZONE, VERIFY_EXPIRE, FREE_VIDEO_DURATION

logger = logging.getLogger(__name__)

print("🔄 Initializing MongoDB connection...")

# Global variables
_client = None
_mydb = None
_connection_attempts = 0
_MAX_RETRIES = 10

async def connect_mongodb():
    """Connect to MongoDB with retry logic"""
    global _client, _mydb, _connection_attempts
    
    _connection_attempts += 1
    print(f"🔄 MongoDB connection attempt {_connection_attempts}...")
    
    try:
        _client = AsyncIOMotorClient(
            DB_URL,
            serverSelectionTimeoutMS=60000,
            connectTimeoutMS=60000,
            socketTimeoutMS=60000,
            maxPoolSize=50,
            minPoolSize=10,
            retryWrites=True,
            retryReads=True,
            maxIdleTimeMS=60000
        )
        
        # Test connection
        await _client.admin.command('ping')
        _mydb = _client[DB_NAME]
        print("✅ MongoDB Connected Successfully!")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        _client = None
        _mydb = None
        return False

async def ensure_connection():
    """Ensure MongoDB connection is alive, reconnect if needed"""
    global _client, _mydb
    
    try:
        if _client is not None and _mydb is not None:
            await _client.admin.command('ping')
            return True
    except:
        pass
    
    # Connection lost or not initialized, reconnect
    print("⚠️ MongoDB connection lost, reconnecting...")
    return await connect_mongodb()

# Initial connection (synchronous wrapper)
def init_connection():
    """Synchronous wrapper for initial connection"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(connect_mongodb())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Initial connection failed: {e}")
        return False

# Initialize
init_connection()

def get_ist_now():
    return datetime.now(pytz.timezone(TIMEZONE))

def get_ist_today():
    return get_ist_now().date()

# -------------------- DATABASE CLASS --------------------
class Database:
    def __init__(self):
        self._db = _mydb
        if self._db:
            self.users = self._db.users
            self.codes = self._db.codes
            self.misc = self._db.misc
            self.videos = self._db.videoz
            self.historys = self._db.historyz
            self.brazzers = self._db.brazzers
            self.verify_id = self._db.verify_id
            self.refer_collection = self._db.referrals
            self.braz_history = self._db.braz_history        
            self.blocked_users = self._db.blocked_users
        else:
            print("⚠️ Database not connected, will retry on first request")

    async def _execute(self, operation, *args, **kwargs):
        """Execute DB operation with auto-reconnect"""
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                # Ensure connection
                if not await ensure_connection():
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    else:
                        raise Exception("MongoDB connection unavailable")
                
                # Execute operation
                return await operation(*args, **kwargs)
                
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                print(f"⚠️ DB operation failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3 * (attempt + 1))
                    # Force reconnection
                    global _client, _mydb
                    _client = None
                    _mydb = None
                else:
                    raise
            except Exception as e:
                print(f"❌ DB operation error: {e}")
                raise
        
        return None

    # ---------- USERS ----------
    async def add_user(self, id, name):
        async def _op():
            if not await self.users.find_one({"id": id}):
                await self.users.insert_one({
                    "id": id,
                    "name": name,
                    "video_count": 0,
                    "last_date": None,
                    "expiry_time": None
                })
        await self._execute(_op)

    async def is_user_exist(self, id):
        async def _op():
            result = await self.users.find_one({'id': int(id)})
            return bool(result)
        return await self._execute(_op)

    async def total_users_count(self):
        async def _op():
            return await self.users.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0

    async def delete_user(self, user_id):
        async def _op():
            await self.users.delete_many({'id': int(user_id)})
        await self._execute(_op)

    async def get_user(self, user_id):
        async def _op():
            return await self.users.find_one({"id": user_id})
        return await self._execute(_op)

    async def update_user(self, user_data):
        async def _op():
            await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)
        await self._execute(_op)

    async def get_all_users(self):
        async def _op():
            return self.users.find({})
        return await self._execute(_op)
        
    # ---------- COUNTS ----------
    async def total_files_count(self):
        async def _op():
            return await self.videos.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0

    async def total_brazzers_videos(self):
        async def _op():
            return await self.brazzers.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0

    async def total_blocked_count(self):
        async def _op():
            return await self.blocked_users.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0

    async def total_redeem_count(self):
        async def _op():
            return await self.codes.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0
        
    # ---------- REFERRAL SYSTEM ----------
    async def is_user_in_list(self, user_id):
        async def _op():
            user = await self.refer_collection.find_one({"user_id": int(user_id)})
            return True if user else False
        return await self._execute(_op)

    async def get_refer_points(self, user_id: int):
        async def _op():
            user = await self.refer_collection.find_one({"user_id": int(user_id)})
            return user.get("points", 0) if user else 0
        result = await self._execute(_op)
        return result if result is not None else 0

    async def add_refer_points(self, user_id: int, points: int):
        async def _op():
            await self.refer_collection.update_one(
                {"user_id": int(user_id)}, 
                {"$set": {"points": points}}, 
                upsert=True
            )
        await self._execute(_op)

    async def change_points(self, user_id: int, amount: int):
        async def _op():
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
        return await self._execute(_op)

    # ---------- MANUAL PAYMENT (ADD PREMIUM) ----------
    async def add_premium_access(self, user_id, days):
        async def _op():
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
        return await self._execute(_op)
        
    # ---------- BLOCK SYSTEM ----------
    async def unblock_user(self, user_id: int):
        async def _op():
            await self.blocked_users.delete_one({"user_id": user_id})
        await self._execute(_op)

    async def get_all_blocked_users(self):
        async def _op():
            return self.blocked_users.find({})
        return await self._execute(_op)

    async def is_user_blocked(self, user_id):
        async def _op():
            user = await self.blocked_users.find_one({"user_id": user_id})
            return bool(user)
        return await self._execute(_op)

    async def block_user(self, user_id, reason="Spam"):
        async def _op():
            await self.blocked_users.update_one(
                {"user_id": user_id},
                {"$set": {"blocked_at": datetime.now(timezone.utc), "reason": reason}},
                upsert=True
            )
        await self._execute(_op)

    async def add_temp_ban(self, user_id, duration_seconds):
        async def _op():
            expiry = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            await self.users.update_one(
                {"id": user_id},
                {"$set": {"temp_ban_expiry": expiry}}
            )
        await self._execute(_op)

    async def is_temp_banned(self, user_id):
        async def _op():
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
        return await self._execute(_op)
            
    # ---------- PREMIUM / EXPIRY ----------
    async def has_premium_access(self, user_id):
        async def _op():
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
        return await self._execute(_op)

    async def update_one(self, filter_query, update_data):
        async def _op():
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        return await self._execute(_op)

    async def get_expired(self, current_time):
        async def _op():
            expired_users = []
            cursor = self.users.find({"expiry_time": {"$lt": current_time}})
            async for user in cursor:
                expired_users.append(user)
            return expired_users
        return await self._execute(_op)

    async def get_expiring_soon(self, label, delta):
        async def _op():
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
        return await self._execute(_op)

    async def remove_premium_access(self, user_id):
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def premium_users_count(self):
        async def _op():
            return await self.users.count_documents({
                "expiry_time": {"$gt": datetime.now(timezone.utc)}
            })
        result = await self._execute(_op)
        return result if result is not None else 0

    async def get_db_size(self):
        async def _op():
            if self._db is None:
                return 0
            stats = await self._db.command("dbstats")
            return stats.get("dataSize", 0)
        result = await self._execute(_op)
        return result if result is not None else 0

    # =============================================
    # 🆕 VIDEOS SYSTEM - ONLY DURATION
    # =============================================
    async def add_video(self, file_unique_id, file_id, duration=0):
        async def _op():
            exists = await self.videos.find_one({"file_unique_id": file_unique_id})
            if not exists:
                await self.videos.insert_one({
                    "file_unique_id": file_unique_id,
                    "file_id": file_id,
                    "duration": duration,
                    "added_at": datetime.now(timezone.utc)
                })
                return True
            return False
        return await self._execute(_op)

    async def total_videos(self):
        async def _op():
            return await self.videos.count_documents({})
        result = await self._execute(_op)
        return result if result is not None else 0

    # =============================================
    # 🗑️ DELETE FUNCTIONS
    # =============================================
    async def delete_main_data(self):
        async def _op():
            await self.videos.delete_many({})
            await self.historys.delete_many({})
            return True
        return await self._execute(_op)

    async def delete_brazzers_data(self):
        async def _op():
            await self.brazzers.delete_many({})
            await self.braz_history.delete_many({})
            return True
        return await self._execute(_op)
        
    async def increase_video_count(self, user_id, username):
        async def _op():
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
        await self._execute(_op)
            
    async def get_video_count(self, user_id: int):
        async def _op():
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
        result = await self._execute(_op)
        return result if result is not None else 0

    # =====================================================
    # 🔥 GET UNSEEN VIDEO (DURATION LIMIT FOR FREE)
    # =====================================================
    async def get_unseen_video(self, user_id):
        async def _op():
            seen = await self.historys.find_one({"user_id": user_id})
            seen_ids = seen.get("seen", []) if seen else []

            is_premium_user = await self.has_premium_access(user_id)
            
            if is_premium_user:
                cursor = self.videos.find(
                    {"file_id": {"$nin": seen_ids}}, 
                    {"file_id": 1, "duration": 1}
                ).limit(500)
            else:
                cursor = self.videos.find(
                    {
                        "file_id": {"$nin": seen_ids},
                        "duration": {"$lte": FREE_VIDEO_DURATION}
                    }, 
                    {"file_id": 1, "duration": 1}
                ).limit(500)
            
            unseen_videos = await cursor.to_list(length=500)

            if not unseen_videos and not is_premium_user:
                cursor = self.videos.find(
                    {"duration": {"$lte": FREE_VIDEO_DURATION}},
                    {"file_id": 1}
                ).limit(500)
                unseen_videos = await cursor.to_list(length=500)
                if not unseen_videos:
                    return None
            elif not unseen_videos:
                return None

            video = random.choice(unseen_videos)
            await self.mark_seen(user_id, video["file_id"])
            return video["file_id"]
        return await self._execute(_op)

    # =====================================================
    # 🔥 GET RANDOM VIDEO (DURATION LIMIT FOR FREE)
    # =====================================================
    async def get_random_video(self, user_id=None):
        async def _op():
            try:
                if user_id:
                    is_premium_user = await self.has_premium_access(user_id)
                else:
                    is_premium_user = False
                
                filter_query = {}
                if not is_premium_user:
                    filter_query["duration"] = {"$lte": FREE_VIDEO_DURATION}
                
                pipeline = [{"$match": filter_query}, {"$sample": {"size": 1}}]
                cursor = self.videos.aggregate(pipeline)
                result = await cursor.to_list(length=1)
                
                if result:
                    return result[0]["file_id"]
            except Exception as e:
                print(f"Random video error: {e}")
            return None
        return await self._execute(_op)

    async def mark_seen(self, user_id, file_id):
        async def _op():
            await self.historys.update_one(
                {"user_id": user_id},
                {"$addToSet": {"seen": file_id}},
                upsert=True
            )
        await self._execute(_op)

    async def reset_seen_videos(self, user_id: int):
        async def _op():
            await self.historys.update_one(
                {"user_id": user_id},
                {"$set": {"seen": []}},
                upsert=True
            )
        await self._execute(_op)
        
    async def add_brazzers_video(self, file_unique_id, file_id):
        async def _op():
            exists = await self.brazzers.find_one({"file_unique_id": file_unique_id})
            if not exists:
                await self.brazzers.insert_one({
                    "file_unique_id": file_unique_id,
                    "file_id": file_id
                })
                return True
            return False
        return await self._execute(_op)

    async def get_unseen_brazzers(self, user_id):
        async def _op():
            seen = await self.braz_history.find_one({"user_id": user_id})
            seen_ids = seen.get("seen", []) if seen else []
            cursor = self.brazzers.find({"file_id": {"$nin": seen_ids}})
            unseen_videos = await cursor.to_list(length=1000)

            if not unseen_videos:
                return None

            video = random.choice(unseen_videos)
            await self.mark_brazzers_seen(user_id, video["file_id"])
            return video["file_id"]
        return await self._execute(_op)

    async def mark_brazzers_seen(self, user_id, file_id):
        async def _op():
            await self.braz_history.update_one(
                {"user_id": user_id},
                {"$addToSet": {"seen": file_id}},
                upsert=True
            )
        await self._execute(_op)
        
    async def reset_seen_brazzers(self, user_id: int):
        async def _op():
            await self.braz_history.update_one(
                {"user_id": user_id},
                {"$set": {"seen": []}},
                upsert=True
            )
        await self._execute(_op)
            
    # ---------- VERIFICATION SYSTEM ----------
    async def get_notcopy_user(self, user_id):
        async def _op():
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
        return await self._execute(_op)

    async def update_notcopy_user(self, user_id, value: dict):
        async def _op():
            user_id = int(user_id)
            myquery = {"user_id": user_id}
            newvalues = {"$set": value}
            return await self.misc.update_one(myquery, newvalues)
        return await self._execute(_op)

    async def is_user_verified(self, user_id):
        async def _op():
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
        return await self._execute(_op)

    # =================================================
    # RESET USER LIMIT FUNCTION
    # =================================================
    async def reset_user_video_limit(self, user_id: int):
        async def _op():
            try:
                today = get_ist_today()
                today_dt = datetime.combine(today, datetime.min.time())
                
                result = await self.users.update_one(
                    {"id": user_id},
                    {"$set": {
                        "video_count": 0,
                        "last_date": today_dt
                    }}
                )
                if result.modified_count > 0:
                    return True
                else:
                    user = await self.users.find_one({"id": user_id})
                    if user:
                        await self.users.update_one(
                            {"id": user_id},
                            {"$set": {"last_date": today_dt}}
                        )
                        return True
                    return False
            except Exception as e:
                print(f"Error resetting user limit: {e}")
                return False
        return await self._execute(_op)

    # ---------- VERIFICATION ID ----------
    async def create_verify_id(self, user_id: int, hash, file_id=None):
        async def _op():
            res = {"user_id": user_id, "hash": hash, "verified": False, "file_id": file_id}
            return await self.verify_id.insert_one(res)
        return await self._execute(_op)

    async def get_verify_id_info(self, user_id: int, hash):
        async def _op():
            return await self.verify_id.find_one({"user_id": user_id, "hash": hash})
        return await self._execute(_op)

    async def update_verify_id_info(self, user_id, hash, value: dict):
        async def _op():
            myquery = {"user_id": user_id, "hash": hash}
            newvalues = {"$set": value}
            return await self.verify_id.update_one(myquery, newvalues)
        return await self._execute(_op)

    async def get_verification_stats(self):
        async def _op():
            midnight_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            level1_count = await self.misc.count_documents({
                "last_verified": {"$gte": midnight_utc}
            })
            return level1_count
        result = await self._execute(_op)
        return result if result is not None else 0

# Initialize
db = Database()
print(f"📊 Database initialized: {db._db is not None}")
