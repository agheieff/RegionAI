"""
Base class for situational overlays.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SituationContext:
    """Context information for a specific situation."""
    situation_id: str
    situation_type: str  # "user_context", "world_context", "scenario"
    name: str
    parameters: Dict[str, Any]
    preferences: Dict[str, Any]
    constraints: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation_id": self.situation_id,
            "situation_type": self.situation_type,
            "name": self.name,
            "parameters": self.parameters,
            "preferences": self.preferences,
            "constraints": self.constraints
        }


class SituationalOverlay(ABC):
    """
    Abstract base class for situational overlays.
    
    Overlays provide context-specific adaptations to the universal reasoning
    engine and domain knowledge without modifying the underlying systems.
    """
    
    def __init__(self, situation_id: str, name: str):
        self.situation_id = situation_id
        self.name = name
        self._context: Optional[SituationContext] = None
    
    @abstractmethod
    def get_situation_type(self) -> str:
        """Get the type of situation this overlay handles."""
        pass
    
    @abstractmethod
    def create_context(self, parameters: Dict[str, Any]) -> SituationContext:
        """Create a situation context with given parameters."""
        pass
    
    @abstractmethod
    def apply_overlay(self, reasoning_input: Any, domain_knowledge: Dict[str, Any]) -> Any:
        """Apply the situational overlay to reasoning input."""
        pass
    
    def get_context(self) -> SituationContext:
        """Get the current situation context."""
        if self._context is None:
            self._context = self.create_context({})
        return self._context
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference in this situation."""
        context = self.get_context()
        context.preferences[key] = value
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference from this situation."""
        context = self.get_context()
        return context.preferences.get(key, default)
    
    def set_constraint(self, key: str, value: Any) -> None:
        """Set a constraint in this situation."""
        context = self.get_context()
        context.constraints[key] = value
    
    def get_constraint(self, key: str, default: Any = None) -> Any:
        """Get a constraint from this situation."""
        context = self.get_context()
        return context.constraints.get(key, default)
    
    def fork(self, new_name: str) -> 'SituationalOverlay':
        """Create a fork of this overlay with a new name."""
        # This is a simplified fork - in practice, this would create
        # a new overlay instance with copied context
        import copy
        import uuid
        
        new_overlay = copy.deepcopy(self)
        new_overlay.situation_id = str(uuid.uuid4())
        new_overlay.name = new_name
        return new_overlay
    
    def __str__(self) -> str:
        return f"SituationalOverlay({self.name})"
    
    def __repr__(self) -> str:
        return f"SituationalOverlay(id='{self.situation_id}', name='{self.name}', type='{self.get_situation_type()}')"