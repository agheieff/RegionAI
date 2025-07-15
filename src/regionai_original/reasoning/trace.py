"""
Reasoning trace logging for the RegionAI reasoning engine.

This module provides data structures for capturing successful reasoning
patterns, enabling the system to analyze and synthesize new heuristics
from effective reasoning chains.
"""
from dataclasses import dataclass, field
from typing import List
from uuid import UUID, uuid4
from datetime import datetime


@dataclass
class ReasoningTrace:
    """
    A trace of a successful reasoning chain.
    
    Captures the sequence of heuristics that successfully discovered
    new knowledge during a discovery cycle. These traces form the raw
    material for heuristic synthesis.
    """
    id: UUID = field(default_factory=uuid4)
    context_tag: str = ""
    successful_heuristic_ids: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Additional metadata
    total_discoveries: int = 0
    analysis_target_preview: str = ""  # First 100 chars of analyzed code
    
    def __post_init__(self):
        """Validate the trace."""
        if not self.context_tag:
            raise ValueError("context_tag cannot be empty")
    
    def add_successful_heuristic(self, heuristic_id: str) -> None:
        """
        Record that a heuristic succeeded in this reasoning chain.
        
        Args:
            heuristic_id: The implementation ID of the successful heuristic
        """
        if heuristic_id and heuristic_id not in self.successful_heuristic_ids:
            self.successful_heuristic_ids.append(heuristic_id)
    
    def is_meaningful(self) -> bool:
        """
        Check if this trace represents a meaningful reasoning pattern.
        
        A trace is meaningful if it contains at least 2 successful heuristics,
        suggesting a potential reasoning chain worth synthesizing.
        """
        return len(self.successful_heuristic_ids) >= 2
    
    def get_pattern_key(self) -> str:
        """
        Get a key representing the reasoning pattern.
        
        Used for identifying recurring patterns across multiple traces.
        """
        return f"{self.context_tag}::{','.join(self.successful_heuristic_ids)}"
    
    def __repr__(self) -> str:
        """String representation of the trace."""
        return (f"ReasoningTrace(id={self.id}, context='{self.context_tag}', "
                f"chain={self.successful_heuristic_ids}, discoveries={self.total_discoveries})")