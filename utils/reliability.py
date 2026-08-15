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
import concurrent.futures
from typing import Any, Callable, Optional, Dict, Union

# Set up logging for Sia reliability safety net
logger = logging.getLogger("sia.reliability")
crash_logger = logging.getLogger("sia.crash_guard")

# Optional Audit Logger integration
try:
    from engine.audit_logger import log_action
except ImportError:
    log_action = None

# UI & Avatar recovery callbacks for global exception handlers
_UI_NOTIFY_CALLBACK: Optional[Callable[[str], None]] = None
_AVATAR_RESET_CALLBACK: Optional[Callable[[], None]] = None


def register_crash_guard_callbacks(
    ui_notify_fn: Optional[Callable[[str], None]] = None,
    avatar_reset_fn: Optional[Callable[[], None]] = None
):
    """
    Register UI notification and avatar state recovery callbacks
    for global exception handlers (sys.excepthook & loop.set_exception_handler).
    """
    global _UI_NOTIFY_CALLBACK, _AVATAR_RESET_CALLBACK
    if ui_notify_fn is not None:
        _UI_NOTIFY_CALLBACK = ui_notify_fn
    if avatar_reset_fn is not None:
        _AVATAR_RESET_CALLBACK = avatar_reset_fn


def safe_async_call(
    timeout_seconds: float = 10.0,
    fallback_message: str = "Thoda issue aa raha hai, dobara try karti hoon",
    max_retries: int = 1,
    fallback_value: Optional[Any] = None
):
    """
    Decorator: kisi bhi async function ko wrap karta hai.
    - Hard timeout via asyncio.wait_for (never hangs on slow/frozen connections)
    - Exception handling so nothing propagates uncaught
    - Retries up to max_retries
    - Re-raises KeyboardInterrupt and asyncio.CancelledError (never swallows system signals)
    - On final failure, logs error to audit logger & returns structured fallback result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    # Never swallow system interrupts or coroutine cancellations
                    raise
                except asyncio.TimeoutError:
                    last_error = f"Timeout after {timeout_seconds}s"
                    logger.warning(f"[TIMEOUT] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[ERROR] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}", exc_info=True)

            # All retries failed — graceful fallback
            logger.error(f"[FALLBACK TRIGGERED] {func.__name__} failed after {max_retries+1} attempts: {last_error}")
            if log_action:
                try:
                    log_action(func.__name__, risk_level="FALLBACK", status="FAILURE", metadata={"error": str(last_error)})
                except Exception:
                    pass

            if fallback_value is not None:
                return fallback_value
            return {"success": False, "message": fallback_message}
        return wrapper
    return decorator


def safe_sync_call(
    timeout_seconds: float = 10.0,
    fallback_message: str = "Thoda issue aa raha hai, dobara try karti hoon",
    max_retries: int = 1,
    fallback_value: Optional[Any] = None
):
    """
    Decorator: kisi bhi synchronous (blocking) risky function ko wrap karta hai.
    - Enforces hard timeout using thread-based pool (ThreadPoolExecutor) since sync code can't use asyncio.wait_for directly.
    - Catches exceptions gracefully without crashing main application thread.
    - Re-raises KeyboardInterrupt.
    - On final failure, logs error & returns structured fallback result.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(func, *args, **kwargs)
                        return future.result(timeout=timeout_seconds)
                except KeyboardInterrupt:
                    raise
                except concurrent.futures.TimeoutError:
                    last_error = f"Sync call timeout after {timeout_seconds}s"
                    logger.warning(f"[SYNC TIMEOUT] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[SYNC ERROR] {func.__name__} attempt {attempt+1}/{max_retries+1}: {last_error}", exc_info=True)

            logger.error(f"[SYNC FALLBACK TRIGGERED] {func.__name__} failed: {last_error}")
            if log_action:
                try:
                    log_action(func.__name__, risk_level="FALLBACK", status="FAILURE", metadata={"error": str(last_error)})
                except Exception:
                    pass

            if fallback_value is not None:
                return fallback_value
            return {"success": False, "message": fallback_message}
        return wrapper
    return decorator


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global sys.excepthook crash guard.
    Logs unhandled exceptions with full traceback at CRITICAL level,
    prevents process exit, triggers non-blocking UI notification, and resets avatar.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    crash_logger.critical(f"UNHANDLED GLOBAL EXCEPTION:\n{error_details}")
    sys.stderr.write(f"⚠️ [SIA SAFETY NET] Unhandled Exception Caught: {exc_value}\n")

    # Non-blocking UI notification
    if _UI_NOTIFY_CALLBACK:
        try:
            _UI_NOTIFY_CALLBACK("Sia encountered a temporary glitch, recovering...")
        except Exception as e:
            logger.error(f"UI notify callback failed: {e}")

    # Return avatar to idle state
    if _AVATAR_RESET_CALLBACK:
        try:
            _AVATAR_RESET_CALLBACK()
        except Exception as e:
            logger.error(f"Avatar reset callback failed: {e}")


def asyncio_exception_handler(loop, context):
    """
    Asyncio loop exception handler (for qasync/asyncio tasks).
    Logs unhandled task errors at CRITICAL level, prevents app crash,
    triggers UI toast notification, and resets avatar state.
    """
    exception = context.get("exception")
    message = context.get("message", "Unhandled asyncio task error")

    if exception:
        error_details = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        crash_logger.critical(f"UNHANDLED ASYNCIO EXCEPTION: {message}\n{error_details}")
    else:
        crash_logger.critical(f"UNHANDLED ASYNCIO ERROR: {message}")

    sys.stderr.write(f"⚠️ [SIA ASYNC SAFETY NET] Unhandled Task Exception: {exception or message}\n")

    if _UI_NOTIFY_CALLBACK:
        try:
            _UI_NOTIFY_CALLBACK("Sia task recovered from background error.")
        except Exception:
            pass

    if _AVATAR_RESET_CALLBACK:
        try:
            _AVATAR_RESET_CALLBACK()
        except Exception:
            pass
