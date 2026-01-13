import os
import time
import hashlib
import requests
import json
import config 
from logger_config import get_logger # Import Logger
from datetime import datetime, timedelta, timezone

logger = get_logger(__name__)

def get_ist_timestamp():
    """Get IST time string YYYY-MM-DDTHH:mm:ss"""
    now_utc = datetime.now(timezone.utc)
    ist_time = now_utc + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%Y-%m-%dT%H:%M:%S")

def send_otp(mobile: str):
    """
    Sends OTP via eMudhra Internal API.
    """
    ts = get_ist_timestamp()
    txn = f"TXN{int(time.time() * 1000)}"
    client_key = config.CLIENT_ACCESS_KEY
    
    raw_str = f"{client_key}{ts}{txn}"
    auth_hash = hashlib.sha256(raw_str.encode()).hexdigest()
    
    payload = {
        "meta": {
            "ver": "1.0",
            "ts": ts,
            "txn": txn,
            "clientCode": config.CLIENT_CODE,
            "clientAccessKey": auth_hash
        },
        "userdetails": {
            "mobileno": mobile
        }
    }
    
    api_url = f"{config.EMUDHRA_API_URL}/CustomerCareAPI/GetMobileOtp"
    
    logger.info(f"🚀 Sending OTP to {mobile}...")

    try:
        resp = requests.post(api_url, json=payload, verify=False, timeout=10)
        data = resp.json()
        logger.info(f"📩 API Response: {data}")

        api_session_id = None
        if 'session_info' in data and 'session_id' in data['session_info']:
            api_session_id = data['session_info']['session_id']
        elif 'session_id' in data:
            api_session_id = data['session_id']
        elif 'sessionId' in data:
            api_session_id = data['sessionId']
            
        status_success = False
        if 'response' in data and str(data['response'].get('status')) == '1':
            status_success = True

        if api_session_id or (status_success and 'errorMessage' not in data):
            return True, "OTP Sent Successfully", api_session_id
        else:
            err_msg = data.get('errorMessage', 'Unknown API Error')
            return False, f"API Error: {err_msg}", None

    except Exception as e:
        logger.error(f"❌ Network Error: {e}")
        return False, f"Connection Failed: {str(e)}", None

def verify_otp(mobile: str, otp: str, api_session_id: str):
    """
    Verifies OTP using the api_session_id stored in DB.
    """
    if not api_session_id:
        return False, "Session expired. Please request OTP again."

    ts = get_ist_timestamp()
    txn = f"TXN{int(time.time() * 1000)}"
    client_key = config.CLIENT_ACCESS_KEY
    
    raw_str = f"{client_key}{ts}{txn}"
    auth_hash = hashlib.sha256(raw_str.encode()).hexdigest()

    payload = {
        "meta": {
            "ver": "1.0",
            "ts": ts,
            "txn": txn,
            "clientCode": config.CLIENT_CODE,
            "clientAccessKey": auth_hash,
            "sessionId": api_session_id 
        },
        "userdetails": {
            "mobileno": mobile,
            "OTP": otp
        }
    }

    api_url = f"{config.EMUDHRA_API_URL}/CustomerCareAPI/AuthenticateMobileOTP"

    try:
        resp = requests.post(api_url, json=payload, verify=False, timeout=10)
        data = resp.json()
        
        status = None
        if 'status' in data: status = data['status']
        elif 'response' in data and 'status' in data['response']: status = data['response']['status']
        elif 'data' in data and 'status' in data['data']: status = data['data']['status']

        if str(status) == "1":
            return True, "Verified"
        else:
            msg = data.get('errorMessage', 'Invalid OTP')
            return False, msg
            
    except Exception as e:
        logger.error(f"❌ Verification Error: {str(e)}")
        return False, f"Verification Error: {str(e)}"