import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_KEY = os.getenv("VAPI_SECRET_TOKEN")
AGENT_ID = os.getenv("VAPI_ASSISTANT_ID") or "769da4c0-fa1e-45fe-af17-6455abcc1308"

URL = f"https://api.vapi.ai/assistant/{AGENT_ID}"

# Load the full config
config_path = os.path.join(os.path.dirname(__file__), "vapi_agent_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Remove read-only/unnecessary fields that VAPI might reject in a PATCH
keys_to_remove = ["id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet"]
for key in keys_to_remove:
    if key in config:
        del config[key]

# Ensure the model provider is set correctly (as discovered in previous 400 error)
if "model" in config:
    if "messages" in config["model"]:
        # We already updated the system prompt in the JSON file in the previous step
        pass

headers = {
    "Authorization": f"Bearer {VAPI_KEY}",
    "Content-Type": "application/json"
}

try:
    print(f"Pushing full configuration to Agent {AGENT_ID}...")
    response = requests.patch(URL, headers=headers, json=config)
    
    if response.status_code == 200:
        print("Assistant updated successfully with full configuration.")
    else:
        print(f"Failed with status {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"An error occurred: {e}")
