"""
World context overlay implementation.
"""

from typing import Dict, Any
from ..overlay import SituationalOverlay, SituationContext


class WorldOverlay(SituationalOverlay):
    """
    Overlay for world-specific contexts and parameters.
    
    This overlay handles world models, physical parameters, and
    environmental contexts that affect reasoning behavior.
    """
    
    def get_situation_type(self) -> str:
        """Get the type of situation this overlay handles."""
        return "world_context"
    
    def create_context(self, parameters: Dict[str, Any]) -> SituationContext:
        """Create a world context with given parameters."""
        return SituationContext(
            situation_id=self.situation_id,
            situation_type=self.get_situation_type(),
            name=self.name,
            parameters=parameters,
            preferences={},
            constraints={}
        )
    
    def apply_overlay(self, reasoning_input: Any, domain_knowledge: Dict[str, Any]) -> Any:
        """Apply the world overlay to reasoning input."""
        # For now, just return the input with world parameters attached
        if isinstance(reasoning_input, dict):
            reasoning_input = reasoning_input.copy()
            reasoning_input["world_parameters"] = self.get_context().parameters
        
        return reasoning_input