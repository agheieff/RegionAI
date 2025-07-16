"""
The Reasoning Engine for RegionAI.

This package contains the dynamic reasoning system that uses the ReasoningKnowledgeGraph
to guide the discovery of knowledge in the WorldKnowledgeGraph. Instead of hard-coded
analysis steps, the system consults its own reasoning map to decide how to think.
"""

from .registry import heuristic_registry
from .engine import ReasoningEngine

# Import implementations to register them

__all__ = ['heuristic_registry', 'ReasoningEngine']