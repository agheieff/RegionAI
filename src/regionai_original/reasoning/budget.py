"""
Discovery Budget for the RegionAI reasoning engine.

This module provides budget constraints for the discovery process,
allowing the engine to limit its reasoning efforts based on available resources.
"""
from dataclasses import dataclass


@dataclass
class DiscoveryBudget:
    """
    Constraints for a discovery cycle.
    
    The budget controls how many resources the reasoning engine can consume
    during a single discovery cycle. This enables intelligent prioritization
    where the engine focuses on the most promising heuristics first.
    """
    max_heuristics_to_run: int
    
    def __post_init__(self):
        """Validate budget constraints."""
        if self.max_heuristics_to_run <= 0:
            raise ValueError("max_heuristics_to_run must be positive")