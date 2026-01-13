import logging
import json
import threading
import requests
import sys
import time
from flask import Flask, request, jsonify

# --- CONFIGURATION ---
MOCK_PORT = 5000
MAIN_APP_WEBHOOK_URL = "http://localhost:8000/send/appusers/{session_id}/messages"
AMEYO_APP_ID = "5cac75981134520011f881ab"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MOCK AMEYO] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MockAmeyo")

app = Flask(__name__)

last_active_session_id = None

# =========================================================
# HELPER: SEND REPLY TO MAIN APP
# =========================================================
def send_reply_to_main_app(session_id, message_text):
    """
    Sends a message back to the Main Chatbot App using the specific JSON format.
    """
    if not session_id or session_id == "Unknown":
        logger.warning("⚠️ Cannot reply: Invalid Session ID")
        return

    target_url = MAIN_APP_WEBHOOK_URL.format(session_id=session_id)

    payload = {
        "role": "appMaker",
        "type": "text",
        "name": "rchat",
        "metadata": {
            "sourceType": "web",
            "appId": AMEYO_APP_ID,
            "IDENTIFIER": "AGENT_MESSAGE",
            "userName": "rchat",
            "userId": "rchat"
        },
        "text": message_text
    }

    try:
        logger.info(f"📤 Sending Auto-Reply to: {target_url}")
        resp = requests.post(target_url, json=payload, timeout=10)
        
        if resp.status_code == 200:
            print(f"   ✅ Reply sent successfully to Session: {session_id}")
        else:
            print(f"   ⚠️ Failed (Status: {resp.status_code}): {resp.text}")
            
    except Exception as e:
        logger.error(f"   ❌ Connection Error: {e}")

# =========================================================
# HELPER: AUTO REPLY THREAD
# =========================================================
def auto_reply_task(session_id):
    """Simulates agent thinking time and sends a reply"""
    time.sleep(2) # Wait 2 seconds
    msg = "Hello! This is an automated reply from the Mock Ameyo Agent. How can I help?"
    send_reply_to_main_app(session_id, msg)

# =========================================================
# 1. RECEIVE MESSAGE ENDPOINT
# =========================================================
@app.route('/ameyorestapi/receiveMessage', methods=['POST'])
def receive_message_from_bot():
    global last_active_session_id
    
    try:
        data = request.json
        
        msg_text = "N/A"
        user_phone = "Unknown"
        session_id = "Unknown"

        if "messages" in data and isinstance(data["messages"], list) and len(data["messages"]) > 0:
            msg_text = data["messages"][0].get("text", "")
            
        if "appUser" in data:
            user_phone = data["appUser"].get("surName", "")
            props_str = data["appUser"].get("properties", {}).get("additionalParameters", "{}")
            try:
                params = json.loads(props_str)
                session_id = params.get("session_id", "Unknown")
            except:
                pass

        if session_id != "Unknown":
            last_active_session_id = session_id

        # --- LOGGING ---
        print("\n" + "="*50)
        logger.info(f"📩 RECEIVED MESSAGE FROM BOT")
        print(f"   👤 Phone    : {user_phone}")
        print(f"   🆔 Session  : {session_id}")
        print(f"   💬 Message  : {msg_text}")
        print("="*50 + "\n")

        # 🔥 TRIGGER AUTO REPLY (In a separate thread so we don't block the 200 OK)
        if session_id != "Unknown":
            threading.Thread(target=auto_reply_task, args=(session_id,)).start()

        return jsonify({
            "status": "success", 
            "message": "Message received",
            "responseCode": 200
        }), 200

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# =========================================================
# 2. CONSOLE INPUT LOOP (Manual Override)
# =========================================================
def console_input_loop():
    time.sleep(1.5) 
    print(f"\n✨ MOCK AMEYO SERVER STARTED ON PORT {MOCK_PORT}")
    print("✨ AUTO-REPLY ENABLED: It will reply automatically after 2 seconds.")
    print("✨ You can ALSO type below to send manual messages:\n")
    
    while True:
        try:
            agent_reply = input()
            if not agent_reply.strip(): continue
            if not last_active_session_id:
                logger.warning("⚠️ No active session found yet.")
                continue
            send_reply_to_main_app(last_active_session_id, agent_reply)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            logger.error(f"Input Error: {e}")

# =========================================================
# MAIN ENTRY POINT
# =========================================================
if __name__ == '__main__':
    input_thread = threading.Thread(target=console_input_loop, daemon=True)
    input_thread.start()
    app.run(host='0.0.0.0', port=MOCK_PORT, debug=False, use_reloader=False)