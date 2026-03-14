import os
import urllib.request
import urllib.parse
import json
from dotenv import load_dotenv

load_dotenv()

def format_telegram_message(data: dict) -> str:
    """
    Formats the JSON data payload into a robust HTML structure for Telegram.
    This avoids the brittleness of Markdown with underscores and special characters.
    """
    
    first_name = data.get("caller_first_name") or ""
    last_name = data.get("caller_last_name") or ""
    name_str = f"{first_name} {last_name}".strip() if (first_name or last_name) else "Unknown"

    phone = data.get("phone_number") or "Unknown"
    zip_code = data.get("zip_code") or "Unknown"
    affected_area = data.get("affected_areas_scope") or "Unknown"
    rooms = str(data.get("affected_rooms_count") or 0)
    water = "Yes" if data.get("standing_or_leaking_water") else "No"
    insurance = "Yes" if data.get("has_insurance") else "No"
    leak_timeline = data.get("leak_timeline") or "Unknown"
    leak_stopped = "Yes" if data.get("leak_stopped") else "No"
    summary = data.get("call_summary") or "No summary provided."
    recording_url = data.get("recording_url") or "No URL available"

    # HTML structure
    message = f"""🚨 <b>NEW HOT LEAD!</b> 🚨

<b>Name:</b> {name_str}
<b>Phone:</b> {phone}
<b>ZIP code:</b> {zip_code}
<b>Affected Area:</b> {affected_area}
<b>Rooms:</b> {rooms}
<b>Standing Water:</b> {water}
<b>Insurance claim:</b> {insurance}
<b>Leak age:</b> {leak_timeline}
<b>Leak stopped:</b> {leak_stopped}
<b>Call Recording link:</b> 
{recording_url}

<b>Call Summary:</b> {summary}

☎️ <b>CALL THEM NOW!</b>
"""
    return message

def send_telegram_alert(data: dict) -> bool:
    """
    Sends the formatted message to the Telegram Chat IDs specified in the environment.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids_str = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_ids_str:
        print("Telegram bot token or chat ID is missing from .env. Skipping alert.")
        return False
        
    chat_ids = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]
    message = format_telegram_message(data)
    
    success = True
    for chat_id in chat_ids:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req, timeout=10) as res:
                response_data = json.loads(res.read().decode())
                if not response_data.get("ok"):
                    print(f"Telegram API warning for chat {chat_id}: {response_data}")
                    success = False
                else:
                    print(f"Successfully sent Telegram alert to {chat_id}")
                    
        except Exception as e:
            print(f"Failed to send Telegram alert to {chat_id}: {e}")
            success = False
            
    return success

if __name__ == "__main__":
    print("Layer 3: execution/telegram_notifier module loaded.")
