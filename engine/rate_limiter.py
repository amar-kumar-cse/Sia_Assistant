"""
Rate Limiting Module for Sia Assistant
Prevents API abuse and ensures fair usage.

Free Tier Limits (as of 2025):
  - Gemini 1.5 Flash : 15 RPM  → we use 14 to be safe
  - Gemini 2.0 Flash : 15 RPM  → same
  - ElevenLabs Free  : ~12 RPM → we use 10 to be safe
  - DuckDuckGo Search: No official limit, we self-limit to 20 RPM
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 14):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        # (tokens_available, last_update_time)
        self.tokens: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(self.requests_per_minute), time.time())
        )

    def is_allowed(self, key: str = "default") -> bool:
        """
        Check if a request is allowed under the rate limit.

        Returns:
            True if allowed, False if rate-limited.
        """
        current_time = time.time()
        tokens_available, last_update = self.tokens[key]

        # Refill tokens based on elapsed time
        elapsed = current_time - last_update
        tokens_available = min(
            float(self.requests_per_minute),
            tokens_available + elapsed * self.requests_per_second,
        )

        if tokens_available >= 1.0:
            self.tokens[key] = (tokens_available - 1.0, current_time)
            return True

        logger.warning(
            "Rate limit exceeded for key '%s'. "
            "%.1f seconds until next token.",
            key,
            (1.0 - tokens_available) / self.requests_per_second,
        )
        return False

    def get_remaining_tokens(self, key: str = "default") -> float:
        """Get current remaining tokens (may be fractional)."""
        current_time = time.time()
        tokens_available, last_update = self.tokens[key]
        elapsed = current_time - last_update
        return min(
            float(self.requests_per_minute),
            tokens_available + elapsed * self.requests_per_second,
        )

    def seconds_until_allowed(self, key: str = "default") -> float:
        """How many seconds until the next request will be allowed."""
        remaining = self.get_remaining_tokens(key)
        if remaining >= 1.0:
            return 0.0
        return (1.0 - remaining) / self.requests_per_second


# ── Global instances ─────────────────────────────────────────
# Gemini free tier: 15 RPM → use 14 to be safe
api_limiter = RateLimiter(requests_per_minute=14)

# ElevenLabs free tier: ~12 RPM → use 10
voice_limiter = RateLimiter(requests_per_minute=10)

# DuckDuckGo / web search: self-imposed limit
search_limiter = RateLimiter(requests_per_minute=20)