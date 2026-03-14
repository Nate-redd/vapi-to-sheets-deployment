import os
import json
import urllib.request
import urllib.error

# Load credentials
with open("credentials.json", "r") as f:
    creds = f.read()

# Setup Render API Payload
render_api_key = os.getenv("RENDER_API_KEY")
url = "https://api.render.com/v1/services"

# Find owner ID first
req = urllib.request.Request("https://api.render.com/v1/owners", headers={
    "Authorization": f"Bearer {render_api_key}",
    "Accept": "application/json"
})
owner_id = None
try:
    with urllib.request.urlopen(req) as response:
        owners = json.loads(response.read().decode())
        if owners:
            owner_id = owners[0]["owner"]["id"]
            print(f"Found owner ID: {owner_id}")
        else:
            print("No owners found for this API key.")
except urllib.error.HTTPError as e:
    print(f"Owner Fetch HTTP Error: {e.code} {e.read().decode()}")
except Exception as e:
     print("Error getting owner id:", e)
     
payload = {
    "type": "web_service",
    "name": "adib-workflow",
    "ownerId": owner_id,
    "repo": "https://github.com/Nate-redd/vapi-to-sheets-deployment",
    "branch": "main",
    "region": "oregon",
    "plan": "free",
    "serviceDetails": {
        "env": "python",
        "envSpecificDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "uvicorn tools.vapi_webhook:app --host 0.0.0.0 --port $PORT"
        }
    },
    "envVars": [
        {"key": "VAPI_SECRET_TOKEN", "value": "89370afc-41a0-4dc8-b8ac-7e546485fb55"},
        {"key": "SPREADSHEET_ID", "value": "1p1_3VsS62YrFAtQwebBy55Gs1aGngabKT_wuSbOovzE"},
        {"key": "SHEET_NAME", "value": "Sheet1"},
        {"key": "GOOGLE_CREDENTIALS", "value": creds.strip()}
    ]
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={
    "Authorization": f"Bearer {render_api_key}",
    "Accept": "application/json",
    "Content-Type": "application/json"
})

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        print("Successfully deployed to Render!")
        print(json.dumps(res, indent=2))
        
        # Save output to read the URL
        with open("render_deploy_output.json", "w") as f:
             json.dump(res, f, indent=2)
except urllib.error.HTTPError as e:
    err_body = e.read().decode()
    print(f"HTTP Return Code: {e.code}")
    print(f"Error Body: {err_body}")
except Exception as e:
    print("Unexpected Error:", e)
