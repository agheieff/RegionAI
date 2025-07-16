"""
Discovery strategies for RegionAI.

This package contains different strategies for discovering transformations:
- Sequential: Linear sequences of primitive operations
- Conditional: IF-THEN-ELSE patterns
- Iterative: FOR-EACH patterns with nested conditionals
"""

from .base import DiscoveryStrategy
from .sequential import SequentialDiscovery
from .conditional import ConditionalDiscovery
from .iterative import IterativeDiscovery

__all__ = [
    "DiscoveryStrategy",
    "SequentialDiscovery",
    "ConditionalDiscovery",
    "IterativeDiscovery",
]