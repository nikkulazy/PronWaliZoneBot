from .users_db import Database

class DatabaseManager:
    def __init__(self, db):
        self.db = db
        
        # =============================================
        # MAIN COLLECTIONS
        # =============================================
        self.users = db.users
        self.videos = db.videos
        self.brazzers_videos = db.brazzers_videos
        self.redeem_codes = db.redeem_codes
        self.blocked_users = db.blocked_users
        self.verify_ids = db.verify_ids
        
        # =============================================
        # REACTIONS & HISTORY COLLECTIONS (NEW)
        # =============================================
        self.user_reactions = db.user_reactions
        self.video_reactions = db.video_reactions
        self.user_history = db.user_history
        
        # =============================================
        # DATABASE INSTANCE
        # =============================================
        self.db_instance = Database(db)

    # =============================================
    # USER MANAGEMENT
    # =============================================
    
    async def add_user(self, user_id, name):
        return await self.db_instance.add_user(user_id, name)

    async def is_user_exist(self, user_id):
        return await self.db_instance.is_user_exist(user_id)

    async def get_user(self, user_id):
        return await self.db_instance.get_user(user_id)

    async def update_user(self, user_data):
        return await self.db_instance.update_user(user_data)

    async def get_all_users(self):
        return await self.db_instance.get_all_users()

    async def total_users_count(self):
        return await self.db_instance.total_users_count()

    async def delete_user(self, user_id):
        return await self.db_instance.delete_user(user_id)

    # =============================================
    # VIDEO COUNT / LIMITS
    # =============================================

    async def get_video_count(self, user_id):
        return await self.db_instance.get_video_count(user_id)

    async def increase_video_count(self, user_id, username):
        return await self.db_instance.increase_video_count(user_id, username)

    # =============================================
    # PREMIUM MANAGEMENT
    # =============================================

    async def has_premium_access(self, user_id):
        return await self.db_instance.has_premium_access(user_id)

    async def add_premium_access(self, user_id, days):
        return await self.db_instance.add_premium_access(user_id, days)

    async def remove_premium_access(self, user_id):
        return await self.db_instance.remove_premium_access(user_id)

    async def premium_users_count(self):
        return await self.db_instance.premium_users_count()

    # =============================================
    # USER VERIFICATION
    # =============================================

    async def is_user_verified(self, user_id):
        return await self.db_instance.is_user_verified(user_id)

    async def update_notcopy_user(self, user_id, data):
        return await self.db_instance.update_notcopy_user(user_id, data)

    # =============================================
    # VERIFICATION ID (For Shortlink Verification)
    # =============================================

    async def create_verify_id(self, user_id, verify_id, file_id):
        return await self.db_instance.create_verify_id(user_id, verify_id, file_id)

    async def get_verify_id_info(self, user_id, verify_id):
        return await self.db_instance.get_verify_id_info(user_id, verify_id)

    async def update_verify_id_info(self, user_id, verify_id, data):
        return await self.db_instance.update_verify_id_info(user_id, verify_id, data)

    # =============================================
    # VIDEOS MANAGEMENT
    # =============================================

    async def add_video(self, file_unique_id, file_id):
        return await self.db_instance.add_video(file_unique_id, file_id)

    async def total_files_count(self):
        return await self.db_instance.total_files_count()

    async def get_random_video(self):
        return await self.db_instance.get_random_video()

    async def get_unseen_video(self, user_id):
        return await self.db_instance.get_unseen_video(user_id)

    async def delete_main_data(self):
        return await self.db_instance.delete_main_data()

    # =============================================
    # BRAZZERS VIDEOS MANAGEMENT
    # =============================================

    async def add_brazzers_video(self, file_unique_id, file_id):
        return await self.db_instance.add_brazzers_video(file_unique_id, file_id)

    async def total_brazzers_videos(self):
        return await self.db_instance.total_brazzers_videos()

    async def get_random_brazzers_video(self):
        return await self.db_instance.get_random_brazzers_video()

    async def get_unseen_brazzers(self, user_id):
        return await self.db_instance.get_unseen_brazzers(user_id)

    async def delete_brazzers_data(self):
        return await self.db_instance.delete_brazzers_data()

    # =============================================
    # VIDEO REACTIONS (Like / Dislike) - NEW
    # =============================================

    async def get_video_reactions(self, video_id):
        return await self.db_instance.get_video_reactions(video_id)

    async def add_reaction(self, user_id, video_id, reaction_type):
        return await self.db_instance.add_reaction(user_id, video_id, reaction_type)

    async def remove_reaction(self, user_id, video_id, reaction_type):
        return await self.db_instance.remove_reaction(user_id, video_id, reaction_type)

    async def get_user_reaction(self, user_id, video_id):
        return await self.db_instance.get_user_reaction(user_id, video_id)

    # =============================================
    # USER HISTORY (For Previous Button) - NEW
    # =============================================

    async def add_to_user_history(self, user_id, video_id, category="main"):
        return await self.db_instance.add_to_user_history(user_id, video_id, category)

    async def get_previous_video(self, user_id, current_video_id, category="main"):
        return await self.db_instance.get_previous_video(user_id, current_video_id, category)

    async def get_user_history_count(self, user_id, category="main"):
        return await self.db_instance.get_user_history_count(user_id, category)

    async def get_user_history_all(self, user_id, category="main"):
        return await self.db_instance.get_user_history_all(user_id, category)

    # =============================================
    # BLOCKED USERS
    # =============================================

    async def block_user(self, user_id):
        return await self.db_instance.block_user(user_id)

    async def unblock_user(self, user_id):
        return await self.db_instance.unblock_user(user_id)

    async def is_user_blocked(self, user_id):
        return await self.db_instance.is_user_blocked(user_id)

    async def total_blocked_count(self):
        return await self.db_instance.total_blocked_count()

    async def get_all_blocked_users(self):
        return await self.db_instance.get_all_blocked_users()

    # =============================================
    # REDEEM CODES
    # =============================================

    async def add_redeem_code(self, code, days):
        return await self.db_instance.add_redeem_code(code, days)

    async def total_redeem_count(self):
        return await self.db_instance.total_redeem_count()

    async def use_redeem_code(self, code, user_id):
        return await self.db_instance.use_redeem_code(code, user_id)

    async def get_all_redeem_codes(self):
        return await self.db_instance.get_all_redeem_codes()

    async def delete_redeem_code(self, code):
        return await self.db_instance.delete_redeem_code(code)

    async def clear_redeem_codes(self):
        return await self.db_instance.clear_redeem_codes()

    # =============================================
    # DATABASE STATS
    # =============================================

    async def get_db_size(self):
        return await self.db_instance.get_db_size()
