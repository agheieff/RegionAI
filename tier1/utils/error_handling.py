"""
Error handling utilities for RegionAI.

This module provides robust error handling mechanisms including
retry logic, circuit breakers, and partial result handling.
"""

import logging
import time
from typing import Optional, Callable, Any, TypeVar, List
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"         # Can be ignored
    MEDIUM = "medium"   # Should be logged
    HIGH = "high"       # Should be handled
    CRITICAL = "critical"  # Must stop processing


@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: type
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    retry_count: int = 0
    context_data: Optional[dict] = None


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open
        
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self._state == "open":
            # Check if we should try half-open
            if (self._last_failure_time and 
                datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout)):
                self._state = "half-open"
                return False
            return True
        return False
        
    def record_success(self) -> None:
        """Record successful call."""
        self._failure_count = 0
        self._state = "closed"
        
    def record_failure(self) -> None:
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
            
    def call(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """
        Call function with circuit breaker protection.
        
        Returns:
            Function result or None if circuit is open
        """
        if self.is_open:
            logger.warning("Circuit breaker is open, skipping call")
            return None
            
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception as e:
            self.record_failure()
            if self._state == "half-open":
                self._state = "open"  # Failed during recovery attempt
            raise


def with_retry(max_retries: int = 3, 
               delay: float = 1.0,
               backoff: float = 2.0,
               exceptions: tuple = (Exception,)):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts")
                        
            raise last_exception
            
        return wrapper
    return decorator


def safe_execute(func: Callable[..., T], 
                default: Optional[T] = None,
                log_errors: bool = True,
                reraise_critical: bool = True) -> Optional[T]:
    """
    Execute function safely, returning default on error.
    
    Args:
        func: Function to execute
        default: Default value to return on error
        log_errors: Whether to log errors
        reraise_critical: Whether to reraise critical errors
        
    Returns:
        Function result or default value
    """
    try:
        return func()
    except KeyboardInterrupt:
        if reraise_critical:
            raise
        return default
    except SystemExit:
        if reraise_critical:
            raise
        return default
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {func.__name__ if hasattr(func, '__name__') else 'function'}: {e}")
        return default


class PartialResultCollector:
    """
    Collects partial results even when some operations fail.
    """
    
    def __init__(self, name: str = "collector"):
        self.name = name
        self.results: List[Any] = []
        self.errors: List[ErrorContext] = []
        self.total_attempted = 0
        
    def collect(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """
        Execute function and collect result or error.
        
        Returns:
            Function result or None on error
        """
        self.total_attempted += 1
        
        try:
            result = func(*args, **kwargs)
            self.results.append(result)
            return result
        except Exception as e:
            error_context = ErrorContext(
                error_type=type(e),
                message=str(e),
                severity=self._determine_severity(e),
                timestamp=datetime.now()
            )
            self.errors.append(error_context)
            logger.warning(f"{self.name}: Partial failure - {e}")
            return None
            
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (IOError, OSError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
            
    @property
    def success_rate(self) -> float:
        """Get success rate of operations."""
        if self.total_attempted == 0:
            return 0.0
        return len(self.results) / self.total_attempted
        
    def get_summary(self) -> dict:
        """Get summary of collection results."""
        return {
            'name': self.name,
            'total_attempted': self.total_attempted,
            'successful': len(self.results),
            'failed': len(self.errors),
            'success_rate': self.success_rate,
            'error_types': list(set(e.error_type.__name__ for e in self.errors)),
            'critical_errors': sum(1 for e in self.errors if e.severity == ErrorSeverity.CRITICAL)
        }


def handle_partial_failure(operations: List[Callable], 
                          stop_on_critical: bool = True) -> PartialResultCollector:
    """
    Execute a list of operations, collecting partial results.
    
    Args:
        operations: List of callables to execute
        stop_on_critical: Whether to stop on critical errors
        
    Returns:
        PartialResultCollector with results and errors
    """
    collector = PartialResultCollector("batch_operations")
    
    for i, operation in enumerate(operations):
        try:
            result = operation()
            collector.results.append(result)
        except Exception as e:
            error_context = ErrorContext(
                error_type=type(e),
                message=str(e),
                severity=collector._determine_severity(e),
                timestamp=datetime.now(),
                context_data={'operation_index': i}
            )
            collector.errors.append(error_context)
            
            if stop_on_critical and error_context.severity == ErrorSeverity.CRITICAL:
                logger.error(f"Critical error in operation {i}, stopping batch")
                break
                
    return collector