"""
Unit test suite for JARVIS-Level Assistant Features.
Tests audit logger, productivity engine, and plugin manager.
"""

import os
import pytest
from engine.audit_logger import log_action, get_recent_audit_logs
from engine.productivity import productivity_engine
from engine.plugin_manager import PluginManager


def test_audit_logger():
    assert log_action("test_action", risk_level="ALLOW", status="SUCCESS", details="unit test") is True
    logs = get_recent_audit_logs(limit=5)
    assert len(logs) > 0
    assert any(log["action_name"] == "test_action" for log in logs)


def test_productivity_daily_briefing():
    res = productivity_engine.generate_daily_briefing()
    assert "date" in res
    assert "briefing" in res
    assert "Good morning" in res["briefing"] or "Sia" in res["briefing"]


def test_productivity_add_reminder():
    res = productivity_engine.add_reminder("Test unit reminder task")
    assert "Done Hero" in res or "Task set" in res


def test_plugin_manager(tmp_path):
    # Create temporary plugin file
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text("""
def register_actions():
    return {"custom_plugin_ping": lambda: "pong from plugin"}
""")

    pm = PluginManager(plugins_dir=str(tmp_path))
    loaded = pm.load_plugins()
    assert "sample_plugin" in loaded

    result = pm.execute_plugin_action("custom_plugin_ping")
    assert result == "pong from plugin"
