"""
The Reasoning Engine for RegionAI.

This module contains the dynamic reasoning system that uses the ReasoningKnowledgeGraph
to guide the discovery of knowledge in the WorldKnowledgeGraph. Instead of hard-coded
analysis steps, the system consults its own reasoning map to decide how to think.
"""
from typing import Dict, Any, List, Optional
import logging

from tier1.knowledge.infrastructure.hub_v1 import KnowledgeHub
from tier1.knowledge.infrastructure.reasoning_graph import Heuristic, ComposedHeuristic
from .budget import DiscoveryBudget
from .context import AnalysisContext, ContextDetector
from .context_rules import DEFAULT_CONTEXT_RULES
from .trace import ReasoningTrace
from tier1.config import HEURISTIC_LEARNING_RATE
from tier1.utils.cache import cached_ast_parse
from tier1.utils.memory_manager import get_memory_manager

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    The main reasoning engine that executes heuristics based on the ReasoningKnowledgeGraph.
    
    This engine bridges the gap between the abstract heuristics in the R-KG and their
    concrete implementations, enabling dynamic, self-directed reasoning.
    """
    
    def __init__(self, hub: KnowledgeHub, memory_manager=None):
        """
        Initialize the reasoning engine.
        
        Args:
            hub: The KnowledgeHub containing both world and reasoning graphs
            memory_manager: Optional memory manager for memory monitoring
        """
        self.hub = hub
        self.memory_manager = memory_manager
        self.context_detector = ContextDetector(DEFAULT_CONTEXT_RULES)
        logger.info("ReasoningEngine initialized with automatic context detection")
    
    def run_prioritized_discovery_cycle(self, context: Dict[str, Any], budget: DiscoveryBudget, 
                                       analysis_context: AnalysisContext, trace: Optional[ReasoningTrace] = None) -> Dict[str, Any]:
        """
        Run a prioritized discovery cycle respecting the given budget.
        
        This method:
        1. Retrieves all heuristics from the ReasoningKnowledgeGraph
        2. Sorts them by context-specific utility scores (highest first)
        3. Executes heuristics until budget is exhausted
        4. Updates context-specific scores based on success/failure
        5. Returns a summary of discoveries
        
        Args:
            context: Context for the discovery cycle, including:
                - code: Source code to analyze
                - function_name: Name of function being analyzed
                - confidence: Base confidence level
                - tags: Optional context tags for filtering heuristics
            budget: The discovery budget constraining this cycle
            analysis_context: The context determining which utility scores to use
                
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
        
        # Sort heuristics by context-specific utility score (highest first)
        # Include both regular heuristics with implementation_id and composed heuristics
        heuristics_with_impl = [
            h for h in heuristics 
            if (h.implementation_id or isinstance(h, ComposedHeuristic))
        ]
        current_context = analysis_context.current_context_tag
        heuristics_sorted = sorted(
            heuristics_with_impl, 
            key=lambda h: h.get_utility_for_context(current_context), 
            reverse=True
        )
        
        logger.info(f"Sorted {len(heuristics_sorted)} heuristics by utility score for context '{current_context}'")
        for h in heuristics_sorted[:3]:  # Log top 3
            score = h.get_utility_for_context(current_context)
            logger.debug(f"  {h.name}: utility_score={score:.3f} (context: {current_context})")
        
        # Track total heuristics available
        results['heuristics_considered'] = len(heuristics_sorted)
        results['budget_exhausted'] = False
        
        # Track already executed heuristics to prevent redundant execution
        executed_heuristic_ids = set()
        
        # Import registry locally
        from .registry import heuristic_registry
        
        # Execute heuristics up to budget limit
        for heuristic in heuristics_sorted:
            # Check memory usage periodically
            if results['heuristics_executed'] % 10 == 0:
                if self.memory_manager:
                    if self.memory_manager.check_memory():
                        logger.warning("Memory cleanup triggered during reasoning")
                        # Give the system a chance to recover
                        import time
                        time.sleep(0.1)
                else:
                    # Fallback to global for backward compatibility
                    memory_manager = get_memory_manager()
                    if memory_manager.check_memory():
                        logger.warning("Memory cleanup triggered during reasoning")
                        # Give the system a chance to recover
                        import time
                        time.sleep(0.1)
            
            # Check if budget exhausted
            if results['heuristics_executed'] >= budget.max_heuristics_to_run:
                logger.info(f"Budget exhausted after {results['heuristics_executed']} heuristics")
                results['budget_exhausted'] = True
                break
            
            # Check if this is a ComposedHeuristic
            if isinstance(heuristic, ComposedHeuristic):
                # Execute composed heuristic
                made_discovery = self._execute_composed_heuristic(
                    heuristic, context, current_context, executed_heuristic_ids, trace
                )
                results['heuristics_executed'] += 1
                
                # Update the composed heuristic's score
                self._update_heuristic_score(heuristic, made_discovery, current_context)
                
            else:
                # Regular heuristic - check if already executed as part of a composition
                if heuristic.implementation_id in executed_heuristic_ids:
                    logger.debug(f"Skipping {heuristic.name} - already executed as part of composition")
                    continue
                
                # Get the implementation function
                func = heuristic_registry.get(heuristic.implementation_id)
                if func is None:
                    error_msg = f"Implementation not found for heuristic '{heuristic.name}' (ID: {heuristic.implementation_id})"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    continue
                
                try:
                    # Execute the heuristic and capture success/failure
                    context_score = heuristic.get_utility_for_context(current_context)
                    logger.debug(f"Executing heuristic: {heuristic.name} (score: {context_score:.3f})")
                    made_discovery = func(self.hub, context)
                    results['heuristics_executed'] += 1
                    
                    # Record successful heuristics in the trace
                    if made_discovery and trace:
                        trace.add_successful_heuristic(heuristic.implementation_id)
                    
                    # Update context-specific utility score based on success/failure
                    self._update_heuristic_score(heuristic, made_discovery, current_context)
                    
                    # Mark as executed
                    executed_heuristic_ids.add(heuristic.implementation_id)
                    
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
    
    def run_autonomous_discovery_cycle(self, analysis_target: str, budget: DiscoveryBudget) -> Optional[ReasoningTrace]:
        """
        Run a prioritized discovery cycle with automatic context detection.
        
        This method automatically detects the appropriate context from the
        source code and then runs the discovery cycle, returning a trace
        of successful reasoning patterns.
        
        Args:
            analysis_target: The source code to analyze
            budget: The discovery budget constraining this cycle
            
        Returns:
            ReasoningTrace if discoveries were made, None otherwise
        """
        # Detect context from the code
        detected_context = self.context_detector.detect(analysis_target)
        logger.info(f"Automatically detected context: '{detected_context.current_context_tag}'")
        
        # Create a reasoning trace for this cycle
        trace = ReasoningTrace(
            context_tag=detected_context.current_context_tag,
            analysis_target_preview=analysis_target[:100]
        )
        
        # Extract context information from the code
        # For now, we'll use a simple approach
        context = {
            'code': analysis_target,
            'function_name': self._extract_function_name(analysis_target),
            'confidence': 0.8  # Default confidence
        }
        
        # Run the discovery cycle with the detected context
        results = self.run_prioritized_discovery_cycle(context, budget, detected_context, trace)
        
        # Return the trace if discoveries were made
        if results.get('discoveries'):
            trace.total_discoveries = len(results['discoveries'])
            return trace
        
        return None
    
    def _extract_function_name(self, code: str) -> str:
        """
        Extract the function name from code if possible.
        
        Args:
            code: Source code
            
        Returns:
            Function name or 'unknown'
        """
        # Use cached AST parsing
        tree = cached_ast_parse(code)
        if tree:
            import ast
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        return 'unknown'
    
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
        
        # Sort by default utility score (highest first)
        all_heuristics.sort(key=lambda h: h.get_utility_for_context("default"), reverse=True)
        
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
                # For ComposedHeuristic, has_implementation is True if it has components
                if isinstance(node, ComposedHeuristic):
                    has_impl = bool(node.component_heuristic_ids)
                else:
                    has_impl = bool(node.implementation_id)
                
                heuristics_info[node.name] = {
                    'description': node.description,
                    'utility_score': node.get_utility_for_context("default"),  # For backward compatibility
                    'utility_model': node.utility_model,
                    'implementation_id': node.implementation_id,
                    'has_implementation': has_impl,
                    'reasoning_type': node.reasoning_type.value,
                    'is_composed': isinstance(node, ComposedHeuristic)
                }
        
        return heuristics_info
    
    def _execute_composed_heuristic(self, composed: ComposedHeuristic, context: Dict[str, Any], 
                                   current_context: str, executed_ids: set, trace: Optional[ReasoningTrace]) -> bool:
        """
        Execute a composed heuristic by running its component heuristics in sequence.
        
        Args:
            composed: The ComposedHeuristic to execute
            context: Context for heuristic execution
            current_context: The current analysis context tag
            executed_ids: Set of already executed heuristic IDs
            trace: Optional reasoning trace for recording successes
            
        Returns:
            True if at least one component made a discovery, False otherwise
        """
        logger.info(f"Executing composed heuristic: {composed.name}")
        
        # Import registry locally
        from .registry import heuristic_registry
        
        overall_success = False
        
        # Execute each component heuristic in sequence
        for component_id in composed.component_heuristic_ids:
            # Skip if already executed
            if component_id in executed_ids:
                logger.debug(f"  Skipping component {component_id} - already executed")
                continue
            
            # Get the implementation
            func = heuristic_registry.get(component_id)
            if func is None:
                logger.error(f"  Component implementation not found: {component_id}")
                continue
            
            # Find the component heuristic node for score updates
            component_heuristic = None
            for node in self.hub.rkg.graph.nodes():
                if isinstance(node, Heuristic) and node.implementation_id == component_id:
                    component_heuristic = node
                    break
            
            try:
                # Execute the component
                logger.debug(f"  Executing component: {component_id}")
                made_discovery = func(self.hub, context)
                
                # Record success in trace
                if made_discovery and trace:
                    trace.add_successful_heuristic(component_id)
                
                # Update component's score independently
                if component_heuristic:
                    self._update_heuristic_score(component_heuristic, made_discovery, current_context)
                
                # Track overall success
                if made_discovery:
                    overall_success = True
                
                # Mark as executed
                executed_ids.add(component_id)
                
            except Exception as e:
                logger.error(f"  Error executing component {component_id}: {str(e)}", exc_info=True)
        
        logger.info(f"Composed heuristic {composed.name} {'succeeded' if overall_success else 'failed'}")
        return overall_success
    
    def _update_heuristic_score(self, heuristic: Heuristic, made_discovery: bool, context_tag: str) -> None:
        """
        Update a heuristic's context-specific utility score based on its success or failure.
        
        Uses a learning rate to gradually adjust scores:
        - Success: score increases toward 1.0 (with diminishing returns)
        - Failure: score decreases proportionally
        
        Args:
            heuristic: The heuristic to update
            made_discovery: Whether the heuristic found new knowledge
            context_tag: The context in which the heuristic was executed
        """
        # Get the current score for this context
        old_score = heuristic.get_utility_for_context(context_tag)
        
        if made_discovery:
            # Success: increase score with diminishing returns as it approaches 1.0
            new_score = old_score + HEURISTIC_LEARNING_RATE * (1.0 - old_score)
        else:
            # Failure: decrease score proportionally
            new_score = old_score - HEURISTIC_LEARNING_RATE * old_score
        
        # Clamp score between 0.0 and 1.0
        new_score = max(0.0, min(1.0, new_score))
        
        # Create updated utility model
        updated_utility_model = dict(heuristic.utility_model)
        updated_utility_model[context_tag] = new_score
        
        # Update the heuristic in the reasoning graph
        # We need to replace the heuristic node with an updated version
        # since Heuristic is frozen (immutable)
        updated_heuristic = Heuristic(
            name=heuristic.name,
            description=heuristic.description,
            reasoning_type=heuristic.reasoning_type,
            applicability_conditions=heuristic.applicability_conditions,
            expected_utility=heuristic.expected_utility,
            utility_model=updated_utility_model,
            implementation_id=heuristic.implementation_id
        )
        
        # Update in the reasoning graph
        # First remove the old node
        self.hub.rkg.graph.remove_node(heuristic)
        
        # Add the updated node
        self.hub.rkg.graph.add_node(updated_heuristic)
        
        # Re-add any edges that were connected to the old heuristic
        # This is a simplified approach - in a real system we'd preserve all edge data
        logger.info(f"Updated {heuristic.name} utility score for context '{context_tag}': "
                   f"{old_score:.3f} -> {new_score:.3f} ({'success' if made_discovery else 'no discovery'})")