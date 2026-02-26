import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# The Google Sheets API scopes required
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Authenticates and returns the Google Sheets API service."""
    creds = None
    if os.path.exists('credentials.json'):
        creds = Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES)
    else:
        raise FileNotFoundError("credentials.json not found in the root directory")

    service = build('sheets', 'v4', credentials=creds)
    return service

def append_to_sheet(data: dict):
    """
    Deterministically appends a row to the Google Sheet based on the provided dictionary.
    
    Expected keys conform to the VAPI Output Pipeline Data Schema in GEMINI.md.
    """
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    range_name = os.getenv("SHEET_NAME", "Sheet1")
    
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID is missing from the environment variables.")
        
    try:
        service = get_sheets_service()
        
        # Structure the values based on our agreed schema
        values = [
            [
                data.get("caller_first_name", ""),
                data.get("caller_last_name", ""),
                data.get("phone_number", ""),
                data.get("zip_code", ""),
                data.get("standing_or_leaking_water", False),
                data.get("affected_areas_scope", ""),
                data.get("affected_rooms_count", 0),
                data.get("leak_stopped", False),
                data.get("leak_timeline", ""),
                data.get("has_insurance", False),
                data.get("call_summary", "")
            ]
        ]
        
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"Row successfully appended. Updates: {result.get('updates')}")
        return True
        
    except Exception as e:
        print(f"Error appending directly to Google Sheets: {e}")
        # Self-healing fallback: Write to local failure log per Layer 1 rule
        log_failure(data, str(e))
        return False

def log_failure(data: dict, error_message: str):
    """Fallback: Logs the unwritten JSON locally into .tmp/sheets_failures.json to prevent data loss."""
    import json
    from datetime import datetime
    
    os.makedirs('.tmp', exist_ok=True)
    failure_file = '.tmp/sheets_failures.json'
    
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "error": error_message,
        "data": data
    }
    
    print(f"Logging failure to {failure_file}")
    
    if os.path.exists(failure_file):
        with open(failure_file, 'r') as f:
            try:
                failures = json.load(f)
            except json.JSONDecodeError:
                failures = []
    else:
        failures = []
        
    failures.append(payload)
    
    with open(failure_file, 'w') as f:
        json.dump(failures, f, indent=2)

if __name__ == "__main__":
    print("Layer 3: execution/sheets_appender module loaded.")
