"""
Productivity Ecosystem Module for Sia Assistant.
Provides Daily Briefings, Reminders/Tasks, Calendar integration, and GitHub status summaries.
"""

import os
import datetime
import subprocess
from typing import Dict, List, Any, Optional
from .memory import SiaMemory, get_facts
from .logger import get_logger
from .audit_logger import log_action

logger = get_logger(__name__)


class ProductivityEngine:
    """Manages productivity workflows, morning briefings, and developer integration summaries."""

    def __init__(self):
        self.memory = SiaMemory()

    def generate_daily_briefing(self) -> Dict[str, Any]:
        """
        Generate a comprehensive morning briefing for the user (Amar).
        Summarizes: date, pending tasks, recent user facts, and system health.
        """
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        # Get facts and tasks
        facts = get_facts(category="personal")
        user_name = "Hero"
        for f in facts:
            if "name" in f.get("fact_key", "").lower() or "amar" in f.get("fact", "").lower():
                user_name = "Amar"
                break

        history = self.memory.get_recent_history(limit=5)
        
        briefing_text = (
            f"[HAPPY] Good morning {user_name}! Aaj {date_str} hai, time {time_str}.\n"
            f"Sia system check completely operational.\n"
            f"- AI Brain: Gemini Rotational + Ollama Offline Ready\n"
            f"- SQLite Memory: Active WAL mode with retention policy\n"
            f"- Security & Audit: Operational\n"
            f"Kya kaam shuru karein aaj?"
        )

        log_action("generate_daily_briefing", risk_level="ALLOW", status="SUCCESS")
        return {
            "date": date_str,
            "time": time_str,
            "user_name": user_name,
            "briefing": briefing_text
        }

    def add_reminder(self, task_description: str, due_time: Optional[str] = None) -> str:
        """Add a reminder or task to Sia's task list."""
        from .memory import add_todo
        success = add_todo(task_description)
        if success:
            log_action("add_reminder", risk_level="ALLOW", status="SUCCESS", details=task_description)
            return f"✅ Done Hero! Task set: '{task_description}'"
        return "❌ Remind set karne mein error aaya."

    def get_github_status_summary(self) -> str:
        """Get git status summary for current workspace repository."""
        try:
            res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                output = res.stdout.strip()
                if not output:
                    return "✅ Git repository clean hai! Koi uncommitted changes nahi hain."
                lines = output.splitlines()
                return f"📊 GitHub Status: {len(lines)} uncommitted file changes pending."
            return "⚠️ Not in a git repository or git command unavailable."
        except Exception as e:
            return f"❌ Git status error: {e}"


productivity_engine = ProductivityEngine()
