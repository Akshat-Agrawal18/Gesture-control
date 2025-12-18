
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

class SheetsManager:
    """
    Manages Google Sheets connection for logging usage data to User's Drive.
    """
    def __init__(self):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds_file = "credentials.json"
        self.client = None
        self.sheet = None
        
        if os.path.exists(self.creds_file):
            try:
                self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_file, self.scope)
                self.client = gspread.authorize(self.creds)
                print("✅ Google Sheets Client Initialized")
                
                # Open or create sheet
                try:
                    self.sheet = self.client.open("EYES_Gesture_Logs")
                except gspread.SpreadsheetNotFound:
                    self.sheet = self.client.create("EYES_Gesture_Logs")
                    print("Created new sheet: EYES_Gesture_Logs")
                    # Init headers
                    self.sheet.sheet1.append_row(["Timestamp", "Gesture", "Hand", "Confidence", "Volume", "Brightness"])
                    
            except Exception as e:
                print(f"⚠️ Google Sheets Init Failed: {e}")
        else:
            print("⚠️ credentials.json not found for Google Sheets")

    def log_session_data(self, gesture_data: dict):
        """Append a row of data to the sheet"""
        if not self.client or not self.sheet: return

        try:
            row = [
                time.strftime("%Y-%m-%d %H:%M:%S"),
                gesture_data.get("gesture"),
                gesture_data.get("hand"),
                gesture_data.get("confidence"),
                gesture_data.get("volume_at_time"),
                gesture_data.get("brightness_at_time")
            ]
            self.sheet.sheet1.append_row(row)
        except Exception as e:
            print(f"Failed to write to Sheet: {e}")
