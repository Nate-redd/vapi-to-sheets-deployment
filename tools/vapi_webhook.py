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
    affected_rooms_count: int | None = None
    leak_stopped: bool | None = None
    leak_timeline: str | None = None
    has_insurance: bool | None = None
    call_summary: str | None = None

    model_config = ConfigDict(extra='ignore')


def format_us_phone(raw: str) -> str:
    """Formats a raw phone string into US format: (XXX) XXX-XXXX"""
    digits = re.sub(r'\D', '', raw)
    # Strip leading country code 1
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    # Return cleaned digits if we can't format
    return raw


def fetch_call_from_vapi(call_id: str) -> dict:
    """Fetches the full call object from the VAPI API, retrying until structuredOutputs are ready."""
    vapi_key = os.getenv("VAPI_SECRET_TOKEN")
    url = f"https://api.vapi.ai/call/{call_id}"

    # VAPI's structuredOutputs analysis runs after the call ends.
    # The webhook fires immediately, but the analysis takes 5-15 seconds.
    # We retry up to 3 times with a 5-second delay to wait for it.
    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {vapi_key}")
            with urllib.request.urlopen(req, timeout=10) as res:
                call_obj = json.loads(res.read().decode())

            # Check if structuredOutputs are populated
            analysis = call_obj.get("analysis", {})
            structured_outputs = analysis.get("structuredOutputs", {})
            if structured_outputs and isinstance(structured_outputs, dict):
                first_key = list(structured_outputs.keys())[0]
                result = structured_outputs[first_key].get("result", {})
                if result:
                    print(f"[Attempt {attempt+1}] Got structuredOutputs from VAPI API")
                    return call_obj

            print(f"[Attempt {attempt+1}] structuredOutputs not ready yet, waiting 5s...")
            time.sleep(5)

        except Exception as e:
            print(f"[Attempt {attempt+1}] VAPI API fetch failed: {e}")
            time.sleep(3)

    # Return whatever we got on last attempt
    print("All retries exhausted. Returning last fetched call object.")
    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {vapi_key}")
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode())
    except:
        return {}


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Healthcheck endpoint for Render and Keep-Alive pings."""
    return {"status": "ok", "service": "VAPI Webhook Endpoint"}


@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request, api_key: str = Security(get_api_key)):
    """Receives the end-of-call-report webhook from VAPI."""
    try:
        payload = await request.json()

        # Only process end-of-call-report
        message_type = payload.get("message", {}).get("type")
        if message_type != "end-of-call-report":
            return {"status": "ignored", "reason": "Not an end-of-call-report"}

        # Get the call ID - this is the key to everything
        call_id = payload.get("message", {}).get("call", {}).get("id")
        if not call_id:
            print("ERROR: No call ID found in webhook payload")
            return {"status": "error", "message": "No call ID in payload"}

        # Grab the customer phone number from the webhook payload immediately
        customer_number = payload.get("message", {}).get("call", {}).get("customer", {}).get("number")

        # Fetch the COMPLETE call object from VAPI API with retry
        # This solves the race condition where the webhook fires before analysis finishes
        call_obj = fetch_call_from_vapi(call_id)

        # Extract structured data from the API response
        structured_data = {}
        analysis = call_obj.get("analysis", {})

        # Try structuredOutputs first (new format)
        structured_outputs = analysis.get("structuredOutputs", {})
        if structured_outputs and isinstance(structured_outputs, dict):
            for key in structured_outputs:
                result = structured_outputs[key].get("result", {})
                if result:
                    structured_data = result
                    break

        # Fallback to legacy structuredData
        if not structured_data:
            structured_data = analysis.get("structuredData", {})

        print(f"Extracted Structured Data: {structured_data}")

        # Phone number override: always use the telecom caller ID if LLM failed
        phone_val = str(structured_data.get("phone_number", ""))
        phone_lower = phone_val.lower()
        if not phone_val or "unknown" in phone_lower or "caller" in phone_lower or len(phone_val) < 7:
            # Use the number from the webhook payload or from the API call object
            if not customer_number:
                customer_number = call_obj.get("customer", {}).get("number")
            if customer_number:
                structured_data["phone_number"] = customer_number

        # Format the phone number as US standard
        if structured_data.get("phone_number"):
            structured_data["phone_number"] = format_us_phone(structured_data["phone_number"])

        # Parse into our deterministic Pydantic model
        validated_data = VAPICallData(**structured_data).model_dump()

        # Route to Google Sheets
        success = append_to_sheet(validated_data)

        if success:
            return {"status": "success", "message": "Row appended to Google Sheets."}
        else:
            return {"status": "partial_failure", "message": "Failed to write to sheets, data logged locally."}

    except Exception as e:
        print(f"CRITICAL WEBHOOK ERROR: {e}")
        return {"status": "error", "message": "Webhook crashed but intercepted gracefully.", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("vapi_webhook:app", host="0.0.0.0", port=port, reload=False)
