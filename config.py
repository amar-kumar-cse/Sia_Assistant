"""
Configuration Module for Sia Assistant
Centralized configuration management with validation.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load Environment Variables securely
load_dotenv()

@dataclass
class Config:
    """Application configuration with validation."""

    # API Keys
    GEMINI_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    ELEVENLABS_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))

    # Voice Settings
    ELEVENLABS_VOICE_ID: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"))
    ELEVENLABS_MODEL: str = field(default_factory=lambda: os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2"))

    # AI Model Settings
    OLLAMA_URL: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"))
    OLLAMA_MODEL: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))

    # Voice Recognition
    VOICE_ENERGY_THRESHOLD: int = 300

    # Rate Limiting
    API_RATE_LIMIT_PER_MINUTE: int = 60
    VOICE_RATE_LIMIT_PER_MINUTE: int = 30
    SEARCH_RATE_LIMIT_PER_MINUTE: int = 20

    # Paths
    BASE_DIR: str = field(init=False)
    ENGINE_DIR: str = field(init=False)
    ASSETS_DIR: str = field(init=False)
    CACHE_DIR: str = field(init=False)
    DB_PATH: str = field(init=False)

    def __post_init__(self):
        """Initialize paths after dataclass creation."""
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.ENGINE_DIR = os.path.join(self.BASE_DIR, "engine")
        self.ASSETS_DIR = os.path.join(self.BASE_DIR, "assets")
        self.CACHE_DIR = os.path.join(self.BASE_DIR, "cache")
        self.DB_PATH = os.path.join(self.BASE_DIR, "memory.db")

        # Create directories
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        os.makedirs(self.ASSETS_DIR, exist_ok=True)

    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []

        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY not set - AI features will be limited")

        if self.VOICE_ENERGY_THRESHOLD < 0:
            errors.append("VOICE_ENERGY_THRESHOLD must be non-negative")

        if self.API_RATE_LIMIT_PER_MINUTE <= 0:
            errors.append("API_RATE_LIMIT_PER_MINUTE must be positive")

        if errors:
            import logging
            logging.basicConfig(level=logging.ERROR)
            logger = logging.getLogger(__name__)
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True

# Global configuration instance
config = Config()
# Log validation warnings but don't crash
config.validate()
