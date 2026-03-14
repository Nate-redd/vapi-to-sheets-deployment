import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
VAPI_KEY = os.getenv("VAPI_SECRET_TOKEN")
# Note: VAPI_ASSISTANT_ID was added to .env in a previous step
AGENT_ID = os.getenv("VAPI_ASSISTANT_ID") or "769da4c0-fa1e-45fe-af17-6455abcc1308"

URL = f"https://api.vapi.ai/assistant/{AGENT_ID}"

# Read the extracted system prompt
prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read()

payload = {
    "model": {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
    }
}

req = urllib.request.Request(URL, method="PATCH")
req.add_header("Authorization", f"Bearer {VAPI_KEY}")
req.add_header("Content-Type", "application/json")

try:
    print(f"Patching Agent {AGENT_ID}...")
    with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8")) as response:
        print("Agent patched successfully.")
        res = json.loads(response.read().decode("utf-8"))
        # Print a snippet of the updated message to verify
        if "model" in res and "messages" in res["model"]:
            content = res["model"]["messages"][0]["content"]
            print(f"Updated System Prompt (First 100 chars):\n{content[:100]}...")
except Exception as e:
    print(f"Failed to patch agent: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode())
