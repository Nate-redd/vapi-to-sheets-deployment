import sys
import os

from tools.sheets_appender import append_to_sheet

data = {
    "zip_code": "78312",
    "call_summary": "Test Caller Jonathan John has an active leak.",
    "leak_stopped": False,
    "phone_number": "CALLER_ID_NUMBER",
    "has_insurance": False,
    "leak_timeline": "Started about 3 days ago, still ongoing.",
    "caller_last_name": "John",
    "caller_first_name": "Jonathan",
    "affected_areas_scope": "Bathroom ceiling and walls are wet.",
    "affected_rooms_count": 1,
    "standing_or_leaking_water": True
}

print("Attempting to append data...")
success = append_to_sheet(data)
print(f"Result: {success}")
