"""
User context overlay implementation.
"""

from typing import Dict, Any
from ..overlay import SituationalOverlay, SituationContext


class UserOverlay(SituationalOverlay):
    """
    Overlay for user-specific contexts and preferences.
    
    This overlay handles user preferences, customizations, and
    personal contexts that affect reasoning behavior.
    """
    
    def get_situation_type(self) -> str:
        """Get the type of situation this overlay handles."""
        return "user_context"
    
    def create_context(self, parameters: Dict[str, Any]) -> SituationContext:
        """Create a user context with given parameters."""
        return SituationContext(
            situation_id=self.situation_id,
            situation_type=self.get_situation_type(),
            name=self.name,
            parameters=parameters,
            preferences={},
            constraints={}
        )
    
    def apply_overlay(self, reasoning_input: Any, domain_knowledge: Dict[str, Any]) -> Any:
        """Apply the user overlay to reasoning input."""
        # For now, just return the input with user preferences attached
        if isinstance(reasoning_input, dict):
            reasoning_input = reasoning_input.copy()
            reasoning_input["user_preferences"] = self.get_context().preferences
        
        return reasoning_input