"""
LLM Response Cache Manager for Sia Assistant.
Provides fast MD5/SHA256 query-hashed response caching to minimize duplicate API costs & latency.
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any
from .logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """File-backed & in-memory cache manager for LLM responses."""

    def __init__(self, cache_dir: Optional[str] = None, ttl_seconds: int = 86400):
        if not cache_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, "cache")
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self.cache_dir, exist_ok=True)

    def _hash_key(self, prompt: str) -> str:
        clean = prompt.strip().lower()
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    def get(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available and not expired."""
        key = self._hash_key(prompt)

        # Check in-memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                logger.info("⚡ Response retrieved from RAM cache")
                return entry["data"]
            else:
                del self._memory_cache[key]

        # Check disk cache
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if time.time() - entry.get("timestamp", 0) < self.ttl_seconds:
                    self._memory_cache[key] = entry
                    logger.info("💾 Response retrieved from Disk cache")
                    return entry.get("data")
                else:
                    os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to read cache file {filepath}: {e}")

        return None

    def set(self, prompt: str, data: Dict[str, Any]) -> None:
        """Store response data in cache."""
        key = self._hash_key(prompt)
        entry = {
            "timestamp": time.time(),
            "prompt": prompt,
            "data": data
        }
        self._memory_cache[key] = entry
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache file {filepath}: {e}")

    def clear(self) -> None:
        """Purge all cache entries."""
        self._memory_cache.clear()
        if os.path.exists(self.cache_dir):
            for fname in os.listdir(self.cache_dir):
                if fname.endswith(".json"):
                    try:
                        os.remove(os.path.join(self.cache_dir, fname))
                    except Exception:
                        pass


cache_manager = CacheManager()
