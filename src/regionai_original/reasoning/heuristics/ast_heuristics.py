"""
AST-based heuristics for code analysis.

This module contains heuristics that analyze Abstract Syntax Trees to discover
relationships and patterns in code structure.
"""
from typing import Dict, Any
import logging

from ...knowledge.hub import KnowledgeHub
from ...knowledge.graph import Concept, Relation, ConceptMetadata
from ...knowledge.action_discoverer import ActionDiscoverer
from ..heuristic_registry import heuristic_registry

logger = logging.getLogger(__name__)


@heuristic_registry.register("ast.method_call_implies_performs",
                           description="Method call implies PERFORMS relationship",
                           applicability_conditions=("ast", "method_call", "performs"),
                           expected_utility=0.85)
def method_call_implies_performs(hub: KnowledgeHub, context: Dict[str, Any]) -> bool:
    """
    Heuristic: Method call implies PERFORMS relationship.
    
    When we see code like `customer.save()`, this implies that the concept
    'Customer' PERFORMS the action 'Save'.
    
    Args:
        hub: The KnowledgeHub containing both world and reasoning graphs
        context: Additional context including:
            - code: The source code to analyze
            - function_name: Name of the function being analyzed
            - confidence: Base confidence for discoveries
    """
    code = context.get('code', '')
    function_name = context.get('function_name', 'unknown')
    base_confidence = context.get('confidence', 0.75)
    
    if not code:
        logger.warning("No code provided for method_call_implies_performs heuristic")
        return False
    
    # Use ActionDiscoverer to find method calls
    discoverer = ActionDiscoverer()
    actions = discoverer.discover_actions(code, function_name)
    
    made_discovery = False
    
    # Process each discovered action
    for action in actions:
        # Create concept if it doesn't exist
        concept = Concept(action.concept.title())
        if concept not in hub.wkg:
            metadata = ConceptMetadata(
                discovery_method='action_inference',
                source_functions=[function_name]
            )
            hub.wkg.add_concept(concept, metadata)
            made_discovery = True
        
        # Create action concept if it doesn't exist
        action_concept = Concept(action.verb.title())
        if action_concept not in hub.wkg:
            metadata = ConceptMetadata(
                discovery_method='action_verb',
                properties={'is_action': True, 'verb_form': action.verb},
                source_functions=[function_name]
            )
            hub.wkg.add_concept(action_concept, metadata)
            made_discovery = True
        
        # Check if PERFORMS relationship already exists
        existing_relations = hub.wkg.get_relations_with_confidence(concept)
        has_performs = any(
            r['target'] == action_concept and str(r['relation']) == 'PERFORMS'
            for r in existing_relations
        )
        
        if not has_performs:
            # Add PERFORMS relationship
            performs_confidence = action.confidence * base_confidence * 0.85  # 0.85 is the heuristic's utility score
            hub.wkg.add_relation(
                concept,
                action_concept,
                Relation('PERFORMS'),
                confidence=performs_confidence,
                evidence=f"Method call: {action.method_name} in {function_name}"
            )
            made_discovery = True
            logger.debug(f"Discovered: {concept} PERFORMS {action_concept} (confidence: {performs_confidence:.2f})")
    
    return made_discovery


@heuristic_registry.register("ast.sequential_nodes_imply_precedes",
                           description="Sequential AST nodes imply PRECEDES relationship",
                           applicability_conditions=("ast", "sequential", "precedes"),
                           expected_utility=0.95)
def sequential_nodes_imply_precedes(hub: KnowledgeHub, context: Dict[str, Any]) -> bool:
    """
    Heuristic: Sequential AST nodes imply PRECEDES relationship.
    
    When actions appear sequentially in code (e.g., validate() then save()),
    this implies a temporal ordering where the first action PRECEDES the second.
    
    Args:
        hub: The KnowledgeHub containing both world and reasoning graphs
        context: Additional context including:
            - code: The source code to analyze
            - function_name: Name of the function being analyzed
            - confidence: Base confidence for discoveries
    """
    code = context.get('code', '')
    function_name = context.get('function_name', 'unknown')
    base_confidence = context.get('confidence', 0.75)
    
    if not code:
        logger.warning("No code provided for sequential_nodes_imply_precedes heuristic")
        return False
    
    # Use ActionDiscoverer to find action sequences
    discoverer = ActionDiscoverer()
    sequences = discoverer.discover_action_sequences(code, function_name)
    
    made_discovery = False
    
    # Process each sequence
    for action1, action2 in sequences:
        # Create action concepts if they don't exist
        action1_concept = Concept(action1.verb.title())
        action2_concept = Concept(action2.verb.title())
        
        for action_obj, action_concept in [(action1, action1_concept), (action2, action2_concept)]:
            if action_concept not in hub.wkg:
                metadata = ConceptMetadata(
                    discovery_method='sequential_analysis',
                    properties={'is_action': True, 'verb_form': action_obj.verb},
                    source_functions=[function_name]
                )
                hub.wkg.add_concept(action_concept, metadata)
                made_discovery = True
        
        # Check if PRECEDES relationship already exists
        existing_relations = hub.wkg.get_relations_with_confidence(action1_concept)
        has_precedes = any(
            r['target'] == action2_concept and str(r['relation']) == 'PRECEDES'
            for r in existing_relations
        )
        
        if not has_precedes:
            # Add PRECEDES relationship
            sequence_confidence = min(action1.confidence, action2.confidence) * base_confidence * 0.95  # 0.95 is the heuristic's utility score
            hub.wkg.add_relation(
                action1_concept,
                action2_concept,
                Relation('PRECEDES'),
                confidence=sequence_confidence,
                evidence=f"Sequential execution: {action1.verb} -> {action2.verb} in {function_name}"
            )
            made_discovery = True
            logger.debug(f"Discovered: {action1_concept} PRECEDES {action2_concept} (confidence: {sequence_confidence:.2f})")
    
    return made_discovery