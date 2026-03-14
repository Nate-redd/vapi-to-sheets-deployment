import urllib.request
import json
import os

render_key = "rnd_3zx5yXfi1j7gT4etv5ieoqte5U7S"
service_id = "srv-d6g44i75r7bs73f8jiq0"
url = f"https://api.render.com/v1/services/{service_id}/logs?limit=50"

req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {render_key}",
    "Accept": "application/json"
})

try:
    with urllib.request.urlopen(req) as response:
        logs = json.loads(response.read().decode())
        for log in logs:
             print(log.get("message", "").strip())
except Exception as e:
    print(f"Error fetching logs: {e}")
