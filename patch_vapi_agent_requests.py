import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_KEY = os.getenv("VAPI_SECRET_TOKEN")
AGENT_ID = os.getenv("VAPI_ASSISTANT_ID") or "769da4c0-fa1e-45fe-af17-6455abcc1308"

URL = f"https://api.vapi.ai/assistant/{AGENT_ID}"

prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read()

payload = {
    "model": {
        "provider": "openai",
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
    }
}

headers = {
    "Authorization": f"Bearer {VAPI_KEY}",
    "Content-Type": "application/json"
}

try:
    print(f"Patching Agent {AGENT_ID} via Requests...")
    response = requests.patch(URL, headers=headers, json=payload)
    if response.status_code == 200:
        print("Agent patched successfully.")
        res = response.json()
        if "model" in res and "messages" in res["model"]:
            content = res["model"]["messages"][0]["content"]
            print(f"Updated System Prompt (First 100 chars):\n{content[:100]}...")
    else:
        print(f"Failed with status {response.status_code}: {response.text}")
except Exception as e:
    print(f"An error occurred: {e}")
