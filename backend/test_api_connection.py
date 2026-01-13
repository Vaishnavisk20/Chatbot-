import os
import requests
import hashlib
import time
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Config
API_URL = os.getenv("EMUDHRA_API_URL")
CLIENT_KEY = os.getenv("CLIENT_ACCESS_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE", "emudhra")

print(f"🔹 Testing Connection to: {API_URL}")

# 3. Helper to generate Hash
def get_headers():
    now_utc = datetime.now(timezone.utc)
    ts = (now_utc + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
    txn = f"TXN{int(time.time() * 1000)}"
    
    raw_str = f"{CLIENT_KEY}{ts}{txn}"
    auth_hash = hashlib.sha256(raw_str.encode()).hexdigest()
    
    return ts, txn, auth_hash

# 4. Input Mobile Number
mobile = input("Enter Mobile Number to test: ")

# 5. Prepare Payload
ts, txn, auth_hash = get_headers()
payload = {
    "meta": {
        "ver": "1.0", 
        "ts": ts, 
        "txn": txn, 
        "clientCode": CLIENT_CODE, 
        "clientAccessKey": auth_hash
    },
    "details": {
        "mobileNo": mobile, 
        "isPIIMasked": "1"
    }
}

# 6. Make Request
try:
    print("⏳ Sending request...")
    url = f"{API_URL}/CustomerCareAPI/getApplicationDetails"
    
    # Verify=False to bypass SSL errors on internal servers
    resp = requests.post(url, json=payload, verify=False, timeout=10)
    
    print(f"✅ Status Code: {resp.status_code}")
    print("👇 RESPONSE BODY:")
    print(resp.text)
    
    # Try parsing JSON
    data = resp.json()
    meta_status = data.get("meta", {}).get("status")
    print(f"\n📊 Meta Status: {meta_status} (1 = Success, 0 = Fail)")

except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")