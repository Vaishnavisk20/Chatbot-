import os
import config 
import requests
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from logger_config import get_logger

logger = get_logger(__name__)

FAQ_DOC_ID = config.FAQ_DOC_ID
ERROR_DOC_ID = config.ERROR_DOC_ID

if not config.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Please check your .env file.")

embeddings = OpenAIEmbeddings(openai_api_key=config.OPENAI_API_KEY)

def download_google_doc(file_id):
    """Downloads Google Doc content as plain text and cleans it."""
    url = f"https://docs.google.com/document/d/{file_id}/export?format=txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        text = response.text
        cleaned_text = text.replace('\r\n', '\n').replace('\n\n\n', '\n\n')
        return cleaned_text
    except Exception as e:
        logger.error(f"Error downloading doc {file_id}: {e}")
        return ""

def create_retriever_from_text(text, source_name):
    """Creates a FAISS retriever from text content."""
    if not text:
        return None
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, 
        chunk_overlap=config.CHUNK_OVERLAP
    )
    texts = text_splitter.split_text(text)
    
    docs = [Document(page_content=t, metadata={"source": source_name}) for t in texts]
    
    if not docs:
        return None
        
    vectorstore = FAISS.from_documents(docs, embeddings)
    
    return vectorstore.as_retriever(search_kwargs={"k": config.RETRIEVER_K})

# --- INITIALIZE KNOWLEDGE BASE ---
logger.info("📚 Loading Knowledge Base (FAQs & Error Docs)...")

faq_text = download_google_doc(FAQ_DOC_ID)
logger.info(f"   - FAQ Doc loaded: {len(faq_text)} characters")
faq_retriever = create_retriever_from_text(faq_text, "FAQ_Doc")

error_text = download_google_doc(ERROR_DOC_ID)
logger.info(f"   - Error Doc loaded: {len(error_text)} characters")
error_retriever = create_retriever_from_text(error_text, "Error_Doc")

logger.info("✅ Knowledge Base Loaded!")