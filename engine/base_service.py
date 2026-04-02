"""
Base Service Module for Sia Assistant
Provides common functionality and error handling for all services.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from .logger import get_logger


class BaseService(ABC):
    """Base class for all service modules with common error handling."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"engine.{service_name}")

    def _handle_error(self, error: Exception, context: str, default_message: str = "Operation failed") -> str:
        """
        Standardized error handling for all services.

        Args:
            error: The exception that occurred
            context: Context where the error occurred
            default_message: Default error message to return

        Returns:
            Formatted error message
        """
        error_msg = f"{self.service_name} {context} failed: {str(error)}"
        self.logger.error(error_msg, exc_info=True)
        return f"❌ {default_message}: {str(error)[:50]}..."

    def _validate_input(self, input_data: Any, input_type: type, field_name: str) -> bool:
        """
        Validate input data type.

        Args:
            input_data: Data to validate
            input_type: Expected type
            field_name: Name of the field for error messages

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(input_data, input_type):
            self.logger.warning(f"Invalid {field_name} type: expected {input_type.__name__}, got {type(input_data).__name__}")
            return False
        return True

    def _sanitize_string(self, text: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.

        Args:
            text: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return ""

        # Truncate if too long
        if len(text) > max_length:
            self.logger.warning(f"String truncated from {len(text)} to {max_length} characters")
            text = text[:max_length]

        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

        return text.strip()

    @abstractmethod
    def health_check(self) -> bool:
        """
        Health check for the service.

        Returns:
            True if service is healthy, False otherwise
        """
        pass