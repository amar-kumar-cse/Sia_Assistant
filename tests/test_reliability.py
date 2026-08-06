"""
Unit tests for utils/reliability.py safety wrapper and crash guard.
"""

import pytest
import asyncio
from utils.reliability import safe_async_call, safe_sync_call, global_exception_handler


@pytest.mark.asyncio
async def test_safe_async_call_success():
    @safe_async_call(timeout_seconds=5)
    async def sample_fn(x, y):
        return x + y

    result = await sample_fn(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_safe_async_call_timeout():
    @safe_async_call(
        timeout_seconds=0.1,
        fallback_message="Timeout occured",
        max_retries=1
    )
    async def hanging_fn():
        await asyncio.sleep(2.0)
        return "Done"

    result = await hanging_fn()
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["message"] == "Timeout occured"


@pytest.mark.asyncio
async def test_safe_async_call_exception_custom_fallback():
    fallback_dict = {"emotion": "error", "text": "API failed"}

    @safe_async_call(
        timeout_seconds=1.0,
        max_retries=1,
        fallback_value=fallback_dict
    )
    async def failing_fn():
        raise RuntimeError("API Connection Error")

    result = await failing_fn()
    assert result == fallback_dict


def test_safe_sync_call_success():
    @safe_sync_call()
    def sync_fn(a, b):
        return a * b

    assert sync_fn(4, 5) == 20


def test_safe_sync_call_exception():
    @safe_sync_call(fallback_message="Sync error caught", max_retries=0)
    def failing_sync_fn():
        raise ValueError("Division by zero")

    res = failing_sync_fn()
    assert isinstance(res, dict)
    assert res["success"] is False
    assert res["message"] == "Sync error caught"


def test_global_exception_handler_keyboard_interrupt(mocker=None):
    # Ensure KeyboardInterrupt is passed to default sys.__excepthook__
    import sys
    try:
        global_exception_handler(KeyboardInterrupt, KeyboardInterrupt("ctrl+c"), None)
    except Exception as e:
        pytest.fail(f"global_exception_handler raised exception: {e}")
