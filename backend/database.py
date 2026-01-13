import os
import json
import time
import psycopg2
import config
from datetime import datetime
from logger_config import get_logger

logger = get_logger(__name__)
DB_URL = config.POSTGRES_DB_URL

def get_db_connection():
    """Establishes connection to Postgres"""
    if not DB_URL:
        logger.error("❌ Error: POSTGRES_DB_URL is not set in .env")
        return None
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        logger.error(f"❌ Database Connection Error: {e}")
        return None

def log_chat_to_db(session_id: str, mobile: str, user_msg: str, bot_msg: str, sender_role: str = "bot"):
    """
    Logs chat messages to PostgreSQL asynchronously.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        current_ts = int(time.time())
        txn_time = datetime.now()
        
        new_history = []
        
        if user_msg:
            new_history.append({
                "source": "user",
                "sentTime": str(current_ts),
                "message": user_msg
            })
            
        if bot_msg:
            new_history.append({
                "source": sender_role, 
                "sentTime": str(current_ts), 
                "message": bot_msg
            })
            
        if not new_history:
            return

        json_payload = json.dumps(new_history)

        sql = """
        INSERT INTO chat_transaction_logs (
            session_id,
            mobile_number,
            txn_start_time,
            txn_end_time,
            chat_messages
        )
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (session_id)
        DO UPDATE SET
            mobile_number = COALESCE(NULLIF(EXCLUDED.mobile_number, ''), chat_transaction_logs.mobile_number),
            txn_end_time = EXCLUDED.txn_end_time,
            chat_messages = COALESCE(chat_transaction_logs.chat_messages, '[]'::jsonb) || EXCLUDED.chat_messages,
            updated_at = NOW();
        """
        
        cur.execute(sql, (
            session_id,
            mobile,
            txn_time,
            txn_time,
            json_payload
        ))
        
        conn.commit()
        cur.close()
        # logger.info(f"📝 DB Logged: {session_id}") 

    except Exception as e:
        logger.error(f"❌ SQL Logging Error: {e}")
    finally:
        if conn:
            conn.close()