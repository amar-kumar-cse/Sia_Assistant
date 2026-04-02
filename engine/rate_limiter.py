"""
Rate Limiting Module for Sia Assistant
Prevents API abuse and ensures fair usage.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from .logger import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        self.tokens: Dict[str, Tuple[float, float]] = defaultdict(lambda: (self.requests_per_minute, time.time()))
        # (tokens_available, last_update_time)

    def is_allowed(self, key: str = "default") -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for the rate limit bucket

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        tokens_available, last_update = self.tokens[key]

        # Calculate tokens to add since last update
        time_passed = current_time - last_update
        tokens_to_add = time_passed * self.requests_per_second
        tokens_available = min(self.requests_per_minute, tokens_available + tokens_to_add)

        if tokens_available >= 1:
            # Allow request and consume token
            self.tokens[key] = (tokens_available - 1, current_time)
            return True
        else:
            # Rate limited
            logger.warning(f"Rate limit exceeded for key: {key}")
            return False

    def get_remaining_tokens(self, key: str = "default") -> float:
        """Get remaining tokens for a key."""
        current_time = time.time()
        tokens_available, last_update = self.tokens[key]

        time_passed = current_time - last_update
        tokens_to_add = time_passed * self.requests_per_second
        return min(self.requests_per_minute, tokens_available + tokens_to_add)

# Global rate limiter instances
api_limiter = RateLimiter(requests_per_minute=60)  # Gemini API
voice_limiter = RateLimiter(requests_per_minute=30)  # Voice API
search_limiter = RateLimiter(requests_per_minute=20)  # Search API