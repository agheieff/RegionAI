"""
Simple brain implementations for tier1 that provide basic functionality.
"""

from typing import Any, Dict, Optional
from tier1.config import RegionAIConfig


class SimpleBrain:
    """Base class for simple brain implementations."""
    
    def __init__(self, config: Optional[RegionAIConfig] = None):
        self.config = config or RegionAIConfig()
        self.name = self.__class__.__name__
    
    def reason(self, input_data: Any) -> Any:
        """Basic reasoning method."""
        return {
            "brain": self.name,
            "result": f"Processed by {self.name}",
            "confidence": 0.5
        }


class BayesianBrain(SimpleBrain):
    """Simple Bayesian reasoning brain."""
    
    def reason(self, input_data: Any) -> Any:
        """Bayesian reasoning with uncertainty."""
        result = super().reason(input_data)
        result["reasoning_type"] = "bayesian"
        result["uncertainty"] = 0.3
        return result


class LogicBrain(SimpleBrain):
    """Simple logic reasoning brain."""
    
    def reason(self, input_data: Any) -> Any:
        """Logical reasoning with rules."""
        result = super().reason(input_data)
        result["reasoning_type"] = "logical"
        result["rules_applied"] = []
        return result


class UtilityBrain(SimpleBrain):
    """Simple utility-based reasoning brain."""
    
    def reason(self, input_data: Any) -> Any:
        """Utility-based reasoning."""
        result = super().reason(input_data)
        result["reasoning_type"] = "utility"
        result["utility_score"] = 0.6
        return result


class ObserverBrain(SimpleBrain):
    """Simple observer brain for pattern recognition."""
    
    def reason(self, input_data: Any) -> Any:
        """Pattern observation and recognition."""
        result = super().reason(input_data)
        result["reasoning_type"] = "observation"
        result["patterns_observed"] = []
        return result


class TemporalBrain(SimpleBrain):
    """Simple temporal reasoning brain."""
    
    def reason(self, input_data: Any) -> Any:
        """Temporal reasoning with time awareness."""
        result = super().reason(input_data)
        result["reasoning_type"] = "temporal"
        result["time_horizon"] = "immediate"
        return result


class SensorimotorBrain(SimpleBrain):
    """Simple sensorimotor brain for embodied reasoning."""
    
    def reason(self, input_data: Any) -> Any:
        """Sensorimotor reasoning for embodied tasks."""
        result = super().reason(input_data)
        result["reasoning_type"] = "sensorimotor"
        result["embodiment_context"] = "abstract"
        return result