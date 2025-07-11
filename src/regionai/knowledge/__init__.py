"""
Knowledge representation and reasoning module for RegionAI.

This package implements the Common Sense Engine that discovers and reasons
about real-world concepts by analyzing code that manipulates them.
"""

from .graph import WorldKnowledgeGraph, Concept, Relation, ConceptMetadata, RelationMetadata
from .hub import KnowledgeHub
from .models import ReasoningKnowledgeGraph, ReasoningConcept, Heuristic
from .discovery import ConceptDiscoverer, CRUDPattern
from .linker import KnowledgeLinker
from .bayesian_updater import BayesianUpdater
from .action_discoverer import ActionDiscoverer, DiscoveredAction

__all__ = [
    # Legacy export for backward compatibility
    'KnowledgeGraph',  # Will be aliased to WorldKnowledgeGraph
    # New architecture
    'WorldKnowledgeGraph',
    'ReasoningKnowledgeGraph',
    'KnowledgeHub',
    # Core types
    'Concept', 
    'Relation',
    'ConceptMetadata',
    'RelationMetadata',
    'ReasoningConcept',
    'Heuristic',
    # Services
    'ConceptDiscoverer',
    'CRUDPattern',
    'KnowledgeLinker',
    'BayesianUpdater',
    'ActionDiscoverer',
    'DiscoveredAction',
]

# Backward compatibility alias
KnowledgeGraph = WorldKnowledgeGraph