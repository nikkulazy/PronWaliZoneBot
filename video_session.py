# plugins/video_session.py

class VideoSession:
    """Store user's current and previous video in memory"""
    
    def __init__(self):
        self.user_videos = {}  # {user_id: {"current": file_id, "previous": file_id}}
    
    def set_current(self, user_id: int, file_id: str):
        """Set current video for user"""
        if user_id not in self.user_videos:
            self.user_videos[user_id] = {}
        
        # Save previous video
        if "current" in self.user_videos[user_id]:
            self.user_videos[user_id]["previous"] = self.user_videos[user_id]["current"]
        
        # Set new current
        self.user_videos[user_id]["current"] = file_id
    
    def get_previous(self, user_id: int):
        """Get previous video for user"""
        if user_id not in self.user_videos:
            return None
        return self.user_videos[user_id].get("previous")
    
    def get_current(self, user_id: int):
        """Get current video for user"""
        if user_id not in self.user_videos:
            return None
        return self.user_videos[user_id].get("current")
    
    def clear(self, user_id: int):
        """Clear user session"""
        if user_id in self.user_videos:
            del self.user_videos[user_id]

video_session = VideoSession()
