"""
Heuristic synthesizer for the RegionAI reasoning engine.

This module analyzes successful reasoning traces and synthesizes new,
more efficient composite heuristics from frequently occurring patterns.
"""
from typing import List, Dict, Tuple, Optional
from collections import Counter
import logging

from ....knowledge.hub import KnowledgeHub
from ....knowledge.models import ComposedHeuristic, ReasoningType, Heuristic
from ....reasoning.trace import ReasoningTrace

logger = logging.getLogger(__name__)


class HeuristicSynthesizer:
    """
    Analyzes reasoning traces to discover and synthesize new heuristics.
    
    The synthesizer looks for frequently occurring patterns in successful
    reasoning chains and creates new composite heuristics that execute
    these patterns more efficiently.
    """
    
    def __init__(self, hub: KnowledgeHub, config=None):
        """
        Initialize the synthesizer.
        
        Args:
            hub: The KnowledgeHub containing both world and reasoning graphs
            config: Configuration object. If None, uses DEFAULT_CONFIG
        """
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        
        self.hub = hub
        self.pattern_threshold = config.synthesizer_pattern_threshold  # Configurable threshold
        logger.info("HeuristicSynthesizer initialized")
    
    def analyze_traces(self, traces: List[ReasoningTrace]) -> Dict[str, List[Tuple[str, str]]]:
        """
        Analyze traces to find frequently occurring heuristic pairs.
        
        For now, we focus on pairs of heuristics that frequently succeed
        together within the same context.
        
        Args:
            traces: List of reasoning traces to analyze
            
        Returns:
            Dictionary mapping context tags to the most frequent heuristic pairs
        """
        # Group traces by context
        context_traces: Dict[str, List[ReasoningTrace]] = {}
        for trace in traces:
            if trace.is_meaningful():  # Only consider traces with 2+ heuristics
                if trace.context_tag not in context_traces:
                    context_traces[trace.context_tag] = []
                context_traces[trace.context_tag].append(trace)
        
        # Analyze patterns per context
        best_patterns: Dict[str, List[Tuple[str, str]]] = {}
        
        for context_tag, context_trace_list in context_traces.items():
            # Count pairs of successive heuristics
            pair_counter = Counter()
            
            for trace in context_trace_list:
                heuristic_ids = trace.successful_heuristic_ids
                # Extract all consecutive pairs
                for i in range(len(heuristic_ids) - 1):
                    pair = (heuristic_ids[i], heuristic_ids[i + 1])
                    pair_counter[pair] += 1
            
            # Find the most common pairs that meet the threshold
            frequent_pairs = [
                pair for pair, count in pair_counter.most_common()
                if count >= self.pattern_threshold
            ]
            
            if frequent_pairs:
                best_patterns[context_tag] = frequent_pairs
                logger.info(f"Found {len(frequent_pairs)} frequent patterns in context '{context_tag}'")
        
        return best_patterns
    
    def synthesize_new_heuristic(self, context: str, pattern: List[str]) -> Optional[ComposedHeuristic]:
        """
        Create a new composite heuristic from a successful pattern.
        
        Args:
            context: The context in which this pattern succeeded
            pattern: List of heuristic IDs that form the pattern
            
        Returns:
            The newly created ComposedHeuristic, or None if already exists
        """
        # Check if this pattern already exists as a composed heuristic
        for node in self.hub.rkg.graph.nodes():
            if isinstance(node, ComposedHeuristic):
                if node.component_heuristic_ids == tuple(pattern):
                    logger.info(f"Composed heuristic already exists for pattern {pattern}")
                    return None
        
        # Look up the component heuristics to create a meaningful name
        component_names = []
        base_utility = 0.0
        
        for heuristic_id in pattern:
            # Find the heuristic by its implementation_id
            for node in self.hub.rkg.graph.nodes():
                if isinstance(node, Heuristic) and node.implementation_id == heuristic_id:
                    component_names.append(node.name.split()[0])  # First word of name
                    # Use the utility of the last component as base
                    base_utility = node.get_utility_for_context(context)
                    break
        
        # Create a descriptive name
        if len(component_names) == len(pattern):
            name = f"Synth: {' → '.join(component_names)}"
        else:
            name = f"Synth: Pattern_{'-'.join(pattern[:2])}"
        
        # Create the utility model with a bonus for the composed pattern
        # The composed heuristic gets a slight boost over its last component
        utility_model = {
            "default": 0.5,
            context: base_utility + 0.05  # 5% boost for efficient composition
        }
        
        # Create the composed heuristic
        composed = ComposedHeuristic(
            name=name,
            description=f"Synthesized pattern: {' then '.join(pattern)}",
            reasoning_type=ReasoningType.HEURISTIC,
            component_heuristic_ids=tuple(pattern),
            utility_model=utility_model,
            implementation_id=""  # ComposedHeuristics have no direct implementation
        )
        
        # Add to the reasoning knowledge graph
        self.hub.rkg.add_concept(composed)
        
        logger.info(f"Synthesized new heuristic: {name} for context '{context}'")
        return composed
    
    def synthesize_from_traces(self, traces: List[ReasoningTrace]) -> List[ComposedHeuristic]:
        """
        Analyze traces and synthesize all viable new heuristics.
        
        Args:
            traces: List of reasoning traces to analyze
            
        Returns:
            List of newly synthesized heuristics
        """
        # Analyze patterns
        patterns_by_context = self.analyze_traces(traces)
        
        # Synthesize heuristics for each pattern
        synthesized = []
        
        for context, patterns in patterns_by_context.items():
            for pattern in patterns:
                # Convert pair tuple to list
                pattern_list = list(pattern)
                new_heuristic = self.synthesize_new_heuristic(context, pattern_list)
                if new_heuristic:
                    synthesized.append(new_heuristic)
        
        logger.info(f"Synthesized {len(synthesized)} new heuristics from {len(traces)} traces")
        return synthesized