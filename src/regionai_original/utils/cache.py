"""
Cache implementations with memory management for RegionAI.

This module provides caching utilities that automatically manage
memory usage to prevent out-of-memory conditions.
"""

import ast
import hashlib
import logging
import sys
from collections import OrderedDict
from typing import Optional, Any, Dict
from functools import wraps
from .memory_manager import get_memory_manager

logger = logging.getLogger(__name__)


class BoundedCache:
    """
    LRU cache with memory bounds and automatic eviction.
    """
    
    def __init__(self, 
                 max_items: int = 1000,
                 max_memory_mb: float = 500.0,
                 name: str = "cache",
                 memory_manager=None):
        """
        Initialize bounded cache.
        
        Args:
            max_items: Maximum number of items to cache
            max_memory_mb: Maximum memory usage in MB
            name: Name for logging
            memory_manager: Optional memory manager for cleanup callbacks
        """
        self.max_items = max_items
        self.max_memory_mb = max_memory_mb
        self.name = name
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._sizes: Dict[str, int] = {}
        self._total_size = 0
        self._hits = 0
        self._misses = 0
        
        # Register cleanup callback
        if memory_manager:
            memory_manager.register_cleanup_callback(self.cleanup)
        else:
            # Fallback to global for backward compatibility
            get_memory_manager().register_cleanup_callback(self.cleanup)
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key in self._cache:
            self._hits += 1
            # Move to end (most recent)
            self._cache.move_to_end(key)
            return self._cache[key]
        else:
            self._misses += 1
            return None
            
    def put(self, key: str, value: Any, size_bytes: Optional[int] = None) -> None:
        """
        Put item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            size_bytes: Size in bytes (estimated if not provided)
        """
        # Estimate size if not provided
        if size_bytes is None:
            size_bytes = sys.getsizeof(value)
            
        # Check if we need to evict items
        while (len(self._cache) >= self.max_items or 
               self._total_size + size_bytes > self.max_memory_mb * 1e6):
            if not self._cache:
                logger.warning(f"{self.name}: Cannot cache item, size too large")
                return
            self._evict_oldest()
            
        # Add to cache
        self._cache[key] = value
        self._sizes[key] = size_bytes
        self._total_size += size_bytes
        
    def _evict_oldest(self) -> None:
        """Evict oldest item from cache."""
        if not self._cache:
            return
            
        # Get oldest key (first item)
        oldest_key = next(iter(self._cache))
        self._cache.pop(oldest_key)
        size = self._sizes.pop(oldest_key, 0)
        self._total_size -= size
        
        logger.debug(f"{self.name}: Evicted {oldest_key} ({size} bytes)")
        
    def cleanup(self, target_percent: float = 50.0) -> None:
        """
        Clean up cache to target size.
        
        Args:
            target_percent: Target size as percentage of max
        """
        target_items = int(self.max_items * target_percent / 100)
        target_size = self.max_memory_mb * target_percent / 100 * 1e6
        
        evicted = 0
        while (len(self._cache) > target_items or 
               self._total_size > target_size) and self._cache:
            self._evict_oldest()
            evicted += 1
            
        if evicted > 0:
            logger.info(f"{self.name}: Evicted {evicted} items during cleanup")
            
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._sizes.clear()
        self._total_size = 0
        logger.info(f"{self.name}: Cleared")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            'name': self.name,
            'items': len(self._cache),
            'size_mb': self._total_size / 1e6,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'max_items': self.max_items,
            'max_memory_mb': self.max_memory_mb
        }


# Global caches for expensive operations
# Note: These use the global memory manager for backward compatibility
# New code should create caches with explicit memory manager
_ast_cache = BoundedCache(max_items=500, max_memory_mb=100, name="AST")
_analysis_cache = BoundedCache(max_items=1000, max_memory_mb=200, name="Analysis")


def cached_ast_parse(code: str) -> Optional[ast.AST]:
    """
    Parse Python code with caching.
    
    Args:
        code: Python source code
        
    Returns:
        AST or None if parsing fails
    """
    # Create cache key
    cache_key = hashlib.md5(code.encode()).hexdigest()
    
    # Check cache
    cached = _ast_cache.get(cache_key)
    if cached is not None:
        return cached
        
    # Parse
    try:
        tree = ast.parse(code)
        _ast_cache.put(cache_key, tree, len(code) * 10)  # Rough estimate
        return tree
    except SyntaxError as e:
        logger.debug(f"Failed to parse code: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing code: {e}")
        return None


def memoize_with_limit(max_cache_size: int = 100, memory_manager=None):
    """
    Decorator for memoization with size limits.
    
    Args:
        max_cache_size: Maximum number of cached results
        memory_manager: Optional memory manager for cleanup callbacks
    """
    def decorator(func):
        cache = BoundedCache(
            max_items=max_cache_size,
            max_memory_mb=50,
            name=f"memoize_{func.__name__}",
            memory_manager=memory_manager
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            cache_key = str((args, tuple(sorted(kwargs.items()))))
            
            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result
                
            # Compute result
            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            return result
            
        # Add cache management methods
        wrapper.clear_cache = cache.clear
        wrapper.get_cache_stats = cache.get_stats
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all global caches."""
    return {
        'ast_cache': _ast_cache.get_stats(),
        'analysis_cache': _analysis_cache.get_stats()
    }