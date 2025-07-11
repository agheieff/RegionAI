"""
Knowledge representation and reasoning module for RegionAI.

This package implements the Common Sense Engine that discovers and reasons
about real-world concepts by analyzing code that manipulates them.
"""

from .graph import KnowledgeGraph, Concept, Relation, ConceptMetadata, RelationMetadata
from .discovery import ConceptDiscoverer, CRUDPattern
from .linker import KnowledgeLinker, RelationshipPattern
from .bayesian_updater import BayesianUpdater
from .action_discoverer import ActionDiscoverer, DiscoveredAction

__all__ = [
    'KnowledgeGraph',
    'Concept', 
    'Relation',
    'ConceptMetadata',
    'RelationMetadata',
    'ConceptDiscoverer',
    'CRUDPattern',
    'KnowledgeLinker',
    'RelationshipPattern',
    'BayesianUpdater',
    'ActionDiscoverer',
    'DiscoveredAction',
]