"""
Knowledge representation and reasoning module for RegionAI.

This package implements the Common Sense Engine that discovers and reasons
about real-world concepts by analyzing code that manipulates them.
"""

from .graph import WorldKnowledgeGraph, Concept, Relation, ConceptMetadata, RelationMetadata
from .hub import KnowledgeHub
from .hub_v2 import KnowledgeHubV2, migrate_from_v1
from .models import ReasoningKnowledgeGraph, ReasoningConcept, Heuristic
from .discovery import ConceptDiscoverer, CRUDPattern
from .linker import KnowledgeLinker
from .bayesian_updater import BayesianUpdater
from .action_discoverer import ActionDiscoverer, DiscoveredAction
# Import specialized services
from .storage_service import StorageService
from .query_service import QueryService
from .reasoning_service import ReasoningService

__all__ = [
    # Legacy export for backward compatibility
    'KnowledgeGraph',  # Will be aliased to WorldKnowledgeGraph
    # New architecture
    'WorldKnowledgeGraph',
    'ReasoningKnowledgeGraph',
    'KnowledgeHub',
    'KnowledgeHubV2',  # New refactored version
    'migrate_from_v1',
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
    # New specialized services
    'StorageService',
    'QueryService',
    'ReasoningService',
]

# Backward compatibility alias
KnowledgeGraph = WorldKnowledgeGraph