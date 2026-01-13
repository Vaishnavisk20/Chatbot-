import os
import json
import requests
import hashlib
import time
from datetime import datetime, timedelta, timezone
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from logger_config import get_logger # Import Logger

import config
from knowledge_base import faq_retriever, error_retriever

logger = get_logger(__name__)

# --- EXISTING TOOLS ---

@tool
def get_purchase_links(product_type: str) -> str:
    """Returns official links for purchasing DSC, SSL, or Tokens."""
    product = product_type.lower()
    if 'dsc' in product or 'digital signature' in product:
        return json.dumps({"website_url": config.URL_BUY_DSC})
    elif 'ssl' in product:
        return json.dumps({"website_url": config.URL_BUY_SSL})
    elif 'token' in product:
        return json.dumps({"website_url": config.URL_BUY_TOKEN})
    return "Please specify if you want DSC, SSL, or Token."

@tool
def track_shipment(awb_number: str):
    """Tracks shipment using Shiprocket API given an AWB number."""
    return "Tracking functionality requires Shiprocket credentials setup."

@tool
def get_application_details(query: str = ""):
    """Fetches application details. Auto-detects verified mobile from context."""
    mobile_number = query.strip()
    if not mobile_number: return "Mobile number not found in context."

    now_utc = datetime.now(timezone.utc)
    ts = (now_utc + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
    txn = f"TXN{int(time.time() * 1000)}"
    client_key = config.CLIENT_ACCESS_KEY
    auth_hash = hashlib.sha256(f"{client_key}{ts}{txn}".encode()).hexdigest()
    
    payload = {
        "meta": {"ver": "1.0", "ts": ts, "txn": txn, "clientCode": config.CLIENT_CODE, "clientAccessKey": auth_hash},
        "details": {"mobileNo": mobile_number, "isPIIMasked": "1"}
    }
    url = f"{config.EMUDHRA_API_URL}/CustomerCareAPI/getApplicationDetails"
    
    try:
        resp = requests.post(url, json=payload, verify=False, timeout=5)
        return json.dumps(resp.json())
    except Exception as e:
        logger.error(f"Error fetching app details: {e}")
        return f"Error: {str(e)}"

# --- RAG TOOLS (With Logging) ---

@tool
def faqdoc(query: str) -> str:
    """
    Search the FAQ Knowledge Base. 
    """
    if not faq_retriever:
        return "FAQ Database not loaded."
    
    docs = faq_retriever.invoke(query)
    
    # Log to FILE only (Console is Warning only)
    logger.info(f"🔍 FAQ SEARCH for '{query}':")
    for i, d in enumerate(docs):
        logger.info(f"   [Chunk {i+1}]: {d.page_content[:150]}...")
    
    result = "\n\n".join([d.page_content for d in docs])
    return result if result else "No relevant FAQ found."

@tool
def errordscdoc(query: str) -> str:
    """
    Search the Error Troubleshooting Database.
    """
    if not error_retriever:
        return "Error Database not loaded."
    
    docs = error_retriever.invoke(query)
    
    logger.info(f"🔍 ERROR SEARCH for '{query}':")
    for i, d in enumerate(docs):
        logger.info(f"   [Chunk {i+1}]: {d.page_content[:150]}...")

    result = "\n\n".join([d.page_content for d in docs])
    return result if result else "No relevant error solution found."

@tool
def website_search(query: str) -> str:
    """
    Search the eMudhra Digital website.
    """
    search = DuckDuckGoSearchRun()
    final_query = f"{config.URL_WEBSITE_SEARCH_DOMAIN} {query}"
    try:
        logger.info(f"🌐 SEARCHING WEB: {final_query}")
        return search.run(final_query)
    except Exception as e:
        logger.error(f"Website search failed: {e}")
        return f"Website search failed: {e}"

@tool
def query_data_tool(query: str) -> str:
    """
    General Knowledge Base Search (VectorDB).
    """
    faq_res = faqdoc(query)
    err_res = errordscdoc(query)
    
    combined = f"FAQs:\n{faq_res}\n\nErrors:\n{err_res}"
    return combined
    