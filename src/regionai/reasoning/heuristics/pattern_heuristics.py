"""
Pattern-based heuristics for discovering relationships.

This module contains heuristics that identify patterns in code structure,
naming conventions, and concept co-occurrence.
"""
from typing import Dict, Any
import logging

from ...knowledge.hub import KnowledgeHub
from ...knowledge.graph import Concept, Relation, ConceptMetadata
from ..heuristic_registry import heuristic_registry

logger = logging.getLogger(__name__)


@heuristic_registry.register("pattern.co_occurrence_implies_related",
                           description="Co-occurrence in function names implies RELATED_TO relationship",
                           applicability_conditions=("pattern", "co_occurrence", "related"),
                           expected_utility=0.75)
def co_occurrence_implies_related(hub: KnowledgeHub, context: Dict[str, Any]) -> bool:
    """
    Heuristic: Co-occurrence in function names implies RELATED_TO relationship.
    
    When two concepts appear together in a function name (e.g., get_customer_orders),
    this implies they are related in some way.
    
    Args:
        hub: The KnowledgeHub containing both world and reasoning graphs
        context: Additional context including:
            - function_name: Name of the function to analyze
            - confidence: Base confidence for discoveries
    """
    function_name = context.get('function_name', '')
    base_confidence = context.get('confidence', 0.75)
    
    if not function_name:
        logger.warning("No function name provided for co_occurrence_implies_related heuristic")
        return False
    
    # Extract potential concept names from the function name
    # Split by underscores and filter out common verbs
    parts = function_name.lower().split('_')
    
    # Common verbs to filter out
    common_verbs = {'get', 'set', 'create', 'update', 'delete', 'find', 'search', 
                    'list', 'save', 'load', 'check', 'validate', 'process', 'handle'}
    
    # Extract nouns (potential concepts)
    potential_concepts = []
    for part in parts:
        if part not in common_verbs and len(part) > 2:
            potential_concepts.append(part.title())
    
    made_discovery = False
    
    # Create relationships between co-occurring concepts
    for i in range(len(potential_concepts)):
        for j in range(i + 1, len(potential_concepts)):
            concept1 = Concept(potential_concepts[i])
            concept2 = Concept(potential_concepts[j])
            
            # Ensure concepts exist
            for concept in [concept1, concept2]:
                if concept not in hub.wkg:
                    metadata = ConceptMetadata(
                        discovery_method='co_occurrence',
                        source_functions=[function_name]
                    )
                    hub.wkg.add_concept(concept, metadata)
                    made_discovery = True
            
            # Check if RELATED_TO relationship already exists
            existing_relations = hub.wkg.get_relations_with_confidence(concept1)
            has_related = any(
                r['target'] == concept2 and str(r['relation']) == 'RELATED_TO'
                for r in existing_relations
            )
            
            if not has_related:
                # Add RELATED_TO relationship (bidirectional)
                co_occurrence_confidence = base_confidence * 0.75  # 0.75 is the heuristic's utility score
                hub.wkg.add_relation(
                    concept1,
                    concept2,
                    Relation('RELATED_TO'),
                    confidence=co_occurrence_confidence,
                    evidence=f"Co-occurrence in function name: {function_name}"
                )
                
                # Add reverse relationship
                hub.wkg.add_relation(
                    concept2,
                    concept1,
                    Relation('RELATED_TO'),
                    confidence=co_occurrence_confidence,
                    evidence=f"Co-occurrence in function name: {function_name}"
                )
                made_discovery = True
                logger.debug(f"Discovered: {concept1} RELATED_TO {concept2} (confidence: {co_occurrence_confidence:.2f})")
    
    return made_discovery