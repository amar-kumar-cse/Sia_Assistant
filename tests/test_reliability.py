"""
Comprehensive Phase 6 Reliability & Stress Test Suite for Sia Assistant.
Tests API invalid keys, network drops, timeouts, rapid-fire stress loops, and OAuth expiry fallbacks.
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import patch, MagicMock

from utils.reliability import (
    safe_async_call,
    safe_sync_call,
    global_exception_handler,
    asyncio_exception_handler
)
from engine.brain import think
from engine.productivity import productivity_engine


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


def test_gemini_invalid_key_graceful_fallback():
    """Test 1: Gemini API call with invalid/expired key returns graceful fallback instead of crashing."""
    with patch("google.generativeai.GenerativeModel.generate_content", side_effect=Exception("400 Invalid API Key")):
        res = think("Hello Sia")
        assert isinstance(res, dict)
        assert res.get("emotion") in ["error", "default", "happy"]
        assert "text" in res
        assert len(res["text"]) > 0


def test_network_unreachable_graceful_fallback():
    """Test 2: Network unreachable during Gemini / Gmail / Calendar call asserts graceful fallback."""
    with patch("google.generativeai.GenerativeModel.generate_content", side_effect=OSError("Network unreachable")):
        res = think("Test prompt")
        assert isinstance(res, dict)
        assert "text" in res

    with patch("googleapiclient.discovery.build", side_effect=OSError("Connection Refused")):
        cal_res = productivity_engine.get_calendar_events()
        assert isinstance(cal_res, list)
        assert len(cal_res) > 0


def test_timeout_exceeded_clean_fallback():
    """Test 3: Exceeded timeout response times out cleanly without hanging."""
    @safe_sync_call(timeout_seconds=0.2, fallback_value={"success": False, "message": "Slow response timeout"}, max_retries=0)
    def slow_external_api():
        time.sleep(1.5)
        return "Finished"

    res = slow_external_api()
    assert isinstance(res, dict)
    assert res["success"] is False
    assert "timeout" in res["message"].lower()


def test_rapid_fire_sequential_commands_stress():
    """Test 4: Rapid-fire 20 sequential commands in a short loop without unhandled exceptions or memory explosion."""
    process = psutil.Process(os.getpid())
    initial_mem = process.memory_info().rss

    mock_resp = MagicMock()
    mock_resp.text = "[EMOTION:happy] Quick response"
    mock_resp.candidates = []

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_resp):
        for i in range(20):
            res = think(f"Quick test command #{i}")
            assert isinstance(res, dict)
            assert "text" in res

    final_mem = process.memory_info().rss
    mem_diff_mb = (final_mem - initial_mem) / (1024 * 1024)
    # Memory growth should be under 50MB for 20 simple calls
    assert mem_diff_mb < 50.0


def test_expired_oauth_token_reconnect_fallback():
    """Test 5: Simulated expired OAuth token returns clear fallback message, not a crash."""
    with patch("os.path.exists", return_value=True), \
         patch("google.oauth2.credentials.Credentials.from_authorized_user_file", side_effect=Exception("Token expired and refresh failed")):
        res = productivity_engine.get_unread_emails()
        assert isinstance(res, (str, dict))
        if isinstance(res, dict):
            assert res.get("success") is False
        else:
            assert ("gmail" in res.lower() or "credentials" in res.lower() or "token" in res.lower() or "error" in res.lower())


def test_global_exception_handler_keyboard_interrupt():
    import sys
    try:
        global_exception_handler(KeyboardInterrupt, KeyboardInterrupt("ctrl+c"), None)
    except Exception as e:
        pytest.fail(f"global_exception_handler raised exception: {e}")
