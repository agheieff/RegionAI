"""
Reasoning service for applying heuristics and strategies.

This service handles the application of reasoning strategies to problems,
extracted from the monolithic KnowledgeHub.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph, Heuristic
from tier1.knowledge.infrastructure.world_graph import Concept
from tier1.utils.error_handling import CircuitBreaker
from tier1.utils.cache import memoize_with_limit

logger = logging.getLogger(__name__)


@dataclass
class ReasoningContext:
    """Context for reasoning operations."""
    problem_description: str
    target_concepts: List[Concept]
    constraints: Dict[str, Any]
    available_data: Dict[str, Any]


@dataclass
class ReasoningResult:
    """Result of applying reasoning strategies."""
    strategy_used: str
    success: bool
    discoveries: List[Any]
    confidence: float
    explanation: str


class ReasoningService:
    """
    Handles application of reasoning strategies.
    
    This service is responsible for:
    - Selecting appropriate heuristics for problems
    - Applying reasoning strategies
    - Managing heuristic effectiveness
    - Cross-graph reasoning operations
    """
    
    def __init__(self, rkg: ReasoningKnowledgeGraph, config=None):
        """
        Initialize reasoning service.
        
        Args:
            rkg: Reasoning knowledge graph
            config: Configuration object. If None, uses DEFAULT_CONFIG
        """
        from tier1.config import DEFAULT_CONFIG
        self.config = config or DEFAULT_CONFIG
        self.rkg = rkg
        self._circuit_breakers = {}  # Circuit breakers per heuristic
        self._effectiveness_scores = {}  # Track heuristic effectiveness
        
    def select_heuristics(self, context: ReasoningContext) -> List[Heuristic]:
        """
        Select appropriate heuristics for the given context.
        
        Args:
            context: Reasoning context with problem details
            
        Returns:
            List of applicable heuristics sorted by relevance
        """
        # Extract tags from context
        tags = self._extract_context_tags(context)
        
        # Get applicable heuristics
        candidates = self.rkg.get_applicable_heuristics(tags)
        
        # Score and sort by relevance
        scored = []
        for heuristic in candidates:
            score = self._score_heuristic_relevance(heuristic, context)
            if score > 0:
                scored.append((score, heuristic))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored]
        
    def apply_heuristic(self, heuristic: Heuristic, 
                       context: ReasoningContext) -> ReasoningResult:
        """
        Apply a single heuristic to solve a problem.
        
        Args:
            heuristic: Heuristic to apply
            context: Problem context
            
        Returns:
            Result of applying the heuristic
        """
        # Get or create circuit breaker for this heuristic
        if heuristic.name not in self._circuit_breakers:
            self._circuit_breakers[heuristic.name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout=self.config.circuit_breaker_recovery_timeout
            )
            
        breaker = self._circuit_breakers[heuristic.name]
        
        # Try to apply heuristic with circuit breaker protection
        result = breaker.call(self._execute_heuristic, heuristic, context)
        
        if result:
            # Update effectiveness score
            self._update_effectiveness(heuristic, result.success)
            return result
        else:
            # Circuit breaker is open
            return ReasoningResult(
                strategy_used=heuristic.name,
                success=False,
                discoveries=[],
                confidence=0.0,
                explanation="Heuristic temporarily disabled due to repeated failures"
            )
            
    def apply_strategy_chain(self, heuristics: List[Heuristic],
                           context: ReasoningContext) -> List[ReasoningResult]:
        """
        Apply a chain of heuristics, passing results between them.
        
        Args:
            heuristics: Ordered list of heuristics to apply
            context: Initial context
            
        Returns:
            List of results from each heuristic
        """
        results = []
        current_context = context
        
        for heuristic in heuristics:
            result = self.apply_heuristic(heuristic, current_context)
            results.append(result)
            
            # Update context with discoveries
            if result.success and result.discoveries:
                current_context = self._update_context(current_context, result)
                
            # Stop chain if critical failure
            if not result.success and result.confidence < 0.1:
                logger.warning(f"Strategy chain stopped at {heuristic.name}")
                break
                
        return results
        
    @memoize_with_limit(max_cache_size=50)
    def suggest_reasoning_path(self, problem: str) -> List[List[Heuristic]]:
        """
        Suggest reasoning paths for a problem.
        
        Args:
            problem: Problem description
            
        Returns:
            List of possible heuristic chains
        """
        # Create context from problem
        context = self._create_context_from_problem(problem)
        
        # Get applicable heuristics
        heuristics = self.select_heuristics(context)
        
        # Generate possible paths
        paths = []
        
        # Single heuristic paths
        for h in heuristics[:5]:  # Top 5
            paths.append([h])
            
        # Two-step paths
        for h1 in heuristics[:3]:
            for h2 in heuristics[:3]:
                if h1 != h2 and self._can_chain(h1, h2):
                    paths.append([h1, h2])
                    
        return paths
        
    def get_heuristic_effectiveness(self, heuristic: Heuristic) -> float:
        """
        Get effectiveness score for a heuristic.
        
        Args:
            heuristic: Heuristic to check
            
        Returns:
            Effectiveness score (0-1)
        """
        if heuristic.name not in self._effectiveness_scores:
            return heuristic.expected_utility
            
        stats = self._effectiveness_scores[heuristic.name]
        if stats['attempts'] == 0:
            return heuristic.expected_utility
            
        return stats['successes'] / stats['attempts']
        
    def _extract_context_tags(self, context: ReasoningContext) -> List[str]:
        """Extract tags from reasoning context."""
        tags = []
        
        # Add tags based on problem description
        problem_lower = context.problem_description.lower()
        if 'prove' in problem_lower or 'theorem' in problem_lower:
            tags.append('theorem_proving')
        if 'optimize' in problem_lower:
            tags.append('optimization')
        if 'analyze' in problem_lower:
            tags.append('analysis')
            
        # Add tags from constraints
        for key in context.constraints:
            tags.append(f"constraint:{key}")
            
        # Add concept-based tags
        for concept in context.target_concepts:
            tags.append(f"concept:{concept.name.lower()}")
            
        return tags
        
    def _score_heuristic_relevance(self, heuristic: Heuristic,
                                  context: ReasoningContext) -> float:
        """Score how relevant a heuristic is to the context."""
        score = heuristic.expected_utility
        
        # Boost score based on tag matches
        context_tags = set(self._extract_context_tags(context))
        heuristic_tags = set(heuristic.applicability_conditions)
        
        overlap = len(context_tags & heuristic_tags)
        if overlap > 0:
            score *= (1 + 0.2 * overlap)
            
        # Adjust based on past effectiveness
        effectiveness = self.get_heuristic_effectiveness(heuristic)
        score *= effectiveness
        
        return min(score, 1.0)
        
    def _execute_heuristic(self, heuristic: Heuristic,
                          context: ReasoningContext) -> ReasoningResult:
        """Execute a heuristic (placeholder for actual implementation)."""
        # This would call the actual heuristic implementation
        # For now, return a mock result
        logger.info(f"Executing heuristic: {heuristic.name}")
        
        # Simulate execution
        import random
        success = random.random() > 0.3
        
        return ReasoningResult(
            strategy_used=heuristic.name,
            success=success,
            discoveries=["mock_discovery"] if success else [],
            confidence=0.8 if success else 0.2,
            explanation=f"Applied {heuristic.name} to {context.problem_description}"
        )
        
    def _update_effectiveness(self, heuristic: Heuristic, success: bool) -> None:
        """Update effectiveness tracking for a heuristic."""
        if heuristic.name not in self._effectiveness_scores:
            self._effectiveness_scores[heuristic.name] = {
                'attempts': 0,
                'successes': 0
            }
            
        stats = self._effectiveness_scores[heuristic.name]
        stats['attempts'] += 1
        if success:
            stats['successes'] += 1
            
    def _update_context(self, context: ReasoningContext,
                       result: ReasoningResult) -> ReasoningContext:
        """Update context with discoveries from a result."""
        new_data = dict(context.available_data)
        new_data['previous_discoveries'] = result.discoveries
        
        return ReasoningContext(
            problem_description=context.problem_description,
            target_concepts=context.target_concepts,
            constraints=context.constraints,
            available_data=new_data
        )
        
    def _create_context_from_problem(self, problem: str) -> ReasoningContext:
        """Create reasoning context from problem description."""
        return ReasoningContext(
            problem_description=problem,
            target_concepts=[],
            constraints={},
            available_data={}
        )
        
    def _can_chain(self, h1: Heuristic, h2: Heuristic) -> bool:
        """Check if two heuristics can be chained."""
        # Simple check - avoid same type twice
        return h1.reasoning_type != h2.reasoning_type