import json
import logging
import os
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

# Determine the absolute path to the project root (one level up from engine/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Path to log files
LOG_FILE = os.path.join(LOG_DIR, "sia.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "sia_error.log")
CRASH_LOG_FILE = os.path.join(LOG_DIR, "crash.log")

# Track all loggers for cleanup
_loggers = {}


class JsonLogFormatter(logging.Formatter):
    """Structured JSON formatter for production log observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S"),
            "logger": record.name,
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_crash_handler():
    """Trap unhandled exceptions on all threads and write structured crash reports."""
    def _handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        crash_info = {
            "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None), "%Y-%m-%d %H:%M:%S"),
            "error_type": exc_type.__name__,
            "error_message": str(exc_value),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        }
        try:
            with open(CRASH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(crash_info) + "\n")
        except Exception:
            pass

        sys.stderr.write(f"💥 CRASH DETECTED [{exc_type.__name__}]: {exc_value}\nCrash log saved to {CRASH_LOG_FILE}\n")

    sys.excepthook = _handle_exception
    threading.excepthook = lambda args: _handle_exception(args.exc_type, args.exc_value, args.exc_traceback)


# Initialize crash reporter
setup_crash_handler()


def get_logger(name):
    """
    Returns a configured logger instance for the given module name.
    Logs will be written to logs/sia.log and rotated when they reach 5MB.
    """
    logger = logging.getLogger(name)
    _loggers[name] = logger
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=5 * 1024 * 1024, 
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JsonLogFormatter())
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
    return logger


def cleanup_logger():
    """Close all logger handlers and release file handles."""
    for logger_name, logger in _loggers.items():
        for handler in logger.handlers[:]:
            try:
                handler.close()
                logger.removeHandler(handler)
            except Exception as e:
                print(f"Error closing handler for {logger_name}: {e}")
    
    _loggers.clear()

