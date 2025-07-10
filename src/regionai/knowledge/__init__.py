"""
Knowledge representation and reasoning module for RegionAI.

This package implements the Common Sense Engine that discovers and reasons
about real-world concepts by analyzing code that manipulates them.
"""

from .graph import KnowledgeGraph, Concept, Relation, ConceptMetadata
from .discovery import ConceptDiscoverer, CRUDPattern

__all__ = [
    'KnowledgeGraph',
    'Concept', 
    'Relation',
    'ConceptMetadata',
    'ConceptDiscoverer',
    'CRUDPattern',
]