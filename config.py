"""
Configuration Module for Sia Assistant
Centralized configuration with multi-API-key rotation support.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()


def _parse_key_list(env_var: str) -> List[str]:
    """
    Parse one or more API keys from a comma-separated env variable.
    Example: GEMINI_API_KEY=key1,key2,key3
    Also checks GEMINI_API_KEY_2, GEMINI_API_KEY_3 for backward compatibility.
    """
    base_key = os.getenv(env_var, "").strip()
    keys: List[str] = []

    # Support comma-separated keys in the primary var
    for k in base_key.split(","):
        k = k.strip()
        if k and "your_" not in k.lower():
            keys.append(k)

    # Also support _2, _3 suffix slots
    for i in range(2, 6):
        extra = os.getenv(f"{env_var}_{i}", "").strip()
        if extra and "your_" not in extra.lower():
            keys.append(extra)

    return keys


@dataclass
class Config:
    """Application configuration with validation and multi-key rotation."""

    # ── Primary API key (first valid key from the list) ──────────────
    GEMINI_API_KEY: Optional[str] = field(
        default_factory=lambda: _parse_key_list("GEMINI_API_KEY")[0]
        if _parse_key_list("GEMINI_API_KEY") else None
    )

    # ── All available Gemini keys (for rotation) ─────────────────────
    GEMINI_API_KEYS: List[str] = field(
        default_factory=lambda: _parse_key_list("GEMINI_API_KEY")
    )

    # ── ElevenLabs ───────────────────────────────────────────────────
    ELEVENLABS_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("ELEVENLABS_API_KEY")
        if "your_" not in os.getenv("ELEVENLABS_API_KEY", "your_") else None
    )

    # ── Voice Settings ────────────────────────────────────────────────
    ELEVENLABS_VOICE_ID: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )
    ELEVENLABS_MODEL: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2")
    )

    # ── AI Model Settings ─────────────────────────────────────────────
    # Primary model: gemini-1.5-flash (most stable free-tier model)
    GEMINI_PRIMARY_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_PRIMARY_MODEL", "gemini-1.5-flash")
    )
    GEMINI_FALLBACK_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")
    )
    GEMINI_LAST_RESORT_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_LAST_RESORT_MODEL", "gemini-1.5-pro")
    )

    OLLAMA_URL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    )
    OLLAMA_MODEL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3")
    )

    # ── Voice Recognition ─────────────────────────────────────────────
    VOICE_ENERGY_THRESHOLD: int = 300

    # ── Rate Limiting (aligned with free-tier limits) ─────────────────
    API_RATE_LIMIT_PER_MINUTE: int = 14   # Gemini free tier: 15 RPM, use 14 safely
    VOICE_RATE_LIMIT_PER_MINUTE: int = 10  # ElevenLabs free tier
    SEARCH_RATE_LIMIT_PER_MINUTE: int = 20  # DuckDuckGo (self-imposed)

    # ── Paths ─────────────────────────────────────────────────────────
    BASE_DIR: str = field(init=False)
    ENGINE_DIR: str = field(init=False)
    ASSETS_DIR: str = field(init=False)
    CACHE_DIR: str = field(init=False)
    DB_PATH: str = field(init=False)

    def __post_init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.ENGINE_DIR = os.path.join(self.BASE_DIR, "engine")
        self.ASSETS_DIR = os.path.join(self.BASE_DIR, "assets")
        self.CACHE_DIR = os.path.join(self.BASE_DIR, "cache")
        self.DB_PATH = os.path.join(self.BASE_DIR, "memory.db")

        os.makedirs(self.CACHE_DIR, exist_ok=True)
        os.makedirs(self.ASSETS_DIR, exist_ok=True)

    def validate(self) -> bool:
        """Validate configuration and log meaningful warnings."""
        import logging
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger(__name__)

        if not self.GEMINI_API_KEYS:
            logger.error(
                "❌ No valid GEMINI_API_KEY found in .env! "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
            return False

        if len(self.GEMINI_API_KEYS) == 1:
            logger.warning(
                "⚠️  Only 1 Gemini API key configured. "
                "Add GEMINI_API_KEY_2 etc. in .env for rotation when quota runs out."
            )

        if not self.ELEVENLABS_API_KEY:
            logger.info(
                "ℹ️  ElevenLabs key not set — using free Edge-TTS for voice (perfectly fine)."
            )

        return True


# Global config instance
config = Config()
config.validate()
