import os
import random
import certifi
import pytz
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError

# Configuration
TIMEZONE = "Asia/Kolkata"
VERIFY_EXPIRE = 60  # seconds

def get_ist_today():
    ist = pytz.timezone(TIMEZONE)
    return datetime.now(ist).date()

# MongoDB Connection URI - à¤‡à¤¸à¥‡ à¤¬à¤¦à¤²à¤¨à¤¾ à¤®à¤¤ à¤­à¥‚à¤²à¤¨à¤¾
MONGO_URI = "mongodb+srv://mastitime:YOUR_REAL_PASSWORD@cluster0.rephea4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

class Database:
    def __init__(self):
        """Initialize MongoDB connection with SSL fix"""
        print("ðŸ”„ Initializing MongoDB Connection...")
        
        # Multiple connection attempts with different settings
        self.client = None
        connection_methods = [
            self._connect_with_certifi,
            self._connect_relaxed_ssl,
            self._connect_standard,
            self._connect_emergency
        ]
        
        for method in connection_methods:
            try:
                self.client = method()
                if self.client:
                    # Test connection
                    self.client.admin.command('ping')
                    print("âœ… MongoDB Connected Successfully!")
                    break
            except Exception as e:
                print(f"âš ï¸ Connection method failed: {e}")
                continue
        
        if not self.client:
            raise Exception("âŒ All MongoDB connection methods failed!")
        
        # Initialize database collections
        self.db = self.client['mastitime']  # à¤†à¤ªà¤•à¤¾ database name
        self.users = self.db['users']
        self.videos = self.db['videos']
        self.historys = self.db['historys']
        self.brazzers = self.db['brazzers']
        self.braz_history = self.db['braz_history']
        self.blocked_users = self.db['blocked_users']
        self.misc = self.db['misc']
        self.verify_id = self.db['verify_id']
        
        print("âœ… All collections initialized!")
    
    def _connect_with_certifi(self):
        """Method 1: Use certifi certificates (Recommended)"""
        return MongoClient(
            MONGO_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            retryWrites=True,
            w='majority',
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
    
    def _connect_relaxed_ssl(self):
        """Method 2: Relaxed SSL settings"""
        return MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            retryWrites=True,
            serverSelectionTimeoutMS=10000
        )
    
    def _connect_standard(self):
        """Method 3: Standard connection without SRV"""
        # Standard connection string (à¤†à¤ª à¤…à¤ªà¤¨à¤¾ à¤¯à¤¹à¤¾à¤ à¤¡à¤¾à¤²à¥‡à¤‚)
        standard_uri = "mongodb://mastitime:YOUR_REAL_PASSWORD@ac-sventfm-shard-00-00.tohbael.mongodb.net:27017,ac-sventfm-shard-00-01.tohbael.mongodb.net:27017,ac-sventfm-shard-00-02.tohbael.mongodb.net:27017/?ssl=true&replicaSet=atlas-yyy7tq&authSource=admin&retryWrites=true&w=majority"
        return MongoClient(
            standard_uri,
            serverSelectionTimeoutMS=10000
        )
    
    def _connect_emergency(self):
        """Method 4: Emergency - disable SSL verification"""
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        return MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=10000
        )
    
    # ---------- USER MANAGEMENT ----------
    async def is_user_exist(self, id):
        """Check if user exists in database"""
        try:
            user = await self.users.find_one({'id': int(id)})
            return bool(user)
        except Exception as e:
            print(f"Error in is_user_exist: {e}")
            return False
    
    async def get_user(self, user_id):
        """Get user data"""
        try:
            return await self.users.find_one({"id": user_id})
        except Exception as e:
            print(f"Error in get_user: {e}")
            return None
    
    async def add_user(self, user_id, username=None):
        """Add new user to database"""
        try:
            existing = await self.get_user(user_id)
            if not existing:
                await self.users.insert_one({
                    "id": user_id,
                    "name": username,
                    "video_count": 0,
                    "expiry_time": None,
                    "joined_at": datetime.now(timezone.utc)
                })
                return True
            return False
        except Exception as e:
            print(f"Error in add_user: {e}")
            return False
    
    # ---------- MANUAL PAYMENT (ADD PREMIUM) ----------
    async def add_premium_access(self, user_id, days):
        """Add premium access to user"""
        try:
            user = await self.get_user(user_id)
            now = datetime.now(timezone.utc)
            
            current_expiry = user.get("expiry_time") if user else None
            
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
        except Exception as e:
            print(f"Error in add_premium_access: {e}")
            return None
    
    # ---------- BLOCK SYSTEM ----------
    async def unblock_user(self, user_id: int):
        """Unblock a user"""
        try:
            await self.blocked_users.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            print(f"Error in unblock_user: {e}")
            return False
    
    async def get_all_blocked_users(self):
        """Fetch all blocked users"""
        try:
            return self.blocked_users.find({})
        except Exception as e:
            print(f"Error in get_all_blocked_users: {e}")
            return []
    
    async def is_user_blocked(self, user_id):
        """Check if user is blocked"""
        try:
            user = await self.blocked_users.find_one({"user_id": user_id})
            return bool(user)
        except Exception as e:
            print(f"Error in is_user_blocked: {e}")
            return False
    
    async def block_user(self, user_id, reason="Spam"):
        """Block a user"""
        try:
            await self.blocked_users.update_one(
                {"user_id": user_id},
                {"$set": {"blocked_at": datetime.now(timezone.utc), "reason": reason}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error in block_user: {e}")
            return False
    
    async def add_temp_ban(self, user_id, duration_seconds):
        """Add temporary ban"""
        try:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            await self.users.update_one(
                {"id": user_id},
                {"$set": {"temp_ban_expiry": expiry}}
            )
            return True
        except Exception as e:
            print(f"Error in add_temp_ban: {e}")
            return False
    
    async def is_temp_banned(self, user_id):
        """Check if user is temporarily banned"""
        try:
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
        except Exception as e:
            print(f"Error in is_temp_banned: {e}")
            return False, 0
    
    # ---------- PREMIUM / EXPIRY ----------
    async def has_premium_access(self, user_id):
        """Check if user has premium access"""
        try:
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
        except Exception as e:
            print(f"Error in has_premium_access: {e}")
            return False
    
    async def update_one(self, filter_query, update_data):
        """Update one document"""
        try:
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        except Exception as e:
            print(f"Error updating document: {e}")
            return False
    
    async def get_expired(self, current_time):
        """Get expired users"""
        try:
            expired_users = []
            cursor = self.users.find({"expiry_time": {"$lt": current_time}})
            async for user in cursor:
                expired_users.append(user)
            return expired_users
        except Exception as e:
            print(f"Error in get_expired: {e}")
            return []
    
    async def get_expiring_soon(self, label, delta):
        """Get users whose premium expires soon"""
        try:
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
        except Exception as e:
            print(f"Error in get_expiring_soon: {e}")
            return []
    
    async def remove_premium_access(self, user_id):
        """Remove premium access"""
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )
    
    async def premium_users_count(self):
        """Count premium users"""
        try:
            return await self.users.count_documents({
                "expiry_time": {"$gt": datetime.now(timezone.utc)}
            })
        except Exception as e:
            print(f"Error in premium_users_count: {e}")
            return 0
    
    async def get_db_size(self):
        """Get database size"""
        try:
            stats = await self.db.command("dbstats")
            return stats.get("dataSize", 0)
        except Exception as e:
            print(f"Error in get_db_size: {e}")
            return 0
    
    # ---------- VIDEOS SYSTEM ----------
    async def add_video(self, file_unique_id, file_id):
        """Add video to database"""
        try:
            exists = await self.videos.find_one({"file_unique_id": file_unique_id})
            if not exists:
                await self.videos.insert_one({
                    "file_unique_id": file_unique_id,
                    "file_id": file_id,
                    "added_at": datetime.now(timezone.utc)
                })
                return True
            return False
        except Exception as e:
            print(f"Error in add_video: {e}")
            return False
    
    async def total_videos(self):
        """Get total video count"""
        try:
            return await self.videos.count_documents({})
        except Exception as e:
            print(f"Error in total_videos: {e}")
            return 0
    
    async def delete_main_data(self):
        """Delete all main videos and history"""
        try:
            await self.videos.delete_many({})
            await self.historys.delete_many({})
            return True
        except Exception as e:
            print(f"Error in delete_main_data: {e}")
            return False
    
    async def delete_brazzers_data(self):
        """Delete all brazzers videos and history"""
        try:
            await self.brazzers.delete_many({})
            await self.braz_history.delete_many({})
            return True
        except Exception as e:
            print(f"Error in delete_brazzers_data: {e}")
            return False
    
    async def increase_video_count(self, user_id, username):
        """Increase user's video watch count"""
        try:
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
            return True
        except Exception as e:
            print(f"Error in increase_video_count: {e}")
            return False
    
    async def get_video_count(self, user_id: int):
        """Get user's today's video count"""
        try:
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
        except Exception as e:
            print(f"Error in get_video_count: {e}")
            return 0
    
    async def get_unseen_video(self, user_id):
        """Get unseen video for user"""
        try:
            seen = await self.historys.find_one({"user_id": user_id})
            seen_ids = seen.get("seen", []) if seen else []
            
            cursor = self.videos.find({"file_id": {"$nin": seen_ids}}, {"file_id": 1}).limit(500)
            unseen_videos = await cursor.to_list(length=500)
            
            if not unseen_videos:
                return await self.get_random_video()
            
            video = random.choice(unseen_videos)
            await self.mark_seen(user_id, video["file_id"])
            return video["file_id"]
        except Exception as e:
            print(f"Error in get_unseen_video: {e}")
            return None
    
    async def get_random_video(self):
        """Get random video"""
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
        """Mark video as seen"""
        try:
            await self.historys.update_one(
                {"user_id": user_id},
                {"$addToSet": {"seen": file_id}},
                upsert=True
            )
        except Exception as e:
            print(f"Error in mark_seen: {e}")
    
    async def reset_seen_videos(self, user_id: int):
        """Reset seen videos for user"""
        try:
            await self.historys.update_one(
                {"user_id": user_id},
                {"$set": {"seen": []}},
                upsert=True
            )
        except Exception as e:
            print(f"Error in reset_seen_videos: {e}")
    
    async def add_brazzers_video(self, file_unique_id, file_id):
        """Add brazzers video"""
        try:
            exists = await self.brazzers.find_one({"file_unique_id": file_unique_id})
            if not exists:
                await self.brazzers.insert_one({
                    "file_unique_id": file_unique_id,
                    "file_id": file_id
                })
                return True
            return False
        except Exception as e:
            print(f"Error in add_brazzers_video: {e}")
            return False
    
    async def get_unseen_brazzers(self, user_id):
        """Get unseen brazzers video"""
        try:
            seen = await self.braz_history.find_one({"user_id": user_id})
            seen_ids = seen.get("seen", []) if seen else []
            cursor = self.brazzers.find({"file_id": {"$nin": seen_ids}})
            unseen_videos = await cursor.to_list(length=1000)
            
            if not unseen_videos:
                return None
            
            video = random.choice(unseen_videos)
            await self.mark_brazzers_seen(user_id, video["file_id"])
            return video["file_id"]
        except Exception as e:
            print(f"Error in get_unseen_brazzers: {e}")
            return None
    
    async def mark_brazzers_seen(self, user_id, file_id):
        """Mark brazzers video as seen"""
        try:
            await self.braz_history.update_one(
                {"user_id": user_id},
                {"$addToSet": {"seen": file_id}},
                upsert=True
            )
        except Exception as e:
            print(f"Error in mark_brazzers_seen: {e}")
    
    async def reset_seen_brazzers(self, user_id: int):
        """Reset seen brazzers videos"""
        try:
            await self.braz_history.update_one(
                {"user_id": user_id},
                {"$set": {"seen": []}},
                upsert=True
            )
        except Exception as e:
            print(f"Error in reset_seen_brazzers: {e}")
    
    # ---------- VERIFICATION SYSTEM ----------
    async def get_notcopy_user(self, user_id):
        """Get user verification data"""
        try:
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
        except Exception as e:
            print(f"Error in get_notcopy_user: {e}")
            return {"user_id": user_id, "last_verified": datetime.now(timezone.utc)}
    
    async def update_notcopy_user(self, user_id, value: dict):
        """Update user verification data"""
        try:
            user_id = int(user_id)
            myquery = {"user_id": user_id}
            newvalues = {"$set": value}
            return await self.misc.update_one(myquery, newvalues)
        except Exception as e:
            print(f"Error in update_notcopy_user: {e}")
            return None
    
    async def is_user_verified(self, user_id):
        """Check if user is verified"""
        try:
            user = await self.get_notcopy_user(user_id)
            
            pastDate = user.get("last_verified")
            
            if not pastDate:
                pastDate = datetime(2020, 5, 17, 0, 0, 0, tzinfo=timezone.utc)
            
            if pastDate.tzinfo is None:
                pastDate = pastDate.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - pastDate
            
            return time_diff < timedelta(seconds=VERIFY_EXPIRE)
        except Exception as e:
            print(f"Error in is_user_verified: {e}")
            return False
    
    async def create_verify_id(self, user_id: int, hash, file_id=None):
        """Create verification ID"""
        try:
            res = {"user_id": user_id, "hash": hash, "verified": False, "file_id": file_id}
            return await self.verify_id.insert_one(res)
        except Exception as e:
            print(f"Error in create_verify_id: {e}")
            return None
    
    async def get_verify_id_info(self, user_id: int, hash):
        """Get verification ID info"""
        try:
            return await self.verify_id.find_one({"user_id": user_id, "hash": hash})
        except Exception as e:
            print(f"Error in get_verify_id_info: {e}")
            return None
    
    async def update_verify_id_info(self, user_id, hash, value: dict):
        """Update verification ID info"""
        try:
            myquery = {"user_id": user_id, "hash": hash}
            newvalues = {"$set": value}
            return await self.verify_id.update_one(myquery, newvalues)
        except Exception as e:
            print(f"Error in update_verify_id_info: {e}")
            return None
    
    async def get_verification_stats(self):
        """Get verification statistics"""
        try:
            midnight_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            level1_count = await self.misc.count_documents({
                "last_verified": {"$gte": midnight_utc}
            })
            return level1_count
        except Exception as e:
            print(f"Error in get_verification_stats: {e}")
            return 0

# Initialize database
print("ðŸš€ Creating database instance...")
db = Database()
print("âœ… Database instance ready!")
