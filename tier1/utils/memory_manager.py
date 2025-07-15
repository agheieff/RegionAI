"""
Memory management utilities for RegionAI.

This module provides memory monitoring and cleanup functionality
to prevent out-of-memory crashes during large-scale analysis.
"""

import gc
import logging
import psutil
import sys
from typing import Callable
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages memory usage and triggers cleanup when thresholds are exceeded.
    """
    
    def __init__(self, 
                 max_memory_percent: float = 80.0,
                 critical_memory_percent: float = 90.0,
                 check_interval_seconds: int = 30):
        """
        Initialize memory manager.
        
        Args:
            max_memory_percent: Trigger cleanup above this threshold
            critical_memory_percent: Force aggressive cleanup above this
            check_interval_seconds: How often to check memory
        """
        self.max_memory_percent = max_memory_percent
        self.critical_memory_percent = critical_memory_percent
        self.check_interval = timedelta(seconds=check_interval_seconds)
        self.last_check = datetime.now()
        self.cleanup_callbacks = []
        
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called during memory cleanup."""
        self.cleanup_callbacks.append(callback)
        
    def check_memory(self, force: bool = False) -> bool:
        """
        Check memory usage and trigger cleanup if needed.
        
        Args:
            force: Force check regardless of interval
            
        Returns:
            True if cleanup was triggered
        """
        # Check if enough time has passed
        now = datetime.now()
        if not force and (now - self.last_check) < self.check_interval:
            return False
            
        self.last_check = now
        
        # Get current memory usage
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        logger.debug(f"Memory usage: {usage_percent:.1f}% ({memory.used / 1e9:.1f}GB / {memory.total / 1e9:.1f}GB)")
        
        # Determine action based on usage
        if usage_percent >= self.critical_memory_percent:
            logger.warning(f"Critical memory usage: {usage_percent:.1f}%")
            self._aggressive_cleanup()
            return True
        elif usage_percent >= self.max_memory_percent:
            logger.info(f"High memory usage: {usage_percent:.1f}%, triggering cleanup")
            self._normal_cleanup()
            return True
            
        return False
        
    def _normal_cleanup(self) -> None:
        """Perform normal memory cleanup."""
        # Call registered callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
                
        # Force garbage collection
        gc.collect()
        
    def _aggressive_cleanup(self) -> None:
        """Perform aggressive memory cleanup."""
        logger.warning("Performing aggressive memory cleanup")
        
        # Normal cleanup first
        self._normal_cleanup()
        
        # More aggressive GC
        gc.collect(2)  # Full collection
        
        # Log memory usage after cleanup
        memory = psutil.virtual_memory()
        logger.info(f"Memory after cleanup: {memory.percent:.1f}%")
        
        # If still critical, we may need to abort operations
        if memory.percent >= self.critical_memory_percent:
            logger.error("Memory still critical after cleanup!")
            

def memory_limit(max_gb: float = 4.0):
    """
    Decorator to enforce memory limits on functions.
    
    Args:
        max_gb: Maximum memory in gigabytes
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check memory before
            memory_before = psutil.Process().memory_info().rss / 1e9
            
            # Set memory limit
            if sys.platform != 'win32':  # Resource module not available on Windows
                import resource
                max_bytes = int(max_gb * 1e9)
                resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
            
            try:
                result = func(*args, **kwargs)
                
                # Check memory after
                memory_after = psutil.Process().memory_info().rss / 1e9
                memory_used = memory_after - memory_before
                
                if memory_used > 0.1:  # Log if more than 100MB used
                    logger.info(f"{func.__name__} used {memory_used:.1f}GB memory")
                    
                return result
                
            except MemoryError:
                logger.error(f"{func.__name__} exceeded memory limit of {max_gb}GB")
                raise
                
        return wrapper
    return decorator


# Backward compatibility: Create a default instance
# This maintains the old API while encouraging migration to the new pattern
import warnings
from .memory_manager_v2 import (
    create_default_memory_manager, 
    get_current_memory_manager
)

# Default instance for backward compatibility
_default_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """
    Get a memory manager instance.
    
    This function maintains backward compatibility but now:
    1. First checks for a context-local memory manager
    2. Falls back to a default instance if needed
    3. Issues a deprecation warning
    
    New code should use dependency injection or MemoryManagerContext instead.
    """
    # Check for context-local manager first
    context_manager = get_current_memory_manager()
    if context_manager is not None:
        return context_manager
        
    # Fall back to default instance
    global _default_memory_manager
    if _default_memory_manager is None:
        warnings.warn(
            "Using global memory manager is deprecated. "
            "Use dependency injection or MemoryManagerContext instead.",
            DeprecationWarning,
            stacklevel=2
        )
        _default_memory_manager = create_default_memory_manager()
        
    return _default_memory_manager