"""
Core utility functions for RegionAI.

This module provides common utilities used across the core abstractions.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_get(dictionary: Dict[str, Any], key: str, default: T = None) -> T:
    """Safely get a value from a dictionary with a default."""
    return dictionary.get(key, default)


def flatten_list(nested_list: List[List[T]]) -> List[T]:
    """Flatten a nested list."""
    return [item for sublist in nested_list for item in sublist]


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to [0, 1] range."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)