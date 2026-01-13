import os
import re
import json
import uuid
import time
import requests
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List

# --- IMPORTS ---
import config
from logger_config import get_logger
from auth import send_otp, verify_otp
from agent import get_agent_executor
from tools import get_application_details
from database import log_chat_to_db
from state_manager import StateManager 
from langchain_core.messages import HumanMessage, AIMessage

# Initialize Logger
logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory History
CHAT_HISTORY = {} 

# =========================================================================
# 🚀 PERFORMANCE OPTIMIZATION: LOAD AGENT ONCE AT STARTUP
# =========================================================================
# This prevents rebuilding the AI brain for every single message.
logger.info("⚡ Initializing AI Agent... (This happens only once)")
try:
    AGENT_EXECUTOR = get_agent_executor()
    logger.info("⚡ AI Agent Ready!")
except Exception as e:
    logger.critical(f"❌ Failed to initialize AI Agent: {e}")
    AGENT_EXECUTOR = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.get("/")
def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "running", "service": "Lia Support Bot (Stateful)"}

# =========================================================================
# HELPER: MASK SENSITIVE INFO (PII)
# =========================================================================
def mask_sensitive_info(text: str) -> str:
    """
    Masks PII: Keeps ONLY the 1st and Last character/digit.
    Rest is replaced with 'X'.
    """
    if not text: return ""

    # 1. Mask Aadhaar (12 digits) -> 1XXXXXXXXXX2
    text = re.sub(r'\b(\d)\d{10}(\d)\b', r'\1XXXXXXXXXX\2', text)

    # 2. Mask Mobile (10 digits) -> 9XXXXXXXX8
    text = re.sub(r'\b(\d)\d{8}(\d)\b', r'\1XXXXXXXX\2', text)

    # 3. Mask PAN (10 chars: 5 letters, 4 digits, 1 letter) -> AXXXXXXXXF
    text = re.sub(r'\b([A-Za-z])[A-Za-z0-9]{8}([A-Za-z0-9])\b', r'\1XXXXXXXX\2', text)

    return text

# =========================================================================
# 1. SEND USER MESSAGE -> AMEYO API
# =========================================================================
def send_to_ameyo(session_id, mobile, message_text):
    try:
        ameyo_url = config.AMEYO_BASE_URL
        app_id = config.AMEYO_APP_ID
        guid = uuid.uuid4().hex
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S+05:30', time.localtime())

        unique_user_id = session_id 

        payload = {
            "trigger": config.AMEYO_MSG_TRIGGER,
            "app": { "_id": app_id },
            "messages": [
                {
                    "type": "text", "text": message_text, "name": mobile,
                    "_id": guid, "mediaUrl": "", "metaData": {},
                    "source": { "type": "web", "integrationId": unique_user_id }
                }
            ],
            "appUser": {
                "_id": unique_user_id,
                "surName": mobile,
                "givenName": "User",
                "clients": [{ "displayName": mobile, "lastSeen": timestamp, "platform": "web" }],
                "properties": { 
                    "additionalParameters": json.dumps({ 
                        "phone": mobile, 
                        "messageText": message_text,
                        "session_id": session_id 
                    }) 
                }
            }
        }
        
        requests.post(f"{ameyo_url}/ameyorestapi/receiveMessage", json=payload, verify=False, timeout=5)
        logger.info(f"✅ Forwarded message to Ameyo for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ameyo Forward Error: {e}")
        return False

# =========================================================================
# 2. RECEIVE AGENT MESSAGE -> USER (Webhook)
# =========================================================================
@app.post("/send/appusers/{user_id}/messages")
async def receive_from_ameyo(user_id: str, request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        logger.info(f"📩 Received from Ameyo for {user_id}: {payload}")
        
        agent_text = payload.get("text", "")
        
        # 1. Capture the Name from your Mock API payload or Ameyo
        agent_name = payload.get("name") 
        if not agent_name:
            agent_name = payload.get("metadata", {}).get("userName", "Support Agent")

        if agent_text:
            # 2. Create a Structured Message Object
            message_data = {
                "text": agent_text,
                "sender": agent_name,   # e.g. "rchat"
                "type": "agent_message",
                "timestamp": time.time()
            }

            # 3. Queue this OBJECT (not just a string)
            StateManager.queue_agent_message(user_id, message_data)
            
            # 4. Log to DB (Text only for readability)
            user_data = StateManager.get_verified_user(user_id)
            mobile = user_data.get('mobile', 'Unknown') if user_data else 'Unknown'
            
            log_text_db = f"[{agent_name}]: {agent_text}"
            background_tasks.add_task(log_chat_to_db, user_id, mobile, "", log_text_db, "agent")
            
        return {"status": "success", "message": "Message queued"}
    except Exception as e:
        logger.error(f"❌ Error receiving from Ameyo: {e}")
        return {"status": "error", "message": str(e)}

# =========================================================================
# 3. POLL ENDPOINT
# =========================================================================
@app.get("/chat/poll")
def poll_messages(session_id: str):
    messages = StateManager.get_agent_messages(session_id)
    return {"messages": messages}

# =========================================================================
# 4. MAIN CHAT ENDPOINT
# =========================================================================
@app.post("/chat")
async def chat_endpoint(req: ChatRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id
    raw_input = req.message.strip()
    
    # 1. Load State
    session_data = StateManager.get_state(session_id)
    is_verified_user = session_data.get("verified") is True
    current_state = session_data.get("state", "init")
    current_mobile = session_data.get("mobile")

    # 2. PII MASKING LOGIC
    if is_verified_user or current_state == "handover_active":
        user_input = mask_sensitive_info(raw_input)
    else:
        user_input = raw_input # No masking during OTP/Mobile entry

    # 3. Context Memory
    if session_id not in CHAT_HISTORY: CHAT_HISTORY[session_id] = []
    history = CHAT_HISTORY[session_id]

    # =========================================================================
    # 🔴 HANDOVER MODE (STRICT TERMINATION OF AI)
    # =========================================================================
    if current_state == "handover_active":
        if current_mobile:
            logger.info(f"👤 Routing to Live Agent: {session_id}")
            
            # A. Send RAW (Unmasked) input to Live Agent
            background_tasks.add_task(send_to_ameyo, session_id, current_mobile, raw_input)
            
            # B. Log MASKED input to Database (Privacy)
            background_tasks.add_task(log_chat_to_db, session_id, current_mobile, user_input, "")
            
            # Return empty (Frontend polls for agent reply)
            return {"response": ""} 
        else:
            return {"response": "Session expired. Please reload."}

    bot_response = ""
    
    # =========================================================================
    # PART A: AUTHENTICATION FLOW
    # =========================================================================
    if not is_verified_user:
        
        # --- SCENARIO 1: WAITING FOR OTP ---
        if current_state == "waiting_for_otp":
            mobile = session_data.get("mobile")
            api_sess_id = session_data.get("api_session_id")
            
            # Verify OTP using raw_input logic (OTP is not PII in this context)
            is_verified, msg = verify_otp(mobile, raw_input, api_sess_id)
            
            if is_verified:
                StateManager.update_session(session_id, {"verified": True, "state": "verified"})
                
                try:
                    logger.info(f"🤖 User Verified. Fetching details for {mobile}...")
                    tool_raw = get_application_details.invoke(mobile)
                    tool_data = json.loads(tool_raw)
                    
                    meta_status = tool_data.get("meta", {}).get("status", "0")
                    
                    if meta_status != "1":
                        bot_response = (
                            "✅ OTP verified. Loading your application details.\n\n"
                            "**Application Not Found.**\n\n"
                            f"No application details found for mobile number **{mobile}**.\n\n"
                            "[Buy Digital Signature](https://emudhradigital.com/buy-digital-signature)"
                        )
                    else:
                        details = tool_data.get("details", {})
                        app_det = details.get("applicantDetails", {})
                        cert_det = details.get("schemeCertDetails", {})
                        pay_det = details.get("paymentDetails", {})
                        status_list = details.get("statusDetails", [])

                        name = app_det.get("commonname") or "Customer"
                        loc_parts = [app_det.get("locality"), app_det.get("state"), app_det.get("country")]
                        location = ", ".join([p for p in loc_parts if p]) or "N/A"
                        org = app_det.get("organization") or "N/A"
                        product = pay_det.get("product") or cert_det.get("certificateClass") or "Digital Signature"
                        app_no = cert_det.get("applicationNo") or "N/A"
                        inv_id = pay_det.get("INVOICE_ID") or "N/A"
                        pay_status = pay_det.get("status") or "Pending"

                        timeline_text = ""
                        def find_date(search_term):
                            for s in status_list:
                                if search_term.lower() in s.get("status", "").lower(): return s.get("dateAndTime")
                            return None

                        sub_date = find_date("Application Submitted")
                        if sub_date: timeline_text += f"✅ Application Submitted on {sub_date}<br>"
                        if find_date("Mobile verification") or find_date("Email verification"):
                            timeline_text += "✅ Mobile and Email verifications completed<br>"
                        
                        act_date = find_date("Account Activated") or find_date("Account Approved")
                        if act_date: timeline_text += f"✅ Account Approved on {act_date}<br>"
                        else: timeline_text += f"⏳ Current Status: {status_list[-1].get('status', 'Pending')}<br>"

                        table_html = """
                        <div style="background-color: #f9f9f9; border-radius: 8px; padding: 10px; margin: 10px 0; border: 1px solid #eee;">
                            <h4 style="margin: 0 0 10px 0; color: #0056b3;">Scheme Details</h4>
                            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        """
                        fields = {"applicationNo": "App No", "certificateClass": "Class", "validity": "Validity", "expiryDate": "Expiry"}
                        for k, l in fields.items():
                            val = cert_det.get(k, "")
                            if val: table_html += f"<tr><td style='padding:4px; font-weight:600;'>{l}</td><td style='padding:4px;'>{val}</td></tr>"
                        table_html += "</table></div>"

                        bot_response = (
                            "✅ OTP verified. Loading your application details.\n\n"
                            f"Dear Customer,\n\n"
                            f"Below is the status for the registered mobile number {mobile}:\n\n"
                            f"**Name:** {name}\n"
                            f"**Location:** {location}\n"
                            f"**Org:** {org}\n"
                            f"**Product:** {product}\n\n"
                            f"**Timeline:**\n{timeline_text}\n"
                            f"{table_html}\n"
                            f"**Payment:** {pay_status} (Inv: {inv_id})\n\n"
                            "[Click Here to Login](https://emudhradigital.com/Login.jsp)"
                        )
                        
                except Exception as e:
                    logger.error(f"❌ Auto-Fetch Error: {e}")
                    bot_response = "✅ OTP verified. Loading your application details.\n\n(Could not fetch details automatically)."
            else:
                bot_response = "❌ The OTP you entered is incorrect. Please re-enter the correct OTP sent to your registered mobile number."

        # --- SCENARIO 2: WAITING FOR MOBILE (INIT) ---
        else:
            if re.match(r'^\d{10}$', raw_input):
                mobile_input = raw_input
                StateManager.clear_previous_sessions_for_mobile(mobile_input)
                success, msg, api_sess_id = send_otp(mobile_input)
                
                if success:
                    StateManager.set_state(session_id, {
                        "state": "waiting_for_otp", 
                        "mobile": mobile_input,
                        "api_session_id": api_sess_id
                    })
                    bot_response = f"✅ We've sent an OTP to **{mobile_input}**. Please enter the OTP to verify and proceed."
                else:
                    StateManager.set_state(session_id, {"state": "init"})
                    bot_response = f"⚠️ Failed to send OTP: {msg}"
            else:
                bot_response = "Please enter your valid 10-digit registered mobile number."

    # =========================================================================
    # PART B: AI AGENT FLOW (VERIFIED)
    # =========================================================================
    else:
        verified_mobile = session_data.get("mobile")
        current_mobile = verified_mobile
        try:
            if AGENT_EXECUTOR:
                # 🚀 USE GLOBAL EXECUTOR
                res = AGENT_EXECUTOR.invoke({"input": user_input, "chat_history": history, "verified_mobile": verified_mobile})
                bot_response = res["output"]
            else:
                logger.critical("Agent Executor is None!")
                bot_response = "System Error: AI Agent not initialized."
                
        except Exception as e:
            logger.error(f"Agent Error: {e}")
            bot_response = "I encountered an error processing your request."

    # =========================================================================
    # PART C: LOGGING & HANDOVER
    # =========================================================================
    
    if "HANDOVER_REQUIRED" in bot_response:
        clean_response = bot_response.replace("{{HANDOVER_REQUIRED}}", "") \
                                     .replace("{HANDOVER_REQUIRED}", "") \
                                     .replace("HANDOVER_REQUIRED", "").strip()
        
        bot_response = clean_response if clean_response else "Connecting you to a support specialist..."
        
        mobile_payload = verified_mobile if verified_mobile else current_mobile
        
        success = send_to_ameyo(session_id, mobile_payload, raw_input)
        
        if success:
            StateManager.set_state(session_id, {"state": "handover_active"})
            
            history.extend([HumanMessage(content=user_input), AIMessage(content=bot_response)])
            if current_mobile:
                background_tasks.add_task(log_chat_to_db, session_id, current_mobile, user_input, bot_response, "bot")
                
            return {"response": "✅ You're now connected. A support specialist will join the chat shortly."}
        else:
            bot_response = "I'm sorry, I was unable to connect you to a support specialist right now."

    history.extend([HumanMessage(content=user_input), AIMessage(content=bot_response)])
    
    if current_mobile:
        background_tasks.add_task(log_chat_to_db, session_id, current_mobile, user_input, bot_response, "bot")

    return {"response": bot_response}