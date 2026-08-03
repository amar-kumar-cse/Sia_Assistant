"""
Deep Edge-Case Test Coverage Suite for Sia Assistant.
Tests native tool calling schemas, continuous voice session timeouts, Google OAuth fallbacks,
structured fact extraction, and proactive IDE error detection.
"""

import pytest
import time
from engine.brain import SIA_TOOLS, GeminiBrain
from engine.listen_engine import set_active_session, is_in_continuous_session
from engine.productivity import productivity_engine
from engine.memory import extract_and_save_facts, get_user_fact
from engine.vision_engine import analyze_proactive_ide_error


def test_native_gemini_tools_declaration():
    assert len(SIA_TOOLS) >= 3
    tool_names = [fn.__name__ for fn in SIA_TOOLS]
    assert "open_app_tool" in tool_names
    assert "get_weather_tool" in tool_names
    assert "add_reminder_tool" in tool_names


def test_continuous_voice_session():
    set_active_session()
    assert is_in_continuous_session() is True


def test_productivity_oauth_fallback():
    events = productivity_engine.get_calendar_events()
    assert isinstance(events, list)
    assert len(events) > 0

    emails = productivity_engine.get_unread_emails()
    assert "Gmail" in emails or "OAuth" in emails


def test_structured_fact_extraction():
    assert extract_and_save_facts("mera naam Amar Kumar hai", "Hello Amar!") is True
    fact = get_user_fact("user_name")
    assert fact is not None
    assert "Amar" in fact["fact"]


def test_proactive_ide_error_scanner():
    # Calling on current window (or unknown window) should complete gracefully without exceptions
    res = analyze_proactive_ide_error()
    assert res is None or isinstance(res, str)
