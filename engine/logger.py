import logging
import os
from logging.handlers import RotatingFileHandler

# Determine the absolute path to the project root (one level up from engine/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Path to the specific log file
LOG_FILE = os.path.join(LOG_DIR, "sia.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "sia_error.log")

# Track all loggers for cleanup
_loggers = {}

def get_logger(name):
    """
    Returns a configured logger instance for the given module name.
    Logs will be written to logs/sia.log and rotated when they reach 5MB.
    """
    logger = logging.getLogger(name)
    _loggers[name] = logger  # ✅ Track logger for cleanup
    
    # Check if this logger already has handlers to prevent duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create console handler for INFO and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Create file handler for DEBUG and above with rotation (max 5MB, keep 3 backups)
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=5 * 1024 * 1024, 
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Dedicated error file handler per TRD requirement.
        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
    return logger


def cleanup_logger():
    """
    ✅ Close all logger handlers and release file handles.
    Call this at application shutdown to prevent resource leaks.
    """
    for logger_name, logger in _loggers.items():
        # Close and remove all handlers
        for handler in logger.handlers[:]:  # Copy list to avoid modification during iteration
            try:
                handler.close()
                logger.removeHandler(handler)
            except Exception as e:
                print(f"Error closing handler for {logger_name}: {e}")
    
    _loggers.clear()  # Clear the tracking dictionary
