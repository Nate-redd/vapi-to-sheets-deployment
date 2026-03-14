import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
VAPI_KEY = os.getenv("VAPI_SECRET_TOKEN")
AGENT_ID = os.getenv("VAPI_ASSISTANT_ID") or "769da4c0-fa1e-45fe-af17-6455abcc1308"

URL = f"https://api.vapi.ai/assistant/{AGENT_ID}"

# Read the full configuration JSON
config_path = os.path.join(os.path.dirname(__file__), "vapi_agent_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config_data = json.load(f)

# Only remove fields that are usually read-only or could cause mismatch during a PATCH
# In many VAPI versions, 'id', 'orgId', 'createdAt', 'updatedAt' should not be sent in a PATCH
fields_to_remove = ["id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet"]
for field in fields_to_remove:
    config_data.pop(field, None)

req = urllib.request.Request(URL, method="PATCH")
req.add_header("Authorization", f"Bearer {VAPI_KEY}")
req.add_header("Content-Type", "application/json")
# Cloudflare/WAF often require a User-Agent to avoid 403 Forbidden
req.add_header("User-Agent", "Mozilla/5.0")

try:
    print(f"Patching Agent {AGENT_ID} with full config...")
    payload_bytes = json.dumps(config_data).encode("utf-8")
    with urllib.request.urlopen(req, data=payload_bytes) as response:
        print("Agent patched successfully.")
        res = json.loads(response.read().decode("utf-8"))
        print(f"Updated Assistant Name: {res.get('name')}")
except urllib.error.HTTPError as e:
    print(f"Failed to patch agent: {e}")
    body = e.read().decode()
    try:
        error_json = json.loads(body)
        print(json.dumps(error_json, indent=2))
    except:
        print(body)
except Exception as e:
    print(f"An error occurred: {e}")
