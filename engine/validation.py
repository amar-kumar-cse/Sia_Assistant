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

    Args:
        filepath: File path to validate

    Returns:
        True if path is valid and safe
    """
    if not filepath or not isinstance(filepath, str):
        return False

    # Check for directory traversal attempts
    if '..' in filepath or filepath.startswith('/'):
        logger.warning(f"Potentially unsafe file path: {filepath}")
        return False

    # Check if file exists
    if not os.path.exists(filepath):
        return False

    return True

def sanitize_command(command: str) -> Optional[str]:
    """
    Sanitize shell commands to prevent injection.

    Args:
        command: Command string to sanitize

    Returns:
        Sanitized command or None if unsafe
    """
    if not command or not isinstance(command, str):
        return None

    # Remove dangerous characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    for char in dangerous_chars:
        if char in command:
            logger.warning(f"Dangerous character '{char}' found in command: {command}")
            return None

    return command.strip()