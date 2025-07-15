"""
Base classes for RegionAI brains.

Provides common interface and functionality for all brain types.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..config import RegionAIConfig


class Brain(ABC):
    """
    Abstract base class for all RegionAI brains.
    
    Each brain (Bayesian, Utility, Symbolic, Temporal, MetaCognitive, Embodiment)
    inherits from this base class.
    """
    
    def __init__(self, config: RegionAIConfig):
        """
        Initialize brain with configuration.
        
        Args:
            config: RegionAIConfig object
        """
        self.config = config
        self.name = self.__class__.__name__
        self.is_active = True
        self.performance_metrics: Dict[str, float] = {}
        
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and produce output.
        
        Args:
            input_data: Input data for processing
            
        Returns:
            Processing results
        """
        pass
        
    def get_state(self) -> Dict[str, Any]:
        """
        Get current brain state.
        
        Returns:
            State dictionary
        """
        return {
            "name": self.name,
            "is_active": self.is_active,
            "performance_metrics": self.performance_metrics
        }
        
    def reset(self) -> None:
        """Reset brain to initial state."""
        self.performance_metrics.clear()
        
    def update_metrics(self, metrics: Dict[str, float]) -> None:
        """Update performance metrics."""
        self.performance_metrics.update(metrics)