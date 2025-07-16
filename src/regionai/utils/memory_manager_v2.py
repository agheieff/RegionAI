"""
Memory management utilities for RegionAI - Version 2.

This module provides memory monitoring and cleanup functionality
to prevent out-of-memory crashes during large-scale analysis.
Refactored to avoid global singleton pattern.
"""

import gc
import logging
import psutil
import sys
import threading
from typing import Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages memory usage and triggers cleanup when thresholds are exceeded.
    
    This is now a regular class that can be instantiated and passed
    as a dependency, avoiding global state issues.
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
        self._lock = threading.RLock()  # For thread safety
        
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called during memory cleanup."""
        with self._lock:
            self.cleanup_callbacks.append(callback)
        
    def unregister_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a cleanup callback."""
        with self._lock:
            try:
                self.cleanup_callbacks.remove(callback)
            except ValueError:
                pass  # Callback not registered
        
    def check_memory(self, force: bool = False) -> bool:
        """
        Check memory usage and trigger cleanup if needed.
        
        Args:
            force: Force check regardless of interval
            
        Returns:
            True if cleanup was triggered
        """
        with self._lock:
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
        # Get callbacks snapshot to avoid holding lock during cleanup
        with self._lock:
            callbacks = list(self.cleanup_callbacks)
            
        # Call registered callbacks
        for callback in callbacks:
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
            
    @contextmanager
    def monitor_scope(self, scope_name: str):
        """
        Context manager to monitor memory usage in a scope.
        
        Args:
            scope_name: Name of the scope for logging
            
        Usage:
            with memory_manager.monitor_scope("analysis"):
                # Memory intensive operations
        """
        # Check memory at start
        memory_before = psutil.Process().memory_info().rss / 1e9
        self.check_memory()
        
        try:
            yield self
        finally:
            # Check memory at end
            memory_after = psutil.Process().memory_info().rss / 1e9
            memory_used = memory_after - memory_before
            
            if memory_used > 0.1:  # Log if more than 100MB used
                logger.info(f"{scope_name} used {memory_used:.1f}GB memory")
                
            # Check if cleanup needed
            self.check_memory()


class MemoryLimiter:
    """
    Provides memory limiting functionality without global state.
    """
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Initialize memory limiter.
        
        Args:
            memory_manager: Memory manager to use for cleanup
        """
        self.memory_manager = memory_manager
        
    def limit(self, max_gb: float = 4.0):
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
                
                # Set memory limit (Unix only)
                if sys.platform != 'win32':  # Resource module not available on Windows
                    import resource
                    max_bytes = int(max_gb * 1e9)
                    old_limit = resource.getrlimit(resource.RLIMIT_AS)
                    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
                
                try:
                    # Check memory with manager if available
                    if self.memory_manager:
                        self.memory_manager.check_memory()
                        
                    result = func(*args, **kwargs)
                    
                    # Check memory after
                    memory_after = psutil.Process().memory_info().rss / 1e9
                    memory_used = memory_after - memory_before
                    
                    if memory_used > 0.1:  # Log if more than 100MB used
                        logger.info(f"{func.__name__} used {memory_used:.1f}GB memory")
                        
                    return result
                    
                except MemoryError:
                    logger.error(f"{func.__name__} exceeded memory limit of {max_gb}GB")
                    # Try cleanup before re-raising
                    if self.memory_manager:
                        self.memory_manager._aggressive_cleanup()
                    raise
                    
                finally:
                    # Restore memory limit
                    if sys.platform != 'win32':
                        resource.setrlimit(resource.RLIMIT_AS, old_limit)
                        
            return wrapper
        return decorator


# Thread-local storage for memory managers
_thread_local = threading.local()


class MemoryManagerContext:
    """
    Context manager for scoped memory management.
    
    This allows different parts of the application to use
    their own memory manager instances.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self._previous = None
        
    def __enter__(self):
        self._previous = getattr(_thread_local, 'memory_manager', None)
        _thread_local.memory_manager = self.memory_manager
        return self.memory_manager
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._previous is None:
            delattr(_thread_local, 'memory_manager')
        else:
            _thread_local.memory_manager = self._previous
        return False


def get_current_memory_manager() -> Optional[MemoryManager]:
    """
    Get the current thread's memory manager.
    
    Returns None if no memory manager is active in the current context.
    """
    return getattr(_thread_local, 'memory_manager', None)


def create_default_memory_manager(**kwargs) -> MemoryManager:
    """
    Create a memory manager with default settings.
    
    Args:
        **kwargs: Override default settings
        
    Returns:
        New MemoryManager instance
    """
    defaults = {
        'max_memory_percent': 80.0,
        'critical_memory_percent': 90.0,
        'check_interval_seconds': 30
    }
    defaults.update(kwargs)
    return MemoryManager(**defaults)


# Convenience decorator that uses current context's memory manager
def memory_limit(max_gb: float = 4.0):
    """
    Decorator to enforce memory limits using current context's memory manager.
    
    Args:
        max_gb: Maximum memory in gigabytes
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get current memory manager from context
            memory_manager = get_current_memory_manager()
            
            # Use MemoryLimiter with current manager
            limiter = MemoryLimiter(memory_manager)
            limited_func = limiter.limit(max_gb)(func)
            
            return limited_func(*args, **kwargs)
            
        return wrapper
    return decorator