import os
import subprocess
import webbrowser
import urllib.parse
import platform
from typing import List


def _run_command(cmd):
    """Run a subprocess command and return (code, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


_SAFE_GIT_COMMANDS = {
    "status": ["git", "status", "--short"],
    "log": ["git", "log", "--oneline", "-n", "20"],
    "diffstat": ["git", "diff", "--stat"],
    "branch": ["git", "branch", "--show-current"],
    "remote": ["git", "remote", "-v"],
}


def run_safe_git(operation: str) -> str:
    """Read-only git sandbox for v1."""
    op = (operation or "").strip().lower()
    if op not in _SAFE_GIT_COMMANDS:
        return "❌ Unsupported git operation in v1 sandbox."
    code, out, err = _run_command(_SAFE_GIT_COMMANDS[op])
    if code != 0:
        return f"❌ Git {op} failed: {err[:160]}"
    return out or f"ℹ️ git {op}: no output"

def git_commit_push(commit_msg="Auto-commit via Sia", require_confirmation: bool = False):
    """
    Automatically adds, commits, and pushes to the current Git repository.
    """
    return "❌ Disabled in v1 sandbox: write git operations are not allowed."

def setup_python_env(require_confirmation: bool = False):
    """
    Creates a Python virtual environment and installs requirements.txt if present.
    """
    return "❌ Disabled in v1 sandbox: environment-changing operations are blocked."

def draft_email(
    subject="Update from Amar",
    body="Hello, this is an automated message drafted by Sia.",
    require_confirmation: bool = False,
):
    """
    Drafts an email using the system's default mail client (mailto: protocol).
    """
    return "❌ Disabled in v1 sandbox: email automation requires manual preview flow outside dev_tools."
