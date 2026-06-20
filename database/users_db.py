import datetime
import pytz
import random
from datetime import timedelta
from info import TIMEZONE, PREMIUM_DAILY_LIMIT, DAILY_LIMIT, VERIFICATION_DAILY_LIMIT

class Database:
    def __init__(self, db):
        self.db = db
        self.users = db.users
        self.videos = db.videos
        self.brazzers_videos = db.brazzers_videos
        self.redeem_codes = db.redeem_codes
        self.blocked_users = db.blocked_users
        self.verify_ids = db.verify_ids
        self.user_reactions = db.user_reactions
        self.video_reactions = db.video_reactions
        self.user_history = db.user_history

    # =============================================
    # USER MANAGEMENT
    # =============================================

    async def add_user(self, user_id, name):
        """Add new user to database"""
        user_data = {
            "id": user_id,
            "name": name,
            "username": None,
            "date": datetime.datetime.now(),
            "video_count": 0,
            "premium": False,
            "expiry_time": None,
            "verified": False,
            "last_verified": None
        }
        await self.users.insert_one(user_data)

    async def is_user_exist(self, user_id):
        """Check if user exists"""
        return await self.users.find_one({"id": user_id}) is not None

    async def get_user(self, user_id):
        """Get user data"""
        return await self.users.find_one({"id": user_id})

    async def update_user(self, user_data):
        """Update user data"""
        await self.users.update_one(
            {"id": user_data["id"]},
            {"$set": user_data},
            upsert=True
        )

    async def get_all_users(self):
        """Get all users"""
        return self.users.find({})

    async def total_users_count(self):
        """Get total users count"""
        return await self.users.count_documents({})

    async def delete_user(self, user_id):
        """Delete user"""
        await self.users.delete_one({"id": user_id})

    # =============================================
    # VIDEO COUNT / LIMITS
    # =============================================

    async def get_video_count(self, user_id):
        """Get user's daily video count"""
        user = await self.get_user(user_id)
        if user:
            last_date = user.get("last_date")
            today = datetime.datetime.now().date()
            
            # Reset count if new day
            if last_date != today:
                await self.users.update_one(
                    {"id": user_id},
                    {"$set": {"video_count": 0, "last_date": today}}
                )
                return 0
            return user.get("video_count", 0)
        return 0

    async def increase_video_count(self, user_id, username):
        """Increase user's daily video count"""
        today = datetime.datetime.now().date()
        await self.users.update_one(
            {"id": user_id},
            {
                "$inc": {"video_count": 1},
                "$set": {"last_date": today, "username": username}
            },
            upsert=True
        )

    # =============================================
    # PREMIUM MANAGEMENT
    # =============================================

    async def has_premium_access(self, user_id):
        """Check if user has premium access"""
        user = await self.get_user(user_id)
        if not user:
            return False
        
        if user.get("premium", False):
            expiry = user.get("expiry_time")
            if expiry:
                # Check if expiry time has passed
                if expiry < datetime.datetime.now():
                    await self.remove_premium_access(user_id)
                    return False
                return True
        return False

    async def add_premium_access(self, user_id, days):
        """Add premium access to user"""
        expiry_time = datetime.datetime.now() + timedelta(days=days)
        
        await self.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "premium": True,
                    "expiry_time": expiry_time
                }
            },
            upsert=True
        )
        return expiry_time

    async def remove_premium_access(self, user_id):
        """Remove premium access from user"""
        result = await self.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "premium": False,
                    "expiry_time": None
                }
            }
        )
        return result.modified_count > 0

    async def premium_users_count(self):
        """Get premium users count"""
        return await self.users.count_documents({"premium": True})

    # =============================================
    # USER VERIFICATION
    # =============================================

    async def is_user_verified(self, user_id):
        """Check if user is verified"""
        user = await self.get_user(user_id)
        if user:
            return user.get("verified", False)
        return False

    async def update_notcopy_user(self, user_id, data):
        """Update user verification"""
        await self.users.update_one(
            {"id": user_id},
            {"$set": data},
            upsert=True
        )

    # =============================================
    # VERIFICATION ID (For Shortlink Verification)
    # =============================================

    async def create_verify_id(self, user_id, verify_id, file_id):
        """Create verification ID"""
        await self.verify_ids.insert_one({
            "user_id": user_id,
            "verify_id": verify_id,
            "file_id": file_id,
            "verified": False,
            "created_at": datetime.datetime.now()
        })

    async def get_verify_id_info(self, user_id, verify_id):
        """Get verification ID info"""
        return await self.verify_ids.find_one({
            "user_id": user_id,
            "verify_id": verify_id
        })

    async def update_verify_id_info(self, user_id, verify_id, data):
        """Update verification ID info"""
        await self.verify_ids.update_one(
            {"user_id": user_id, "verify_id": verify_id},
            {"$set": data}
        )

    # =============================================
    # VIDEOS MANAGEMENT
    # =============================================

    async def add_video(self, file_unique_id, file_id):
        """Add video to database"""
        existing = await self.videos.find_one({"file_unique_id": file_unique_id})
        if existing:
            return False
        
        await self.videos.insert_one({
            "file_unique_id": file_unique_id,
            "file_id": file_id
        })
        return True

    async def total_files_count(self):
        """Get total files count"""
        return await self.videos.count_documents({})

    async def get_random_video(self):
        """Get random video"""
        pipeline = [{"$sample": {"size": 1}}]
        result = await self.videos.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["file_unique_id"]
        return None

    async def get_unseen_video(self, user_id):
        """Get unseen video for user"""
        # Get user's seen videos from history
        user_data = await self.user_history.find_one({"user_id": user_id})
        seen_videos = []
        if user_data and "history" in user_data:
            seen_videos = [h["video_id"] for h in user_data["history"] if h.get("category") == "main"]
        
        # Get videos not in seen list
        pipeline = [
            {"$match": {"file_unique_id": {"$nin": seen_videos}}},
            {"$sample": {"size": 1}}
        ]
        result = await self.videos.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["file_unique_id"]
        return None

    async def delete_main_data(self):
        """Delete all main videos"""
        await self.videos.delete_many({})
        return True

    # =============================================
    # BRAZZERS VIDEOS MANAGEMENT
    # =============================================

    async def add_brazzers_video(self, file_unique_id, file_id):
        """Add brazzers video to database"""
        existing = await self.brazzers_videos.find_one({"file_unique_id": file_unique_id})
        if existing:
            return False
        
        await self.brazzers_videos.insert_one({
            "file_unique_id": file_unique_id,
            "file_id": file_id
        })
        return True

    async def total_brazzers_videos(self):
        """Get total brazzers videos count"""
        return await self.brazzers_videos.count_documents({})

    async def get_random_brazzers_video(self):
        """Get random brazzers video"""
        pipeline = [{"$sample": {"size": 1}}]
        result = await self.brazzers_videos.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["file_unique_id"]
        return None

    async def get_unseen_brazzers(self, user_id):
        """Get unseen brazzers video for user"""
        user_data = await self.user_history.find_one({"user_id": user_id})
        seen_videos = []
        if user_data and "history" in user_data:
            seen_videos = [h["video_id"] for h in user_data["history"] if h.get("category") == "brazzers"]
        
        pipeline = [
            {"$match": {"file_unique_id": {"$nin": seen_videos}}},
            {"$sample": {"size": 1}}
        ]
        result = await self.brazzers_videos.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["file_unique_id"]
        return None

    async def delete_brazzers_data(self):
        """Delete all brazzers videos"""
        await self.brazzers_videos.delete_many({})
        return True

    # =============================================
    # VIDEO REACTIONS (Like / Dislike)
    # =============================================

    async def get_video_reactions(self, video_id):
        """Get like/dislike counts for a video"""
        data = await self.video_reactions.find_one({"video_id": video_id})
        if data:
            return {
                "likes": data.get("likes", 0),
                "dislikes": data.get("dislikes", 0)
            }
        return {"likes": 0, "dislikes": 0}

    async def add_reaction(self, user_id, video_id, reaction_type):
        """Add like or dislike"""
        update_field = "likes" if reaction_type == 'like' else "dislikes"
        
        # Update video reactions
        await self.video_reactions.update_one(
            {"video_id": video_id},
            {"$inc": {update_field: 1}},
            upsert=True
        )
        
        # Save user reaction
        await self.user_reactions.update_one(
            {"user_id": user_id, "video_id": video_id},
            {"$set": {"reaction": reaction_type}},
            upsert=True
        )

    async def remove_reaction(self, user_id, video_id, reaction_type):
        """Remove like or dislike"""
        update_field = "likes" if reaction_type == 'like' else "dislikes"
        
        await self.video_reactions.update_one(
            {"video_id": video_id},
            {"$inc": {update_field: -1}}
        )
        
        await self.user_reactions.delete_one(
            {"user_id": user_id, "video_id": video_id}
        )

    async def get_user_reaction(self, user_id, video_id):
        """Get user's reaction for a video"""
        data = await self.user_reactions.find_one(
            {"user_id": user_id, "video_id": video_id}
        )
        return data.get("reaction") if data else None

    # =============================================
    # USER HISTORY (For Previous Button)
    # =============================================

    async def add_to_user_history(self, user_id, video_id, category="main"):
        """Add video to user's watch history"""
        ist_timezone = pytz.timezone(TIMEZONE)
        current_time = datetime.datetime.now(tz=ist_timezone)
        
        # Remove if already exists (to avoid duplicates)
        await self.user_history.update_one(
            {"user_id": user_id},
            {"$pull": {"history": {"video_id": video_id}}}
        )
        
        # Add new entry at the end
        await self.user_history.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "history": {
                        "video_id": video_id,
                        "category": category,
                        "timestamp": current_time
                    }
                }
            },
            upsert=True
        )
        
        # Keep only last 50 videos (limit history)
        user_data = await self.user_history.find_one({"user_id": user_id})
        if user_data and "history" in user_data:
            if len(user_data["history"]) > 50:
                # Remove oldest
                await self.user_history.update_one(
                    {"user_id": user_id},
                    {"$pop": {"history": -1}}
                )

    async def get_previous_video(self, user_id, current_video_id, category="main"):
        """Get previous video from user's history"""
        data = await self.user_history.find_one({"user_id": user_id})
        
        if data and "history" in data:
            history = data["history"]
            
            # Filter by category
            history = [h for h in history if h.get("category") == category]
            
            # Find current video index
            for i, h in enumerate(history):
                if h["video_id"] == current_video_id:
                    if i > 0:
                        return history[i - 1]["video_id"]
        return None

    async def get_user_history_count(self, user_id, category="main"):
        """Get count of user's history for a category"""
        data = await self.user_history.find_one({"user_id": user_id})
        
        if data and "history" in data:
            count = len([h for h in data["history"] if h.get("category") == category])
            return count
        return 0

    async def get_user_history_all(self, user_id, category="main"):
        """Get all user's history for a category"""
        data = await self.user_history.find_one({"user_id": user_id})
        
        if data and "history" in data:
            history = [h["video_id"] for h in data["history"] if h.get("category") == category]
            return history
        return []

    # =============================================
    # BLOCKED USERS
    # =============================================

    async def block_user(self, user_id):
        """Block a user"""
        await self.blocked_users.insert_one({"user_id": user_id})

    async def unblock_user(self, user_id):
        """Unblock a user"""
        await self.blocked_users.delete_one({"user_id": user_id})

    async def is_user_blocked(self, user_id):
        """Check if user is blocked"""
        return await self.blocked_users.find_one({"user_id": user_id}) is not None

    async def total_blocked_count(self):
        """Get total blocked users count"""
        return await self.blocked_users.count_documents({})

    async def get_all_blocked_users(self):
        """Get all blocked users"""
        return self.blocked_users.find({})

    # =============================================
    # REDEEM CODES
    # =============================================

    async def add_redeem_code(self, code, days):
        """Add a redeem code"""
        await self.redeem_codes.insert_one({
            "code": code,
            "days": days,
            "used": False,
            "used_by": None,
            "created_at": datetime.datetime.now()
        })

    async def total_redeem_count(self):
        """Get total redeem codes count"""
        return await self.redeem_codes.count_documents({})

    async def use_redeem_code(self, code, user_id):
        """Use a redeem code"""
        code_data = await self.redeem_codes.find_one({"code": code, "used": False})
        if code_data:
            await self.redeem_codes.update_one(
                {"code": code},
                {"$set": {"used": True, "used_by": user_id}}
            )
            return code_data.get("days", 0)
        return 0

    async def get_all_redeem_codes(self):
        """Get all redeem codes"""
        return self.redeem_codes.find({})

    async def delete_redeem_code(self, code):
        """Delete a redeem code"""
        await self.redeem_codes.delete_one({"code": code})

    async def clear_redeem_codes(self):
        """Clear all redeem codes"""
        await self.redeem_codes.delete_many({})

    # =============================================
    # DATABASE STATS
    # =============================================

    async def get_db_size(self):
        """Get database size"""
        stats = await self.db.command("dbStats")
        return stats.get("dataSize", 0)
