import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- SERVER SETTINGS ---
API_HOST = "0.0.0.0"
API_PORT = 8000

# --- SECRETS ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLIENT_ACCESS_KEY = os.getenv("CLIENT_ACCESS_KEY", "emCustomerAPI$$8765##ICA")
SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL")
SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD")
POSTGRES_DB_URL = os.getenv("POSTGRES_DB_URL")

# --- API URLS ---
EMUDHRA_API_URL = os.getenv("EMUDHRA_API_URL", "https://qaserver-int.emudhra.net:18006")
AMEYO_BASE_URL = os.getenv("AMEYO_BASE_URL", "http://127.0.0.1:5000")  # Changed to mock API for testing

# --- AMEYO CONFIGURATION ---
AMEYO_APP_ID = os.getenv("AMEYO_APP_ID", "5cac75981134520011f881ab")
AMEYO_MSG_TRIGGER = "message:appUser"

# --- CLIENT IDENTIFIERS ---
CLIENT_CODE = os.getenv("CLIENT_CODE", "emudhra")

# --- GOOGLE DOC IDS (KNOWLEDGE BASE) ---
FAQ_DOC_ID = os.getenv("GOOGLE_FAQ_DOC_ID", "1YT1NlHLyEgVp6InGedO2pI3-lfAayH8u")
ERROR_DOC_ID = os.getenv("GOOGLE_ERROR_DOC_ID", "1DDP5ouLtlE38QrU3CwjWxX2B_AFjQoeY")

# --- RAG / VECTOR STORE SETTINGS ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
RETRIEVER_K = 3  # Number of docs to retrieve

# --- AI MODEL SETTINGS ---
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
OPENAI_TEMPERATURE = 0

# --- WEBSITE URLS (HARDCODED LINKS) ---
URL_BUY_DSC = "https://emudhradigital.com/buy-digital-signature"
URL_BUY_SSL = "https://emudhradigital.com/buy-ssl-certificate"
URL_BUY_TOKEN = "https://emudhradigital.com/buy-usb-token-online"
URL_LOGIN = "https://emudhradigital.com/Login.jsp"
URL_WEBSITE_SEARCH_DOMAIN = "site:emudhradigital.com"