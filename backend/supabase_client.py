
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    """
    Manages Supabase connection for syncing settings and logging gestures.
    """
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print("✅ Supabase Client Initialized")
            except Exception as e:
                print(f"⚠️ Supabase Init Failed: {e}")
        else:
            print("⚠️ Supabase Credentials missing in .env")

    def log_gesture(self, gesture_data: dict, user_id: str = None):
        """Log a gesture to the database"""
        if not self.client: return
        
        try:
            data = {**gesture_data}
            if user_id:
                data['user_id'] = user_id
                
            self.client.table('gestures_log').insert(data).execute()
        except Exception as e:
            print(f"Failed to log gesture to Supabase: {e}")

    def get_user_settings(self, user_id: str):
        """Fetch settings for a specific user"""
        if not self.client: return None
        try:
            response = self.client.table('user_settings').select("*").eq('user_id', user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Failed to fetch settings: {e}")
            return None

    def save_user_settings(self, user_id: str, settings: dict):
        """Save/Update user settings"""
        if not self.client: return
        try:
            data = {**settings, 'user_id': user_id}
            self.client.table('user_settings').upsert(data).execute()
        except Exception as e:
            print(f"Failed to save settings: {e}")
