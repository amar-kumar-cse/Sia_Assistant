"""
Agentic Multi-Step Task Planner for Sia Assistant.
Decomposes complex multi-goal user directives into ordered sub-task plans
and evaluates each sub-task against the PermissionGate before execution.
"""

from typing import List, Dict, Any
from .logger import get_logger
from .permission_gate import permission_gate, ActionRiskLevel
from .action_handler import action_handler

logger = get_logger(__name__)


class AgenticTaskStep:
    def __init__(self, step_number: int, action_type: str, command: str, description: str):
        self.step_number = step_number
        self.action_type = action_type
        self.command = command
        self.description = description
        self.status = "PENDING"
        self.result: Any = None
        self.risk_level: ActionRiskLevel = ActionRiskLevel.SAFE
        self.risk_reason: str = ""


class AgenticPlanner:
    def decompose_prompt(self, user_prompt: str) -> List[AgenticTaskStep]:
        prompt_lower = user_prompt.lower().strip()
        steps: List[AgenticTaskStep] = []
        step_counter = 1

        if "briefing" in prompt_lower or "morning" in prompt_lower:
            steps.append(AgenticTaskStep(step_counter, "generate_daily_briefing", "", "Generate briefing"))
            step_counter += 1

        if "weather" in prompt_lower or "mausam" in prompt_lower:
            steps.append(AgenticTaskStep(step_counter, "weather", "Roorkee", "Fetch weather"))
            step_counter += 1

        if "news" in prompt_lower or "khabar" in prompt_lower:
            steps.append(AgenticTaskStep(step_counter, "news", "India technology", "Fetch news"))
            step_counter += 1

        if "system" in prompt_lower or "cpu" in prompt_lower:
            steps.append(AgenticTaskStep(step_counter, "system_info", "", "Check system info"))
            step_counter += 1

        if not steps:
            steps.append(AgenticTaskStep(1, "chat", user_prompt, f"Process directive: {user_prompt}"))

        return steps

    def execute_plan(self, steps: List[AgenticTaskStep]) -> List[Dict[str, Any]]:
        execution_report = []
        for step in steps:
            risk, reason = permission_gate.evaluate_action(step.action_type, step.command, source="agentic_planner")
            step.risk_level = risk
            step.risk_reason = reason

            if risk == ActionRiskLevel.DENY:
                step.status = "BLOCKED_SECURITY"
                step.result = f"Blocked by safety policy: {reason}"
                logger.warning(f"[AgenticPlanner] Step {step.step_number} DENIED: {reason}")
                execution_report.append({
                    "step": step.step_number,
                    "action": step.action_type,
                    "status": step.status,
                    "result": step.result,
                })
                break
            elif risk == ActionRiskLevel.CONFIRM:
                step.status = "PENDING_CONFIRMATION"
                step.result = f"Requires explicit consent: {reason}"
                execution_report.append({
                    "step": step.step_number,
                    "action": step.action_type,
                    "status": step.status,
                    "result": step.result,
                })
                break
            else:
                try:
                    res = action_handler.execute(step.action_type, step.command, source="agentic_planner")
                    step.status = "COMPLETED"
                    step.result = res or "Step completed"
                except Exception as e:
                    step.status = "FAILED"
                    step.result = f"Error: {e}"
                execution_report.append({
                    "step": step.step_number,
                    "action": step.action_type,
                    "status": step.status,
                    "result": step.result,
                })

        return execution_report


agentic_planner = AgenticPlanner()
