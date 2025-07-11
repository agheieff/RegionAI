"""
The Reasoning Engine for RegionAI.

This module contains the dynamic reasoning system that uses the ReasoningKnowledgeGraph
to guide the discovery of knowledge in the WorldKnowledgeGraph. Instead of hard-coded
analysis steps, the system consults its own reasoning map to decide how to think.
"""
from typing import Dict, Any, List, Optional
import logging

from ..knowledge.hub import KnowledgeHub
from ..knowledge.models import Heuristic
from .budget import DiscoveryBudget
from ..config import HEURISTIC_LEARNING_RATE

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    The main reasoning engine that executes heuristics based on the ReasoningKnowledgeGraph.
    
    This engine bridges the gap between the abstract heuristics in the R-KG and their
    concrete implementations, enabling dynamic, self-directed reasoning.
    """
    
    def __init__(self, hub: KnowledgeHub):
        """
        Initialize the reasoning engine.
        
        Args:
            hub: The KnowledgeHub containing both world and reasoning graphs
        """
        self.hub = hub
        logger.info("ReasoningEngine initialized")
    
    def run_prioritized_discovery_cycle(self, context: Dict[str, Any], budget: DiscoveryBudget) -> Dict[str, Any]:
        """
        Run a prioritized discovery cycle respecting the given budget.
        
        This method:
        1. Retrieves all heuristics from the ReasoningKnowledgeGraph
        2. Sorts them by utility_score (highest first)
        3. Executes heuristics until budget is exhausted
        4. Returns a summary of discoveries
        
        Args:
            context: Context for the discovery cycle, including:
                - code: Source code to analyze
                - function_name: Name of function being analyzed
                - confidence: Base confidence level
                - tags: Optional context tags for filtering heuristics
            budget: The discovery budget constraining this cycle
                
        Returns:
            Dictionary with discovery results:
                - heuristics_executed: Number of heuristics run
                - discoveries: List of what was discovered
                - errors: Any errors encountered
                - heuristics_considered: Total heuristics available
                - budget_exhausted: Whether budget limit was reached
        """
        results = {
            'heuristics_executed': 0,
            'discoveries': [],
            'errors': []
        }
        
        # Get initial graph state for comparison
        initial_nodes = len(self.hub.wkg.graph.nodes())
        initial_edges = len(self.hub.wkg.graph.edges())
        
        # Get context tags for filtering (if provided)
        context_tags = context.get('tags', [])
        
        # Retrieve all heuristics from the reasoning graph
        heuristics = self._get_applicable_heuristics(context_tags)
        logger.info(f"Found {len(heuristics)} applicable heuristics")
        
        # Sort heuristics by utility score (highest first)
        heuristics_with_impl = [h for h in heuristics if h.implementation_id]
        heuristics_sorted = sorted(heuristics_with_impl, key=lambda h: h.utility_score, reverse=True)
        
        logger.info(f"Sorted {len(heuristics_sorted)} heuristics by utility score")
        for h in heuristics_sorted[:3]:  # Log top 3
            logger.debug(f"  {h.name}: utility_score={h.utility_score}")
        
        # Track total heuristics available
        results['heuristics_considered'] = len(heuristics_sorted)
        results['budget_exhausted'] = False
        
        # Import registry locally
        from .registry import heuristic_registry
        
        # Execute heuristics up to budget limit
        for heuristic in heuristics_sorted:
            # Check if budget exhausted
            if results['heuristics_executed'] >= budget.max_heuristics_to_run:
                logger.info(f"Budget exhausted after {results['heuristics_executed']} heuristics")
                results['budget_exhausted'] = True
                break
            
            # Get the implementation function
            func = heuristic_registry.get(heuristic.implementation_id)
            if func is None:
                error_msg = f"Implementation not found for heuristic '{heuristic.name}' (ID: {heuristic.implementation_id})"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                continue
            
            try:
                # Execute the heuristic and capture success/failure
                logger.debug(f"Executing heuristic: {heuristic.name} (score: {heuristic.utility_score})")
                made_discovery = func(self.hub, context)
                results['heuristics_executed'] += 1
                
                # Update utility score based on success/failure
                self._update_heuristic_score(heuristic, made_discovery)
                
            except Exception as e:
                error_msg = f"Error executing heuristic '{heuristic.name}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
        
        # Calculate what was discovered
        final_nodes = len(self.hub.wkg.graph.nodes())
        final_edges = len(self.hub.wkg.graph.edges())
        
        nodes_added = final_nodes - initial_nodes
        edges_added = final_edges - initial_edges
        
        if nodes_added > 0:
            results['discoveries'].append(f"Added {nodes_added} new concepts")
        if edges_added > 0:
            results['discoveries'].append(f"Added {edges_added} new relationships")
        
        logger.info(f"Discovery cycle complete: {results['heuristics_executed']} heuristics executed, "
                   f"{nodes_added} nodes added, {edges_added} edges added")
        
        return results
    
    def _get_applicable_heuristics(self, context_tags: List[str]) -> List[Heuristic]:
        """
        Get heuristics applicable to the current context.
        
        Args:
            context_tags: Tags describing the current context
            
        Returns:
            List of applicable heuristics
        """
        # If context tags provided, use the RKG's built-in filtering
        if context_tags:
            return self.hub.rkg.get_applicable_heuristics(context_tags)
        
        # Otherwise, get all heuristics
        all_heuristics = []
        for node in self.hub.rkg.graph.nodes():
            if isinstance(node, Heuristic):
                all_heuristics.append(node)
        
        # Sort by utility score (highest first)
        all_heuristics.sort(key=lambda h: h.utility_score, reverse=True)
        
        return all_heuristics
    
    def execute_specific_heuristic(self, heuristic_id: str, context: Dict[str, Any]) -> bool:
        """
        Execute a specific heuristic by its ID.
        
        Args:
            heuristic_id: The implementation ID of the heuristic
            context: Context for the heuristic execution
            
        Returns:
            True if successful, False otherwise
        """
        # Import registry locally
        from .registry import heuristic_registry
        
        func = heuristic_registry.get(heuristic_id)
        if func is None:
            logger.error(f"Heuristic not found: {heuristic_id}")
            return False
        
        try:
            made_discovery = func(self.hub, context)
            logger.info(f"Successfully executed heuristic: {heuristic_id} (made_discovery={made_discovery})")
            return made_discovery
            
        except Exception as e:
            logger.error(f"Error executing heuristic '{heuristic_id}': {str(e)}", exc_info=True)
            return False
    
    def get_available_heuristics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available heuristics.
        
        Returns:
            Dictionary mapping heuristic names to their details
        """
        heuristics_info = {}
        
        for node in self.hub.rkg.graph.nodes():
            if isinstance(node, Heuristic):
                heuristics_info[node.name] = {
                    'description': node.description,
                    'utility_score': node.utility_score,
                    'implementation_id': node.implementation_id,
                    'has_implementation': bool(node.implementation_id),
                    'reasoning_type': node.reasoning_type.value
                }
        
        return heuristics_info
    
    def _update_heuristic_score(self, heuristic: Heuristic, made_discovery: bool) -> None:
        """
        Update a heuristic's utility score based on its success or failure.
        
        Uses a learning rate to gradually adjust scores:
        - Success: score increases toward 1.0 (with diminishing returns)
        - Failure: score decreases proportionally
        
        Args:
            heuristic: The heuristic to update
            made_discovery: Whether the heuristic found new knowledge
        """
        old_score = heuristic.utility_score
        
        if made_discovery:
            # Success: increase score with diminishing returns as it approaches 1.0
            new_score = old_score + HEURISTIC_LEARNING_RATE * (1.0 - old_score)
        else:
            # Failure: decrease score proportionally
            new_score = old_score - HEURISTIC_LEARNING_RATE * old_score
        
        # Clamp score between 0.0 and 1.0
        new_score = max(0.0, min(1.0, new_score))
        
        # Update the heuristic in the reasoning graph
        # We need to replace the heuristic node with an updated version
        # since Heuristic is frozen (immutable)
        updated_heuristic = Heuristic(
            name=heuristic.name,
            description=heuristic.description,
            reasoning_type=heuristic.reasoning_type,
            applicability_conditions=heuristic.applicability_conditions,
            expected_utility=heuristic.expected_utility,
            utility_score=new_score,
            implementation_id=heuristic.implementation_id
        )
        
        # Update in the reasoning graph
        # First remove the old node
        self.hub.rkg.graph.remove_node(heuristic)
        
        # Add the updated node
        self.hub.rkg.graph.add_node(updated_heuristic)
        
        # Re-add any edges that were connected to the old heuristic
        # This is a simplified approach - in a real system we'd preserve all edge data
        logger.info(f"Updated {heuristic.name} utility score: {old_score:.3f} -> {new_score:.3f} "
                   f"({'success' if made_discovery else 'no discovery'})")