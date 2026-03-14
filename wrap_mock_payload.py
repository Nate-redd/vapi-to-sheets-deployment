import json
import os

with open(".tmp/test_call_json.json", "r") as f:
    raw_call = json.load(f)

# VAPI webhooks wrap the call object in a message structure
webhook_payload = {
    "message": {
        "type": "end-of-call-report",
        "call": raw_call,
        "artifact": {
            "structuredOutputs": [
                {
                    "result": raw_call.get("structuredOutputs", {}).get("36a835d1-c09a-4001-91c9-650cf4898f4e", {}).get("result", {})
                }
            ]
        }
    }
}

with open(".tmp/test_webhook_payload.json", "w") as f:
    json.dump(webhook_payload, f, indent=2)
