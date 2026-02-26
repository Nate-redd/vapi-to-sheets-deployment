# SOP: VAPI to Google Sheets Integration

## Goal
To predictably, securely, and deterministically persist collected caller data from VAPI voice interactions into a Google Sheet.

## Inputs
- **VAPI Webhook Payload (JSON):** Specifically, the `end-of-call-report` from VAPI's `structuredDataPlan` feature.

## Outputs
- **Google Sheets Row appended:** With the 11 schema attributes requested by the user.

## Edge Cases & Error Handling
- **API Errors/Failures:** If Google Sheets API rejects the write (e.g., token expired, rate limit), the Python application MUST catch this and append the JSON payload to `.tmp/sheets_failures.json`.
- **Missing Data:** If VAPI passes non-existent data, default to an empty string. VAPI `structuredDataPlan` schema handles ensuring all values are extracted, but the Python logic must be resilient to `None` values.

## Architectural Flow
1. **User Call Ends:** VAPI concludes the emergency call based on the finalized `structuredDataPlan`.
2. **Webhook Fired:** VAPI fires the `end-of-call-report` containing the JSON payload.
3. **`tools/vapi_webhook.py` Receives:** A lightweight FastAPI server validates the schema signature and passes it to the module `sheets_appender`.
4. **`tools/sheets_appender.py` Appends:** Standard `google-api-python-client` logic dynamically binds to the `.env` `SPREADSHEET_ID` and appends a row to the next available block via the `append` strategy.
