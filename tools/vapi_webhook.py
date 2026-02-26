import os
from typing import Any, Dict
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

# Layer 3 Execution Tools
from tools.sheets_appender import append_to_sheet

load_dotenv()

app = FastAPI(title="VAPI to Sheets Webhook")

# API Key Validation (Optional but recommended)
api_key_header = APIKeyHeader(name="X-Vapi-Secret", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    vapi_secret = os.getenv("VAPI_SECRET_TOKEN")
    if vapi_secret and api_key_header != vapi_secret:
        # If a secret is defined in .env and the incoming header doesn't match, reject.
        raise HTTPException(
            status_code=401, detail="Invalid X-Vapi-Secret Header"
        )
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

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Healthcheck endpoint for Render and Keep-Alive pings. Accepts HEAD for UptimeRobot."""
    return {"status": "ok", "service": "VAPI Webhook Endpoint"}

@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request, api_key: str = Security(get_api_key)):
    """Receives the end-of-call-report webhook from VAPI."""
    try:
        payload = await request.json()
        
        # Validate that this is the end-of-call report
        message_type = payload.get("message", {}).get("type")
        
        if message_type != "end-of-call-report":
             return {"status": "ignored", "reason": "Not an end-of-call-report"}

        # 1. Try legacy structuredData (Deprecated)
        analysis = payload.get("message", {}).get("analysis", {})
        if not analysis:
             analysis = payload.get("message", {}).get("call", {}).get("analysis", {})
             
        structured_data = analysis.get("structuredData", {})
        
        # 2. Try new structuredOutputs dictionary
        if not structured_data:
            structured_outputs = analysis.get("structuredOutputs", {})
            if structured_outputs and isinstance(structured_outputs, dict):
                 if len(structured_outputs.keys()) > 0:
                     first_key = list(structured_outputs.keys())[0]
                     structured_data = structured_outputs[first_key].get("result", {})

        print(f"Extracted Structured Data: {structured_data}")

        if not structured_data:
            print("Warning: No structuredData or structuredOutputs found in the VAPI end-of-call payload.")
        
        # Override Phone Number if LLM couldn't extract it
        phone_val = str(structured_data.get("phone_number", ""))
        phone_val_lower = phone_val.lower()
        
        if not phone_val or "unknown" in phone_val_lower or "caller" in phone_val_lower or len(phone_val) < 7:
            customer_number = payload.get("message", {}).get("call", {}).get("customer", {}).get("number")
            if not customer_number:
                customer_number = payload.get("message", {}).get("customer", {}).get("number")
                
            # Forcibly retrieve true telecom Caller ID from VAPI API
            if not customer_number:
                call_id = payload.get("message", {}).get("call", {}).get("id")
                if call_id:
                    try:
                        import urllib.request
                        vapi_key = os.getenv("VAPI_SECRET_TOKEN")
                        req = urllib.request.Request(f"https://api.vapi.ai/call/{call_id}")
                        req.add_header("Authorization", f"Bearer {vapi_key}")
                        # Adding timeout to prevent webhook hanging
                        with urllib.request.urlopen(req, timeout=5) as res:
                            call_obj = json.loads(res.read().decode())
                            customer_number = call_obj.get("customer", {}).get("number")
                    except Exception as e:
                        print(f"Failed forceful telecom override: {e}")
                        
            if customer_number:
                print(f"Fallback to true caller ID: {customer_number}")
                structured_data["phone_number"] = customer_number

        # Parse into our deterministic Pydantic model
        validated_data = VAPICallData(**structured_data).model_dump()
        
        # Route via Orchestration to Execution Tool
        success = append_to_sheet(validated_data)
        
        if success:
             return {"status": "success", "message": "Row appended to Google Sheets."}
        else:
             return {"status": "partial_failure", "message": "Failed to write to sheets, data logged locally."}

    except Exception as e:
        print(f"CRITICAL WEBHOOK ERROR: {e}")
        # We STILL return 200 OK so VAPI doesn't get confused and freeze the agent
        return {"status": "error", "message": "Webhook crashed but intercepted gracefully.", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Make sure to bind to 0.0.0.0 and dynamically grab the PORT env var for Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("vapi_webhook:app", host="0.0.0.0", port=port, reload=False)
