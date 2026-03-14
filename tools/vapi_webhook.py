import os
import json
import time
import urllib.request
import re
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

# Layer 3 Execution Tools
from tools.sheets_appender import append_to_sheet
from tools.telegram_notifier import send_telegram_alert

load_dotenv()

app = FastAPI(title="VAPI to Sheets Webhook")

# API Key Validation
api_key_header = APIKeyHeader(name="X-Vapi-Secret", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    vapi_secret = os.getenv("VAPI_SECRET_TOKEN")
    if vapi_secret and api_key_header != vapi_secret:
        raise HTTPException(status_code=401, detail="Invalid X-Vapi-Secret Header")
    return api_key_header

# Pydantic Schema mapping exactly to our GEMINI.md Constitution
class VAPICallData(BaseModel):
    caller_first_name: str | None = None
    caller_last_name: str | None = None
    phone_number: str | None = None
    zip_code: str | None = None
    standing_or_leaking_water: bool | None = None
    affected_areas_scope: str | None = None
    affected_rooms_count: int | str | None = None
    leak_stopped: bool | None = None
    leak_timeline: str | None = None
    has_insurance: bool | None = None
    call_summary: str | None = None
    recording_url: str | None = None

    model_config = ConfigDict(extra='ignore')


def format_us_phone(raw: str) -> str:
    """Formats a raw phone string into US format: (XXX) XXX-XXXX"""
    if not raw:
        return ""
    digits = re.sub(r'\D', '', str(raw))
    # Strip leading country code 1
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


def fetch_call_from_vapi(call_id: str) -> dict:
    """Fetches the full call object from the VAPI API, retrying until structuredOutputs are ready."""
    vapi_key = os.getenv("VAPI_SECRET_TOKEN")
    url = f"https://api.vapi.ai/call/{call_id}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {vapi_key}")
            with urllib.request.urlopen(req, timeout=10) as res:
                call_obj = json.loads(res.read().decode())

            analysis = call_obj.get("analysis", {})
            structured_outputs = analysis.get("structuredOutputs", {})
            if structured_outputs and isinstance(structured_outputs, dict):
                for key in structured_outputs:
                    if structured_outputs[key].get("result"):
                        print(f"[Attempt {attempt+1}] Got structuredOutputs from VAPI API")
                        return call_obj

            print(f"[Attempt {attempt+1}] structuredOutputs not ready yet, waiting 5s...")
            time.sleep(5)

        except Exception as e:
            print(f"[Attempt {attempt+1}] VAPI API fetch failed: {e}")
            time.sleep(3)

    print("All retries exhausted.")
    return {}


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Healthcheck endpoint for Render and Keep-Alive pings."""
    return {"status": "ok", "service": "VAPI Webhook Endpoint"}


@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request, api_key: str = Security(get_api_key)):
    """Receives the end-of-call-report webhook from VAPI."""
    try:
        raw_payload = await request.json()
        
        # Handle case where payload is a list (n8n execution format)
        if isinstance(raw_payload, list) and len(raw_payload) > 0:
            payload = raw_payload[0].get("body", raw_payload[0])
        else:
            payload = raw_payload

        message = payload.get("message", {})
        message_type = message.get("type")
        
        if message_type != "end-of-call-report":
            return {"status": "ignored", "reason": f"Type {message_type} is not end-of-call-report"}

        # Robust extraction of call data from payload
        artifact = message.get("artifact", {})
        # VAPI puts 'call' at the root of 'message', but the user payload has it in 'artifact'
        call = message.get("call") or artifact.get("call") or {}
        call_id = call.get("id")
        
        if not call_id:
            print("ERROR: No call ID found in webhook payload")
            return {"status": "error", "message": "No call ID in payload"}

        # Get customer number as early as possible
        customer_number = call.get("customer", {}).get("number")
        if not customer_number:
            customer_number = message.get("customer", {}).get("number")

        # Fetch full object from API
        call_obj = fetch_call_from_vapi(call_id)
        
        # Determine which analysis object to use
        if call_obj:
            analysis_source = call_obj.get("analysis", {})
            # Also check artifact in call_obj
            if not analysis_source.get("structuredOutputs"):
                analysis_source = call_obj.get("artifact", {})
        else:
            # Fallback to payload's artifact/analysis
            analysis_source = artifact if artifact.get("structuredOutputs") else message.get("analysis", {})

        # Extract structured data
        structured_data = {}
        structured_outputs = analysis_source.get("structuredOutputs", {})
        if structured_outputs and isinstance(structured_outputs, dict):
            for key in structured_outputs:
                result = structured_outputs[key].get("result", {})
                if result:
                    structured_data = result
                    break

        if not structured_data:
            structured_data = analysis_source.get("structuredData", {})

        # Merge in recording URL
        recording_url = artifact.get("recordingUrl") or call_obj.get("recordingUrl")
        if recording_url:
            structured_data["recording_url"] = recording_url

        # Phone number reconciliation
        phone_val = str(structured_data.get("phone_number", ""))
        if not phone_val or any(x in phone_val.lower() for x in ["unknown", "caller", "null", "none"]):
            if customer_number:
                structured_data["phone_number"] = customer_number
        
        # Ensure rooms count is an integer if possible
        rooms = structured_data.get("affected_rooms_count")
        if rooms and isinstance(rooms, str) and rooms.isdigit():
            structured_data["affected_rooms_count"] = int(rooms)

        # Format Final Phone
        if structured_data.get("phone_number"):
            structured_data["phone_number"] = format_us_phone(structured_data["phone_number"])

        # Parse and Send
        validated_data = VAPICallData(**structured_data).model_dump()
        print(f"Final Data for Output: {json.dumps(validated_data, indent=2)}")

        sheets_success = append_to_sheet(validated_data)
        telegram_success = send_telegram_alert(validated_data)

        if sheets_success and telegram_success:
            return {"status": "success", "message": "Row appended to Google Sheets and Telegram alert sent."}
        else:
            return {"status": "partial_failure", "message": "Failed to write to one or more systems. Check logs."}

    except Exception as e:
        print(f"CRITICAL WEBHOOK ERROR: {e}")
        return {"status": "error", "message": "Webhook crashed but intercepted gracefully.", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("vapi_webhook:app", host="0.0.0.0", port=port, reload=False)
