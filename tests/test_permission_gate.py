"""
Unit tests for Active Permission Gate & Security Defense System.
"""

import pytest
from engine.permission_gate import permission_gate, ActionRiskLevel
from engine.action_handler import action_handler


def test_permission_gate_risk_matrix():
    # SAFE action checks
    risk_safe, _ = permission_gate.evaluate_action("system_info")
    assert risk_safe == ActionRiskLevel.SAFE

    # CONFIRM action checks
    risk_confirm, reason = permission_gate.evaluate_action("kill_app", "chrome.exe")
    assert risk_confirm == ActionRiskLevel.CONFIRM
    assert "Confirmation required" in reason

    # DENY action checks
    risk_deny, reason_deny = permission_gate.evaluate_action("system_info", "format c: delete all")
    assert risk_deny == ActionRiskLevel.DENY
    assert "Security Block" in reason_deny


def test_untrusted_screen_ocr_defense():
    # Direct user input can execute or ask confirmation
    risk_user, _ = permission_gate.evaluate_action("kill_app", "notepad.exe", source="direct_user_input")
    assert risk_user == ActionRiskLevel.CONFIRM

    # Untrusted screen OCR is completely DENIED for destructive/confirm actions
    risk_ocr, reason_ocr = permission_gate.evaluate_action("kill_app", "notepad.exe", source="untrusted_screen_observation")
    assert risk_ocr == ActionRiskLevel.DENY
    assert "untrusted" in reason_ocr.lower()


def test_action_handler_permission_integration():
    # SAFE action executes immediately
    res_safe = action_handler.execute("system_info", "get info")
    assert res_safe is not None

    # CONFIRM action returns confirmation prompt before execution
    res_confirm = action_handler.execute("kill_app", "notepad.exe")
    assert "Safety check" in res_confirm or "Confirmation" in res_confirm

    # DENIED action returns security warning immediately
    res_deny = action_handler.execute("system_info", "format c:")
    assert "Security Block" in res_deny
