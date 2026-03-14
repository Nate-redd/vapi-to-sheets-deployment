import time
import urllib.request
import urllib.error

# The Render URL for your deployment
TARGET_URL = "https://vapi-to-sheets.onrender.com/"
PING_INTERVAL_SECONDS = 10 * 60  # Ping every 10 minutes

def ping_server():
    """Pings the root healthcheck endpoint to keep the Render server alive."""
    try:
        req = urllib.request.Request(TARGET_URL, headers={"User-Agent": "Antigravity-KeepAlive/1.0"})
        with urllib.request.urlopen(req) as response:
            res = response.read().decode()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server pinged successfully. Status: {response.status}")
    except urllib.error.URLError as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to ping server: {e}")

if __name__ == "__main__":
    print(f"Starting Keep-Alive worker for {TARGET_URL}. Pinging every 10 minutes.")
    while True:
        ping_server()
        time.sleep(PING_INTERVAL_SECONDS)
