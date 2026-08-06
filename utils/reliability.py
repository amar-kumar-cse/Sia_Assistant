"""
RELIABILITY WRAPPER — Sia ka safety net
Har external/risky call is decorator se guzarni chahiye.
Isse Sia KABHI crash nahi hogi — hamesha graceful fallback degi.
"""

import sys
import asyncio
import functools
import logging
import traceback
from typing import Any, Callable, Optional, Dict, Union

# Set up logging for Sia reliability safety net
logger = logging.getLogger("sia.reliability")
crash_logger = logging.getLogger("sia.crash_guard")


def safe_async_call(
    timeout_seconds: float = 10.0,
    fallback_message: str = "Thoda issue aa raha hai, dobara try karti hoon",
    max_retries: int = 1,
    fallback_value: Optional[Any] = None
):
    """
    Decorator: kisi bhi async function ko wrap karta hai.
    - Timeout lagata hai (hamesha ke liye wait nahi karega — internet slow ho ya API hang ho)
    - Exception silently catch karta hai (crash nahi hone dega poora app)
    - Fallback message / value deta hai jo Sia bol/use kar sake user ko
    - Failure ko log karta hai
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    last_error = f"Timeout after {timeout_seconds}s"
                    logger.warning(f"[TIMEOUT] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[ERROR] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}", exc_info=True)

            # Sab retries fail — crash NAHI, graceful fallback return karo
            logger.error(f"[FALLBACK TRIGGERED] {func.__name__} failed after {max_retries+1} attempts: {last_error}")
            
            if fallback_value is not None:
                return fallback_value
            return {"success": False, "message": fallback_message}
        return wrapper
    return decorator


def safe_sync_call(
    fallback_message: str = "Thoda issue aa raha hai, dobara try karti hoon",
    max_retries: int = 1,
    fallback_value: Optional[Any] = None
):
    """
    Decorator: kisi bhi synchronous (blocking) risky function ko wrap karta hai.
    - Catch karta hai exceptions gracefully.
    - Logs errors without crashing the main application thread.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[SYNC ERROR] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}", exc_info=True)

            logger.error(f"[SYNC FALLBACK TRIGGERED] {func.__name__} failed: {last_error}")
            if fallback_value is not None:
                return fallback_value
            return {"success": False, "message": fallback_message}
        return wrapper
    return decorator


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Poore app ka last-line-of-defense.
    Koi bhi unhandled crash yahan pakda jaayega — app band NAHI hogi.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    crash_logger.critical(f"UNHANDLED EXCEPTION:\n{error_details}")

    # Display safe log warning to stderr
    sys.stderr.write(f"⚠️ [SIA SAFETY NET] Unhandled Exception Caught: {exc_value}\n")
