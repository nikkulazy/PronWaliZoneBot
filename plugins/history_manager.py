# plugins/history_manager.py

from database.users_db import db
from datetime import datetime, timedelta
import random

class HistoryManager:
    """Manage user video history for Previous/Next navigation"""
    
    def __init__(self):
        self.collection = db.historys  # Already existing collection
    
    async def add_to_history(self, user_id: int, file_id: str, category: str = "main"):
        """
        Add video to user's history with timestamp
        category: "main" or "brazzers"
        """
        history_entry = {
            "file_id": file_id,
            "category": category,
            "timestamp": datetime.now()
        }
        
        await self.collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"history": history_entry},
                "$addToSet": {"seen": file_id}  # Keep seen list for uniqueness
            },
            upsert=True
        )
    
    async def get_previous_video(self, user_id: int, current_file_id: str, category: str = "main"):
        """
        Get previous video from user's history
        Returns file_id of previous video or None
        """
        user_history = await self.collection.find_one({"user_id": user_id})
        
        if not user_history or "history" not in user_history:
            return None
        
        history_list = user_history["history"]
        
        # Filter by category
        category_history = [h for h in history_list if h.get("category") == category]
        
        if len(category_history) < 2:
            return None
        
        # Find current video in history
        for i, entry in enumerate(category_history):
            if entry["file_id"] == current_file_id:
                if i > 0:  # Has previous
                    return category_history[i-1]["file_id"]
                else:
                    # Return last video if at first (loop back)
                    return category_history[-1]["file_id"]
        
        return None
    
    async def get_next_video(self, user_id: int, current_file_id: str, category: str = "main"):
        """
        Get next video from user's history
        Returns file_id of next video or None
        """
        user_history = await self.collection.find_one({"user_id": user_id})
        
        if not user_history or "history" not in user_history:
            return None
        
        history_list = user_history["history"]
        
        # Filter by category
        category_history = [h for h in history_list if h.get("category") == category]
        
        if len(category_history) < 2:
            return None
        
        # Find current video in history
        for i, entry in enumerate(category_history):
            if entry["file_id"] == current_file_id:
                if i < len(category_history) - 1:
                    return category_history[i+1]["file_id"]
                else:
                    # Return first video if at last (loop back)
                    return category_history[0]["file_id"]
        
        return None
    
    async def get_random_video_from_history(self, user_id: int, category: str = "main"):
        """Get random video from user's history"""
        user_history = await self.collection.find_one({"user_id": user_id})
        
        if not user_history or "history" not in user_history:
            return None
        
        history_list = user_history["history"]
        category_history = [h for h in history_list if h.get("category") == category]
        
        if not category_history:
            return None
        
        random_entry = random.choice(category_history)
        return random_entry["file_id"]
    
    async def clear_history(self, user_id: int, category: str = None):
        """Clear user's history (optionally by category)"""
        if category:
            await self.collection.update_one(
                {"user_id": user_id},
                {"$pull": {"history": {"category": category}}}
            )
        else:
            await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": []}}
            )
    
    async def get_history_count(self, user_id: int, category: str = "main"):
        """Get total history count for user"""
        user_history = await self.collection.find_one({"user_id": user_id})
        
        if not user_history or "history" not in user_history:
            return 0
        
        history_list = user_history["history"]
        category_history = [h for h in history_list if h.get("category") == category]
        
        return len(category_history)

# Initialize
history_manager = HistoryManager()
