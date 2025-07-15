"""
Main discovery module - now a facade for the unified discovery engine.
Maintains backward compatibility while using the new strategy-based engine.
"""
from typing import List, Optional, Dict
import warnings
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .discovery_engine import UnifiedDiscoveryEngine, SequentialDiscovery
from tier1.data.problem import Problem
from tier1.core.region import RegionND


# Global engine instance
_discovery_engine = UnifiedDiscoveryEngine()


class DiscoveryEngine:
    """
    Main discovery engine class for transformation discovery.
    This is the primary interface for discovering new transformations.
    """
    
    def __init__(self, primitives=None, max_search_depth=3):
        """
        Initialize discovery engine.
        
        Args:
            primitives: List of primitive transformations (for compatibility)
            max_search_depth: Maximum depth for search
        """
        self.engine = UnifiedDiscoveryEngine()
        self.max_search_depth = max_search_depth
        
        # Update strategy parameters if needed
        for strategy in self.engine.strategies.values():
            if hasattr(strategy, 'max_depth'):
                strategy.max_depth = max_search_depth
    
    def discover_transformations(self, problems: List[Problem], 
                               strategy: Optional[str] = None) -> List[RegionND]:
        """
        Discover transformations that solve the given problems.
        
        Args:
            problems: List of problems to solve
            strategy: Specific strategy to use ('sequential', 'conditional', 'iterative')
                     or None to try all strategies
        
        Returns:
            List of discovered transformation regions
        """
        discovered = []
        
        # Group problems by type
        problem_groups = self._group_problems_by_type(problems)
        
        for problem_type, group_problems in problem_groups.items():
            print(f"\nAnalyzing {len(group_problems)} {problem_type} problems...")
            
            # Try discovery
            result = self.engine.discover(group_problems, strategy)
            if result:
                discovered.append(result)
                print(f"✓ Discovered: {result.name}")
        
        return discovered
    
    def _group_problems_by_type(self, problems: List[Problem]) -> Dict[str, List[Problem]]:
        """Group problems by their input/output characteristics."""
        groups = {}
        
        for problem in problems:
            # Determine problem type
            if hasattr(problem.input_data, 'dim'):
                # Tensor problems
                key = 'tensor'
            elif isinstance(problem.input_data, list) and problem.input_data:
                if isinstance(problem.input_data[0], dict):
                    key = 'structured'
                else:
                    key = 'list'
            else:
                key = 'other'
            
            if key not in groups:
                groups[key] = []
            groups[key].append(problem)
        
        return groups
    
    def set_strategy_order(self, order: List[str]):
        """Set the order in which discovery strategies are tried."""
        self.engine.set_discovery_order(order)


# Legacy function for backward compatibility
def discover_transformations(problems: List[Problem]) -> List[RegionND]:
    """
    Legacy function for discovering transformations.
    
    Deprecated: Use DiscoveryEngine class instead.
    """
    warnings.warn(
        "discover_transformations() is deprecated. Use DiscoveryEngine class instead.",
        DeprecationWarning,
        stacklevel=2
    )
    engine = DiscoveryEngine()
    return engine.discover_transformations(problems)


# Legacy function from original discover.py
def discover_concept_from_failures(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Legacy function maintained for backward compatibility.
    Uses sequential discovery strategy.
    """
    if not failed_problems:
        return None
    
    strategy = SequentialDiscovery()
    return strategy.discover(failed_problems)


# Re-export for convenience
__all__ = [
    'DiscoveryEngine',
    'discover_transformations',
    'discover_concept_from_failures',
    'UnifiedDiscoveryEngine'
]