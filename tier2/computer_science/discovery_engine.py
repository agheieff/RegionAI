"""
Unified discovery engine with strategy pattern for different discovery approaches.
"""
from typing import List, Optional

from tier1.data.problem import Problem
from tier1.geometry.region import RegionND
from .strategies import (
    DiscoveryStrategy,
    SequentialDiscovery,
    ConditionalDiscovery,
    IterativeDiscovery
)


class UnifiedDiscoveryEngine:
    """
    Main discovery engine that orchestrates different strategies.
    """
    
    def __init__(self):
        self.strategies = {
            'sequential': SequentialDiscovery(),
            'conditional': ConditionalDiscovery(),
            'iterative': IterativeDiscovery()
        }
        self.discovery_order = ['sequential', 'conditional', 'iterative']
    
    def discover(self, problems: List[Problem], 
                strategy: Optional[str] = None) -> Optional[RegionND]:
        """
        Discover new concepts using specified or all strategies.
        
        Args:
            problems: Failed problems to analyze
            strategy: Specific strategy to use, or None to try all
            
        Returns:
            Discovered concept region or None
        """
        if strategy:
            if strategy in self.strategies:
                return self.strategies[strategy].discover(problems)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
        
        # Try strategies in order
        for strat_name in self.discovery_order:
            print(f"\nTrying {strat_name} discovery...")
            result = self.strategies[strat_name].discover(problems)
            if result:
                print(f"Success with {strat_name} discovery!")
                return result
        
        return None
    
    def add_strategy(self, name: str, strategy: DiscoveryStrategy):
        """Add a new discovery strategy."""
        self.strategies[name] = strategy
        if name not in self.discovery_order:
            self.discovery_order.append(name)
    
    def remove_strategy(self, name: str):
        """Remove a discovery strategy."""
        if name in self.strategies:
            del self.strategies[name]
            if name in self.discovery_order:
                self.discovery_order.remove(name)
    
    def set_discovery_order(self, order: List[str]):
        """Set the order in which strategies are tried."""
        # Validate all strategies exist
        for strat in order:
            if strat not in self.strategies:
                raise ValueError(f"Unknown strategy in order: {strat}")
        self.discovery_order = order