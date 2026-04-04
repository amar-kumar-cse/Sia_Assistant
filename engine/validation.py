"""
Input Validation Module for Sia Assistant
Provides secure input sanitization and validation functions.
"""

import os
import re
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)

def sanitize_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user input to prevent injection attacks and ensure safety.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text string

    Raises:
        ValueError: If input is invalid
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]

    # Remove null bytes and control characters (except newlines and tabs)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

    # Remove potentially dangerous patterns
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    return text.strip()

def validate_file_path(filepath: str) -> bool:
    """
    Validate that a file path is safe and exists.
    Uses pathlib for cross-platform path handling.

    Args:
        filepath: File path to validate (supports absolute and relative paths)

    Returns:
        True if path is valid and safe
    """
    if not filepath or not isinstance(filepath, str):
        return False

    try:
        import pathlib
        
        # ✅ Use pathlib for cross-platform path handling
        path = pathlib.Path(filepath).resolve()
        
        # ✅ Only block actual directory traversal attempts
        # (not absolute paths which are legitimate)
        if ".." in str(path.relative_to(path.anchor)):
            logger.warning(f"Directory traversal attempt detected: {filepath}")
            return False
        
        # ✅ Check if file exists and is readable
        if not path.exists():
            logger.debug(f"File does not exist: {filepath}")
            return False
        
        if not path.is_file():
            logger.debug(f"Path is not a file: {filepath}")
            return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Invalid file path: {filepath} - {e}")
        return False

def sanitize_command(command: str) -> Optional[str]:
    """
    Sanitize shell commands to prevent injection attacks.
    Only blocks shell redirection, command substitution, and destructive commands.

    Args:
        command: Command string to sanitize

    Returns:
        Sanitized command or None if unsafe
    """
    if not command or not isinstance(command, str):
        return None

    # ✅ Only block shell redirection and execution patterns
    # (not legitimate characters like parentheses in function calls)
    dangerous_patterns = [
        r'[;&|`]\s*(?:rm|del|format|fdisk|deltree)',  # Shell + destructive commands
        r'\$\(.*\)|`.*`',  # Command substitution: $(cmd) or `cmd`
        r'>\s*[\\/]',  # Redirect to device: > /dev/null or > COM1
        r'<\s*(?:con|prn|aux|nul)',  # Input from device (Windows)
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f"Dangerous pattern detected in command: {command}")
            return None

    return command.strip()