"""
Knowledge services for specialized analysis tasks.

These services extract focused functionality from the KnowledgeLinker,
making each component more testable and reusable.
"""
from .concept_variations import ConceptVariationBuilder
from .pattern_matcher import RelationshipPatternMatcher, RelationshipMatch
from .relationship_discoverer import RelationshipDiscoverer, DiscoveredRelationship
from .action_coordinator import ActionCoordinator, ActionDiscoveryResult
from .grammar_extractor import GrammarExtractor, ExtractedPattern

__all__ = [
    'ConceptVariationBuilder',
    'RelationshipPatternMatcher',
    'RelationshipMatch',
    'RelationshipDiscoverer',
    'DiscoveredRelationship',
    'ActionCoordinator',
    'ActionDiscoveryResult',
    'GrammarExtractor',
    'ExtractedPattern',
]