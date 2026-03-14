import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

# We need to import the get_sheets_service from the tool
import sys
sys.path.append(os.getcwd())
from tools.sheets_appender import get_sheets_service

load_dotenv()

spreadsheet_id = os.getenv("SPREADSHEET_ID")
range_name = os.getenv("SHEET_NAME", "Sheet1") + "!A1:K1"

service = get_sheets_service()

headers = [
    [
        "First Name",
        "Last Name",
        "Phone Number",
        "Zip Code",
        "Standing Water?",
        "Affected Areas",
        "Rooms Affected",
        "Leak Stopped?",
        "Leak Timeline",
        "Has Insurance?",
        "Call Summary"
    ]
]

body = {
    'values': headers
}

try:
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print("Headers successfully written to row 1.")
    
    # Let's also freeze the top row and bold it using batchUpdate
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 11
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        "textFormat": {
                            "bold": True
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": 0,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        }
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()
    print("Headers formatted styling.")
    
except Exception as e:
    print(f"Failed to write headers: {e}")
