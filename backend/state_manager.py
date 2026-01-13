import os
import json
import psycopg2
import config 
from logger_config import get_logger
from langchain_core.messages import HumanMessage, AIMessage

logger = get_logger(__name__)
DB_URL = config.POSTGRES_DB_URL

class StateManager:
    
    @staticmethod
    def _get_connection():
        """Establishes connection to Postgres"""
        if not DB_URL: return None
        try:
            return psycopg2.connect(DB_URL)
        except Exception as e:
            logger.error(f"❌ DB Connection Error: {e}")
            return None

    # --- CORE: GET DATA (Strictly DB) ---
    @staticmethod
    def _get_data(session_id):
        conn = StateManager._get_connection()
        if not conn: return {}
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT session_data FROM active_user_sessions WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row: return row[0]
            return {}
            
        except Exception as e:
            logger.warning(f"⚠️ DB Read Error ({session_id}): {e}")
            if conn: conn.close()
            return {}

    # --- CORE: SET DATA (Strictly DB) ---
    @staticmethod
    def _set_data(session_id, data):
        conn = StateManager._get_connection()
        if not conn: return

        try:
            cur = conn.cursor()
            json_data = json.dumps(data)
            
            sql = """
            INSERT INTO active_user_sessions (session_id, session_data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (session_id) 
            DO UPDATE SET session_data = EXCLUDED.session_data, updated_at = NOW();
            """
            cur.execute(sql, (session_id, json_data))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ DB Write Error: {e}")
            if conn: conn.close()

    # =========================================================
    # PUBLIC METHODS
    # =========================================================

    @staticmethod
    def update_session(session_id, updates):
        current_data = StateManager._get_data(session_id)
        current_data.update(updates)
        StateManager._set_data(session_id, current_data)

    @staticmethod
    def get_state(session_id):
        return StateManager._get_data(session_id)

    @staticmethod
    def set_state(session_id, state_data):
        StateManager.update_session(session_id, state_data)

    @staticmethod
    def get_verified_user(session_id):
        data = StateManager._get_data(session_id)
        if data.get("verified") is True:
            return {"mobile": data.get("mobile"), "verified": True}
        return None

    @staticmethod
    def set_verified_user(session_id, user_data):
        StateManager.update_session(session_id, user_data)

    @staticmethod
    def set_mobile_session_map(mobile, session_id):
        StateManager.update_session(session_id, {"mobile": mobile})

    @staticmethod
    def clear_previous_sessions_for_mobile(mobile):
        conn = StateManager._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                sql = "DELETE FROM active_user_sessions WHERE session_data->>'mobile' = %s"
                cur.execute(sql, (mobile,))
                conn.commit()
                cur.close()
                conn.close()
            except: pass

    # --- AGENT QUEUE (DB Based) ---
    @staticmethod
    def queue_agent_message(session_id, message):
        data = StateManager._get_data(session_id)
        queue = data.get("agent_queue", [])
        
        if queue and queue[-1] == message: return

        queue.append(message)
        logger.info(f"📥 Queueing for {session_id} -> {message}")
        StateManager.update_session(session_id, {"agent_queue": queue})

    @staticmethod
    def get_agent_messages(session_id):
        data = StateManager._get_data(session_id)
        queue = data.get("agent_queue", [])
        
        if queue:
            StateManager.update_session(session_id, {"agent_queue": []})
            return queue
        return []

    # =========================================================
    # 🔥 AI CHAT HISTORY MANAGEMENT (DB Based) 🔥
    # =========================================================
    
    @staticmethod
    def get_chat_history(session_id):
        data = StateManager._get_data(session_id)
        raw_history = data.get("ai_history", [])
        
        history_objects = []
        for msg in raw_history:
            if msg["type"] == "human":
                history_objects.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                history_objects.append(AIMessage(content=msg["content"]))
        
        return history_objects

    @staticmethod
    def update_chat_history(session_id, user_msg, bot_msg):
        data = StateManager._get_data(session_id)
        current_history = data.get("ai_history", [])
        
        if user_msg:
            current_history.append({"type": "human", "content": user_msg})
        if bot_msg:
            current_history.append({"type": "ai", "content": bot_msg})
            
        if len(current_history) > 20: 
            current_history = current_history[-20:]
            
        StateManager.update_session(session_id, {"ai_history": current_history})