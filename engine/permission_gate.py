"""
Active Permission Gate & Risk Classifier for Sia Assistant.
Intercepts action execution requests BEFORE OS state changes occur.
Categorizes actions into SAFE (zero friction), CONFIRM (pre-execution approval), and DENY (blocked).
"""

from enum import Enum
from typing import Dict, Any, Tuple, Optional
from .logger import get_logger
from .audit_logger import log_action

logger = get_logger(__name__)


class ActionRiskLevel(Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


# Action risk classification matrix
ACTION_RISK_MATRIX: Dict[str, ActionRiskLevel] = {
    # ── SAFE / READ_ONLY Actions ──────────────────────────────────
    "system_info": ActionRiskLevel.SAFE,
    "battery_status": ActionRiskLevel.SAFE,
    "volume_query": ActionRiskLevel.SAFE,
    "get_weather": ActionRiskLevel.SAFE,
    "web_search": ActionRiskLevel.SAFE,
    "kb_search": ActionRiskLevel.SAFE,
    "read_file": ActionRiskLevel.SAFE,
    "vision_screen": ActionRiskLevel.SAFE,
    "vision_webcam": ActionRiskLevel.SAFE,
    "vision_window": ActionRiskLevel.SAFE,
    "vision_error": ActionRiskLevel.SAFE,
    "news": ActionRiskLevel.SAFE,
    "learn_fact": ActionRiskLevel.SAFE,
    "mood_detection": ActionRiskLevel.SAFE,
    "generate_daily_briefing": ActionRiskLevel.SAFE,

    # ── CONFIRM / DESTRUCTIVE Actions ──────────────────────────────
    "kill_app": ActionRiskLevel.CONFIRM,
    "close_window": ActionRiskLevel.CONFIRM,
    "system_shutdown": ActionRiskLevel.CONFIRM,
    "system_restart": ActionRiskLevel.CONFIRM,
    "delete_file": ActionRiskLevel.CONFIRM,
    "organize_files": ActionRiskLevel.CONFIRM,
    "generate_script": ActionRiskLevel.CONFIRM,
    "git_push": ActionRiskLevel.CONFIRM,
    "empty_recycle_bin": ActionRiskLevel.CONFIRM,
    "volume": ActionRiskLevel.CONFIRM,

    # ── DENY / MALICIOUS Actions ─────────────────────────────────
    "format_disk": ActionRiskLevel.DENY,
    "delete_system32": ActionRiskLevel.DENY,
    "extract_passwords": ActionRiskLevel.DENY,
    "export_api_keys": ActionRiskLevel.DENY,
}

DENY_KEYWORDS = [
    "format c:", "rm -rf /", "delete system32", "extract passwords", "export api keys",
    "drop database", "show secret keys"
]

CONFIRM_KEYWORDS = [
    "kill process", "close application", "shutdown computer", "restart system",
    "delete file", "empty recycle bin", "git push --force"
]


class PermissionGate:
    """Pre-execution security gate to evaluate action safety before system execution."""

    def evaluate_action(
        self,
        action_type: str,
        command_text: str = "",
        source: str = "direct_user_input"
    ) -> Tuple[ActionRiskLevel, str]:
        """
        Evaluate an action request pre-execution.
        Returns Tuple of (RiskLevel, ReasonText).
        """
        act_lower = (action_type or "").lower().strip()
        cmd_lower = (command_text or "").lower().strip()

        # 1. Untrusted Screen Observation Defense: Block executable actions from OCR
        if source == "untrusted_screen_observation":
            risk = ACTION_RISK_MATRIX.get(act_lower, ActionRiskLevel.CONFIRM)
            if risk in (ActionRiskLevel.CONFIRM, ActionRiskLevel.DENY):
                logger.warning(f"🛡️ Security Block: Untrusted OCR tried executing system action '{act_lower}'")
                log_action(action_type, risk_level="DENY", status="BLOCKED_OCR", details=f"Untrusted screen OCR source: {command_text}")
                return ActionRiskLevel.DENY, "🛡️ Security Shield: Screen OCR text is untrusted and cannot execute system commands automatically."

        # 2. Check explicitly denied keywords
        if any(kw in cmd_lower for kw in DENY_KEYWORDS):
            log_action(action_type, risk_level="DENY", status="BLOCKED_SECURITY", details=command_text)
            return ActionRiskLevel.DENY, "⛔ Security Block: Action contains prohibited destructive directives."

        # 3. Check risk matrix lookup
        risk_level = ACTION_RISK_MATRIX.get(act_lower, ActionRiskLevel.CONFIRM)

        # 4. Check keyword risk override
        if any(kw in cmd_lower for kw in CONFIRM_KEYWORDS) and risk_level == ActionRiskLevel.SAFE:
            risk_level = ActionRiskLevel.CONFIRM

        if risk_level == ActionRiskLevel.DENY:
            log_action(action_type, risk_level="DENY", status="BLOCKED_POLICY", details=command_text)
            return ActionRiskLevel.DENY, "⛔ Security Block: Action is blocked by system safety policy."

        if risk_level == ActionRiskLevel.CONFIRM:
            return ActionRiskLevel.CONFIRM, f"⚠️ Confirmation required: Executing '{action_type}' will modify OS state."

        return ActionRiskLevel.SAFE, "✅ Action safe for immediate execution."


permission_gate = PermissionGate()
