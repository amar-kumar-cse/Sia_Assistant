"""
Secure Keyring / Keychain Manager for Sia Assistant.
Provides OS Credential Manager storage for API keys with fallback to .env file.
"""

import os
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "SiaAssistant"


class KeychainManager:
    """Interface to OS Credential Manager (keyring) with environment fallback."""

    def __init__(self):
        self._keyring_available = False
        try:
            import keyring
            self._keyring = keyring
            self._keyring_available = True
            logger.info("🔑 Keyring service active (OS Credential Store enabled)")
        except ImportError:
            logger.info("ℹ️ keyring library not installed — using environment file fallback")
            self._keyring = None

    def set_api_key(self, key_name: str, secret_value: str) -> bool:
        """Store API key into OS keychain or fallback to env."""
        if self._keyring_available:
            try:
                self._keyring.set_password(SERVICE_NAME, key_name, secret_value)
                logger.info(f"🔒 Stored {key_name} in OS Credential Store")
                return True
            except Exception as e:
                logger.warning(f"Failed to store key in keyring: {e}")
        return False

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Retrieve API key from OS keychain or environment."""
        if self._keyring_available:
            try:
                val = self._keyring.get_password(SERVICE_NAME, key_name)
                if val:
                    return val
            except Exception as e:
                logger.warning(f"Failed reading key from keyring: {e}")
        
        # Fallback to environment variable
        return os.getenv(key_name)

    def delete_api_key(self, key_name: str) -> bool:
        """Remove key from OS keychain."""
        if self._keyring_available:
            try:
                self._keyring.delete_password(SERVICE_NAME, key_name)
                return True
            except Exception:
                pass
        return False


keychain = KeychainManager()
