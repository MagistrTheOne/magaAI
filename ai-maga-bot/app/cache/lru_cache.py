"""LRU cache implementation for AI-Maga responses."""

import time
import hashlib
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
from app.observability.metrics import metrics_collector


class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items
            ttl_seconds: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = None  # Will be set to threading.Lock if needed
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if item is expired."""
        return time.time() - timestamp > self.ttl_seconds
    
    def _cleanup_expired(self):
        """Remove expired items."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _make_key(self, *args, **kwargs) -> str:
        """Create cache key from arguments."""
        # Create deterministic key from arguments
        key_data = str(sorted(args)) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        
        # Check if expired
        if self._is_expired(timestamp):
            del self.cache[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        current_time = time.time()
        
        # Cleanup expired items if cache is full
        if len(self.cache) >= self.max_size:
            self._cleanup_expired()
            
            # If still full, remove least recently used
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
        
        self.cache[key] = (value, current_time)
    
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """Clear all items."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        self._cleanup_expired()
        return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


class ResponseCache:
    """Response cache for LLM and TTS responses."""
    
    def __init__(self, llm_cache_size: int = 500, tts_cache_size: int = 200, ttl_seconds: int = 3600):
        """
        Initialize response cache.
        
        Args:
            llm_cache_size: LLM cache size
            tts_cache_size: TTS cache size  
            ttl_seconds: Time to live in seconds
        """
        self.llm_cache = LRUCache(max_size=llm_cache_size, ttl_seconds=ttl_seconds)
        self.tts_cache = LRUCache(max_size=tts_cache_size, ttl_seconds=ttl_seconds)
    
    def get_llm_response(self, system_prompt: str, user_message: str, **kwargs) -> Optional[str]:
        """Get cached LLM response."""
        key = self.llm_cache._make_key(system_prompt, user_message, **kwargs)
        response = self.llm_cache.get(key)
        
        if response is not None:
            metrics_collector.record_cache_hit("llm")
        else:
            metrics_collector.record_cache_miss("llm")
        
        return response
    
    def set_llm_response(self, system_prompt: str, user_message: str, response: str, **kwargs) -> None:
        """Cache LLM response."""
        key = self.llm_cache._make_key(system_prompt, user_message, **kwargs)
        self.llm_cache.set(key, response)
    
    def get_tts_response(self, text: str, voice: str, format: str, **kwargs) -> Optional[bytes]:
        """Get cached TTS response."""
        key = self.tts_cache._make_key(text, voice, format, **kwargs)
        response = self.tts_cache.get(key)
        
        if response is not None:
            metrics_collector.record_cache_hit("tts")
        else:
            metrics_collector.record_cache_miss("tts")
        
        return response
    
    def set_tts_response(self, text: str, voice: str, format: str, response: bytes, **kwargs) -> None:
        """Cache TTS response."""
        key = self.tts_cache._make_key(text, voice, format, **kwargs)
        self.tts_cache.set(key, response)
    
    def clear_llm_cache(self):
        """Clear LLM cache."""
        self.llm_cache.clear()
    
    def clear_tts_cache(self):
        """Clear TTS cache."""
        self.tts_cache.clear()
    
    def clear_all(self):
        """Clear all caches."""
        self.llm_cache.clear()
        self.tts_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "llm_cache": self.llm_cache.stats(),
            "tts_cache": self.tts_cache.stats()
        }


# Global cache instance
response_cache = ResponseCache()
