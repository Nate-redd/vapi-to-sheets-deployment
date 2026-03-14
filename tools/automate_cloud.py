import os
import json
import urllib.request
import urllib.error
import subprocess
from dotenv import load_dotenv

load_dotenv()

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
GITHUB_PAT = os.getenv("GITHUB_PAT")
REPO_URL = "https://github.com/Nate-redd/vapi-to-sheets-deployment"
NEW_SERVICE_NAME = "adib-workflow"
OLD_SERVICE_NAME = "vapi-to-sheets"

def rename_render_service():
    print(f"--- Renaming Render Service to '{NEW_SERVICE_NAME}' ---")
    
    # 1. Find the service ID for the old name
    list_url = "https://api.render.com/v1/services"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(list_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            services = json.loads(response.read().decode())
            
        service_id = None
        for s in services:
            if s['service']['name'] == OLD_SERVICE_NAME:
                service_id = s['service']['id']
                break
        
        if not service_id:
            # Check if it's already renamed
            for s in services:
                if s['service']['name'] == NEW_SERVICE_NAME:
                    print(f"Service '{NEW_SERVICE_NAME}' already exists (ID: {s['service']['id']}). Skipping rename.")
                    return s['service']['id']
            print(f"Error: Could not find service with name '{OLD_SERVICE_NAME}'")
            return None

        print(f"Found Service ID: {service_id}")

        # 2. PATCH the service name
        patch_url = f"https://api.render.com/v1/services/{service_id}"
        payload = {"name": NEW_SERVICE_NAME}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(patch_url, data=data, headers=headers, method="PATCH")
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"Successfully renamed service to: {result['name']}")
            return service_id

    except Exception as e:
        print(f"Render Rename Error: {e}")
        return None

def push_to_github():
    print("\n--- Pushing Code to GitHub via PAT ---")
    if not GITHUB_PAT:
        print("Error: GITHUB_PAT not found in .env")
        return False

    # Construct authenticated URL
    # Format: https://<token>@github.com/<user>/<repo>.git
    auth_url = REPO_URL.replace("https://", f"https://{GITHUB_PAT}@")
    if not auth_url.endswith(".git"):
        auth_url += ".git"

    try:
        # Update remote URL
        subprocess.run(["git", "remote", "set-url", "origin", auth_url], check=True)
        
        # Push
        print("Running 'git push origin main'...")
        result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully pushed to GitHub!")
            return True
        else:
            print(f"Git Push Failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"GitHub Push Error: {e}")
        return False

if __name__ == "__main__":
    s_id = rename_render_service()
    if s_id:
        if push_to_github():
            print("\n✅ CLOUD AUTOMATION COMPLETE!")
            print(f"Your service should be live at: https://{NEW_SERVICE_NAME}.onrender.com")
        else:
            print("\n❌ GitHub Push Failed.")
    else:
        print("\n❌ Render Rename Failed.")
