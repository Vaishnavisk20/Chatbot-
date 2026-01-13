import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_logger(module_name):
    """
    Configures and returns a logger instance.
    - File Handler: INFO level (writes all details to file)
    - Console Handler: WARNING level (keeps console clean)
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)  # Capture everything globally

    # Check if handlers are already added to avoid duplicates
    if not logger.handlers:
        # 1. Define Formats
        # File Format: Date Time - Module - Level - Message
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Console Format: Simple message
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')

        # 2. File Handler (Rotates daily)
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_filename = os.path.join(LOG_DIR, f"app_{current_date}.log")
        
        file_handler = TimedRotatingFileHandler(
            log_filename, when="midnight", interval=1, backupCount=30, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO) # Write INFO and above to file
        file_handler.setFormatter(file_formatter)

        # 3. Console Handler (Standard Output)
        console_handler = logging.StreamHandler(sys.stdout)
        # SET TO 'WARNING' TO REDUCE CONSOLE NOISE (As requested)
        # SET TO 'INFO' if you want to see basics in console
        console_handler.setLevel(logging.WARNING) 
        console_handler.setFormatter(console_formatter)

        # 4. Add Handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid double logging with Uvicorn
        logger.propagate = False

    return logger