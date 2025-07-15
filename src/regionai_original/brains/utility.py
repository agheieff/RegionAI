"""
Utility Brain - "How to think?"

This brain module manages thinking strategies, heuristics, and resource allocation.
It decides which cognitive resources to apply to which problems.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time

from ..config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ThinkingMode(Enum):
    """Different modes of thinking."""
    FAST = "fast"  # Quick, heuristic-based
    BALANCED = "balanced"  # Default mode
    DEEP = "deep"  # Thorough analysis
    CREATIVE = "creative"  # Exploration mode


@dataclass
class Heuristic:
    """Represents a thinking heuristic or strategy."""
    name: str
    description: str
    applicability_check: Callable[[Any], float]  # Returns score 0-1
    apply: Callable[[Any], Any]  # The actual heuristic
    cost: float  # Computational cost
    success_rate: float = 0.5  # Track performance
    usage_count: int = 0


@dataclass
class ThinkingStrategy:
    """A strategy for approaching a problem."""
    name: str
    mode: ThinkingMode
    heuristics: List[str]  # Names of heuristics to apply
    time_limit: Optional[float] = None
    confidence_threshold: float = 0.7


class UtilityBrain:
    """
    The Utility brain manages how to think about problems.
    
    Core responsibilities:
    - Select appropriate thinking strategies
    - Manage computational resources
    - Apply and learn from heuristics
    - Balance exploration vs exploitation
    """
    
    def __init__(self, config: RegionAIConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.heuristics: Dict[str, Heuristic] = {}
        self.strategies: Dict[str, ThinkingStrategy] = {}
        self.current_mode = ThinkingMode.BALANCED
        self._performance_history: List[Dict] = []
        
        # Initialize default heuristics
        self._initialize_default_heuristics()
        self._initialize_default_strategies()
        
    def _initialize_default_heuristics(self):
        """Set up basic heuristics."""
        # Pattern matching heuristic
        self.register_heuristic(
            "pattern_match",
            "Look for similar patterns seen before",
            lambda x: 0.8 if hasattr(x, 'pattern') else 0.3,
            lambda x: self._pattern_match(x),
            cost=0.1
        )
        
        # Decomposition heuristic
        self.register_heuristic(
            "decompose",
            "Break problem into smaller parts",
            lambda x: 0.9 if hasattr(x, '__len__') and len(x) > 1 else 0.2,
            lambda x: self._decompose(x),
            cost=0.3
        )
        
        # Analogy heuristic
        self.register_heuristic(
            "analogy",
            "Find analogous solved problems",
            lambda x: 0.6,  # Generally applicable
            lambda x: self._find_analogy(x),
            cost=0.5
        )
        
        # First principles heuristic
        self.register_heuristic(
            "first_principles",
            "Reason from fundamental principles",
            lambda x: 0.4,  # More expensive, use sparingly
            lambda x: self._first_principles(x),
            cost=0.8
        )
        
    def _initialize_default_strategies(self):
        """Set up basic thinking strategies."""
        # Fast mode strategy
        self.register_strategy(
            "quick_scan",
            ThinkingMode.FAST,
            ["pattern_match"],
            time_limit=1.0,
            confidence_threshold=0.6
        )
        
        # Balanced mode strategy
        self.register_strategy(
            "standard_analysis",
            ThinkingMode.BALANCED,
            ["pattern_match", "decompose", "analogy"],
            time_limit=5.0,
            confidence_threshold=0.7
        )
        
        # Deep mode strategy
        self.register_strategy(
            "thorough_analysis",
            ThinkingMode.DEEP,
            ["decompose", "first_principles", "analogy", "pattern_match"],
            time_limit=None,
            confidence_threshold=0.9
        )
        
        # Creative mode strategy
        self.register_strategy(
            "creative_exploration",
            ThinkingMode.CREATIVE,
            ["analogy", "decompose", "pattern_match"],
            time_limit=10.0,
            confidence_threshold=0.5
        )
        
    def register_heuristic(self, name: str, description: str,
                          applicability_check: Callable, apply_func: Callable,
                          cost: float = 0.5):
        """Register a new heuristic."""
        self.heuristics[name] = Heuristic(
            name=name,
            description=description,
            applicability_check=applicability_check,
            apply=apply_func,
            cost=cost
        )
        
    def register_strategy(self, name: str, mode: ThinkingMode,
                         heuristics: List[str], time_limit: Optional[float] = None,
                         confidence_threshold: float = 0.7):
        """Register a new thinking strategy."""
        self.strategies[name] = ThinkingStrategy(
            name=name,
            mode=mode,
            heuristics=heuristics,
            time_limit=time_limit,
            confidence_threshold=confidence_threshold
        )
        
    def think_about(self, problem: Any, mode: Optional[ThinkingMode] = None) -> Dict[str, Any]:
        """
        Apply thinking strategies to a problem.
        
        Args:
            problem: The problem to think about
            mode: Optional thinking mode override
            
        Returns:
            Dict with solution, confidence, and metadata
        """
        start_time = time.time()
        mode = mode or self.current_mode
        
        # Select strategy based on mode
        strategy = self._select_strategy(mode)
        
        results = {
            'problem': str(problem)[:100],  # Truncate for logging
            'mode': mode.value,
            'strategy': strategy.name,
            'solutions': [],
            'confidence': 0.0,
            'time_spent': 0.0,
            'heuristics_used': []
        }
        
        # Apply heuristics in order
        for heuristic_name in strategy.heuristics:
            if heuristic_name not in self.heuristics:
                continue
                
            heuristic = self.heuristics[heuristic_name]
            
            # Check time limit
            if strategy.time_limit and (time.time() - start_time) > strategy.time_limit:
                logger.debug(f"Time limit reached for {strategy.name}")
                break
                
            # Check applicability
            applicability = heuristic.applicability_check(problem)
            if applicability < 0.3:  # Skip if not applicable
                continue
                
            # Apply heuristic
            try:
                solution = heuristic.apply(problem)
                if solution:
                    results['solutions'].append({
                        'heuristic': heuristic_name,
                        'solution': solution,
                        'applicability': applicability
                    })
                    results['heuristics_used'].append(heuristic_name)
                    
                    # Update heuristic usage
                    heuristic.usage_count += 1
                    
            except Exception as e:
                logger.error(f"Heuristic {heuristic_name} failed: {e}")
                
            # Check if we have enough confidence
            if results['solutions'] and self._calculate_confidence(results) >= strategy.confidence_threshold:
                break
                
        # Finalize results
        results['time_spent'] = time.time() - start_time
        results['confidence'] = self._calculate_confidence(results)
        
        # Record performance
        self._performance_history.append(results)
        
        return results
        
    def allocate_resources(self, tasks: List[Any]) -> Dict[str, Any]:
        """
        Decide how to allocate thinking resources across multiple tasks.
        
        Args:
            tasks: List of tasks to prioritize
            
        Returns:
            Resource allocation plan
        """
        allocations = []
        
        for task in tasks:
            # Estimate complexity
            complexity = self._estimate_complexity(task)
            
            # Suggest mode based on complexity
            if complexity < 0.3:
                mode = ThinkingMode.FAST
            elif complexity < 0.7:
                mode = ThinkingMode.BALANCED
            else:
                mode = ThinkingMode.DEEP
                
            allocations.append({
                'task': str(task)[:50],
                'complexity': complexity,
                'suggested_mode': mode.value,
                'estimated_time': complexity * 10.0  # Simple linear estimate
            })
            
        # Sort by complexity (highest first)
        allocations.sort(key=lambda x: x['complexity'], reverse=True)
        
        return {
            'allocations': allocations,
            'total_estimated_time': sum(a['estimated_time'] for a in allocations),
            'recommendation': self._resource_recommendation(allocations)
        }
        
    def learn_from_outcome(self, problem: Any, heuristic_name: str, 
                          success: bool, solution_quality: float = 0.5):
        """
        Update heuristic performance based on outcomes.
        
        Args:
            problem: The problem that was solved
            heuristic_name: Which heuristic was used
            success: Whether it succeeded
            solution_quality: Quality score [0,1]
        """
        if heuristic_name not in self.heuristics:
            return
            
        heuristic = self.heuristics[heuristic_name]
        
        # Update success rate with exponential moving average
        alpha = 0.1  # Learning rate
        if success:
            heuristic.success_rate = (1 - alpha) * heuristic.success_rate + alpha * solution_quality
        else:
            heuristic.success_rate = (1 - alpha) * heuristic.success_rate
            
        logger.debug(
            f"Updated {heuristic_name} success rate: {heuristic.success_rate:.3f}"
        )
        
    def get_thinking_profile(self) -> Dict[str, Any]:
        """Get a profile of thinking patterns and performance."""
        if not self._performance_history:
            return {'error': 'No thinking history available'}
            
        # Analyze heuristic usage
        heuristic_usage = {}
        total_time = 0
        successful_thinks = 0
        
        for record in self._performance_history:
            total_time += record['time_spent']
            if record['confidence'] > 0.5:
                successful_thinks += 1
                
            for h in record['heuristics_used']:
                heuristic_usage[h] = heuristic_usage.get(h, 0) + 1
                
        return {
            'total_problems': len(self._performance_history),
            'successful_thinks': successful_thinks,
            'success_rate': successful_thinks / len(self._performance_history),
            'average_time': total_time / len(self._performance_history),
            'heuristic_usage': heuristic_usage,
            'preferred_mode': self.current_mode.value,
            'heuristic_performance': {
                name: {
                    'success_rate': h.success_rate,
                    'usage_count': h.usage_count,
                    'cost': h.cost
                }
                for name, h in self.heuristics.items()
            }
        }
        
    def _select_strategy(self, mode: ThinkingMode) -> ThinkingStrategy:
        """Select appropriate strategy for mode."""
        for strategy in self.strategies.values():
            if strategy.mode == mode:
                return strategy
        # Fallback to balanced
        return self.strategies['standard_analysis']
        
    def _calculate_confidence(self, results: Dict) -> float:
        """Calculate confidence in solutions."""
        if not results['solutions']:
            return 0.0
            
        # Simple average of applicability scores
        scores = [s['applicability'] for s in results['solutions']]
        return sum(scores) / len(scores)
        
    def _estimate_complexity(self, task: Any) -> float:
        """Estimate task complexity."""
        # Simple heuristics for now
        complexity = 0.5
        
        if hasattr(task, '__len__'):
            # Larger tasks are more complex
            complexity += min(0.3, len(task) / 100.0)
            
        if hasattr(task, 'dependencies'):
            # More dependencies = more complex
            complexity += min(0.2, len(task.dependencies) / 10.0)
            
        return min(1.0, complexity)
        
    def _resource_recommendation(self, allocations: List[Dict]) -> str:
        """Provide resource allocation recommendation."""
        total_time = sum(a['estimated_time'] for a in allocations)
        
        if total_time < 5:
            return "Light workload - can handle in parallel"
        elif total_time < 20:
            return "Moderate workload - prioritize complex tasks first"
        else:
            return "Heavy workload - consider batching or delegation"
            
    # Placeholder heuristic implementations
    def _pattern_match(self, x):
        """Simple pattern matching."""
        return f"Pattern match result for {type(x).__name__}"
        
    def _decompose(self, x):
        """Problem decomposition."""
        if hasattr(x, '__len__') and len(x) > 1:
            return f"Decomposed into {len(x)} parts"
        return "Cannot decompose"
        
    def _find_analogy(self, x):
        """Find analogous problems."""
        return f"Found analogy in domain {type(x).__name__}"
        
    def _first_principles(self, x):
        """Reason from first principles."""
        return f"First principles analysis of {type(x).__name__}"