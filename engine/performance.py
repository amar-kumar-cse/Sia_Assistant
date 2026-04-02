"""
Performance Optimization Module for Sia Assistant
Enhanced memory management, caching, and resource optimization
"""

import gc
import psutil
import threading
import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
import weakref
from .logger import get_logger

logger = get_logger(__name__)

class LRUCache:
    """Thread-safe LRU Cache with memory limits."""
    
    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.current_memory = 0
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> bool:
        with self.lock:
            # Estimate memory usage
            value_size = len(str(value)) if isinstance(value, str) else 1024
            
            # Remove old items if necessary
            while (len(self.cache) >= self.max_size or 
                   self.current_memory + value_size > self.max_memory_bytes):
                if not self.cache:
                    break
                old_key, old_value = self.cache.popitem(last=False)
                self.current_memory -= len(str(old_value)) if isinstance(old_value, str) else 1024
            
            # Add new item
            if len(self.cache) < self.max_size:
                self.cache[key] = value
                self.current_memory += value_size
                return True
            return False
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.current_memory = 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'size': len(self.cache),
                'memory_mb': self.current_memory / (1024 * 1024)
            }

class MemoryManager:
    """Advanced memory management for Sia Assistant."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.memory_cache = LRUCache(max_size=50, max_memory_mb=50)
        self.cleanup_thread = None
        self.running = False
    
    def start_monitoring(self):
        """Start memory monitoring thread."""
        if not self.running:
            self.running = True
            self.cleanup_thread = threading.Thread(target=self._memory_monitor, daemon=True)
            self.cleanup_thread.start()
            logger.info("✅ Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring thread."""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=1)
    
    def _memory_monitor(self):
        """Background memory monitoring and cleanup."""
        while self.running:
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                # Trigger cleanup if memory usage is high
                if memory_mb > 500:  # 500MB threshold
                    logger.warning(f"⚠️ High memory usage: {memory_mb:.1f}MB")
                    self.perform_cleanup()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Memory monitor error: {e}")
                time.sleep(60)
    
    def perform_cleanup(self):
        """Perform aggressive memory cleanup."""
        try:
            # Clear caches
            self.memory_cache.clear()
            
            # Force garbage collection
            collected = gc.collect()
            
            # Log cleanup results
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            logger.info(f"🧹 Memory cleanup: {collected} objects collected, {memory_mb:.1f}MB used")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            return {
                'memory_mb': memory_info.rss / (1024 * 1024),
                'memory_vms_mb': memory_info.vms / (1024 * 1024),
                'cpu_percent': cpu_percent,
                'cache_stats': self.memory_cache.get_stats()
            }
        except Exception as e:
            logger.error(f"❌ Memory stats error: {e}")
            return {}

class ResourcePool:
    """Resource pooling for expensive objects."""
    
    def __init__(self):
        self.pools = {}
        self.lock = threading.RLock()
    
    def get_resource(self, resource_type: str, factory_func):
        """Get resource from pool or create new one."""
        with self.lock:
            if resource_type not in self.pools:
                self.pools[resource_type] = []
            
            pool = self.pools[resource_type]
            
            # Try to get from pool
            while pool:
                resource = pool.pop()
                if self._is_resource_valid(resource):
                    return resource
            
            # Create new resource
            return factory_func()
    
    def return_resource(self, resource_type: str, resource):
        """Return resource to pool."""
        with self.lock:
            if resource_type not in self.pools:
                self.pools[resource_type] = []
            
            # Limit pool size
            pool = self.pools[resource_type]
            if len(pool) < 10:  # Max 10 resources per type
                pool.append(resource)
    
    def _is_resource_valid(self, resource) -> bool:
        """Check if resource is still valid."""
        try:
            # Basic validity check - can be extended
            return resource is not None
        except:
            return False

# Global instances
memory_manager = MemoryManager()
resource_pool = ResourcePool()

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # Log slow functions
                logger.warning(f"⏱️ Slow function: {func.__name__} took {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Function {func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper

# Initialize performance optimization
def initialize_optimization():
    """Initialize performance optimization systems."""
    memory_manager.start_monitoring()
    logger.info("✅ Performance optimization initialized")

def shutdown_optimization():
    """Shutdown performance optimization systems."""
    memory_manager.stop_monitoring()
    memory_manager.perform_cleanup()
    logger.info("✅ Performance optimization shutdown")
