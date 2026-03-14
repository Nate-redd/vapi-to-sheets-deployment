import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_KEY = os.getenv("VAPI_SECRET_TOKEN")
URL = "https://api.vapi.ai/structured-output"

payload = {
    "name": "water_restoration_data",
    "description": "Information collected from a water damage lead.",
    "schema": {
        "type": "object",
        "properties": {
            "caller_first_name": {"type": "string"},
            "caller_last_name": {"type": "string"},
            "phone_number": {"type": "string"},
            "zip_code": {"type": "string"},
            "standing_or_leaking_water": {"type": "boolean"},
            "affected_areas_scope": {"type": "string"},
            "affected_rooms_count": {"type": "integer"},
            "leak_stopped": {"type": "boolean"},
            "leak_timeline": {"type": "string"},
            "has_insurance": {"type": "boolean"},
            "call_summary": {"type": "string"}
        }
    }
}

headers = {
    "Authorization": f"Bearer {VAPI_KEY}",
    "Content-Type": "application/json"
}

try:
    print("Creating Structured Output...")
    response = requests.post(URL, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code in [200, 201]:
        res = response.json()
        new_id = res['id']
        print(f"SUCCESS! New ID: {new_id}")
        with open("structured_output_id.txt", "w") as f:
            f.write(new_id)
except Exception as e:
    print(f"An error occurred: {e}")
