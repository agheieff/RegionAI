"""
Situation Manager for handling situational overlays.
"""

from typing import Dict, Any, Optional, List
import uuid
from .overlay import SituationalOverlay, SituationContext


class SituationManager:
    """
    Manages situational overlays and their contexts.
    
    Handles user contexts, world contexts, and scenarios that provide
    situational adaptations to the universal reasoning engine.
    """
    
    def __init__(self):
        self._overlays: Dict[str, SituationalOverlay] = {}
        self._active_overlays: List[str] = []
    
    def create_user_context(self, name: str, preferences: Dict[str, Any] = None) -> str:
        """
        Create a new user context overlay.
        
        Args:
            name: Name of the user context
            preferences: User preferences
            
        Returns:
            Situation ID of the created context
        """
        from .user_contexts.user_overlay import UserOverlay
        
        situation_id = str(uuid.uuid4())
        overlay = UserOverlay(situation_id, name)
        
        if preferences:
            for key, value in preferences.items():
                overlay.set_preference(key, value)
        
        self._overlays[situation_id] = overlay
        return situation_id
    
    def create_world_context(self, name: str, world_parameters: Dict[str, Any] = None) -> str:
        """
        Create a new world context overlay.
        
        Args:
            name: Name of the world context
            world_parameters: World-specific parameters
            
        Returns:
            Situation ID of the created context
        """
        from .world_contexts.world_overlay import WorldOverlay
        
        situation_id = str(uuid.uuid4())
        overlay = WorldOverlay(situation_id, name)
        
        if world_parameters:
            context = overlay.get_context()
            context.parameters.update(world_parameters)
        
        self._overlays[situation_id] = overlay
        return situation_id
    
    def create_scenario(self, name: str, scenario_type: str, parameters: Dict[str, Any] = None) -> str:
        """
        Create a new scenario overlay.
        
        Args:
            name: Name of the scenario
            scenario_type: Type of scenario (e.g., "embodiment", "temporal")
            parameters: Scenario-specific parameters
            
        Returns:
            Situation ID of the created scenario
        """
        from .scenarios.scenario_overlay import ScenarioOverlay
        
        situation_id = str(uuid.uuid4())
        overlay = ScenarioOverlay(situation_id, name, scenario_type)
        
        if parameters:
            context = overlay.get_context()
            context.parameters.update(parameters)
        
        self._overlays[situation_id] = overlay
        return situation_id
    
    def get_overlay(self, situation_id: str) -> Optional[SituationalOverlay]:
        """Get an overlay by situation ID."""
        return self._overlays.get(situation_id)
    
    def activate_overlay(self, situation_id: str) -> None:
        """Activate an overlay for use in reasoning."""
        if situation_id in self._overlays and situation_id not in self._active_overlays:
            self._active_overlays.append(situation_id)
    
    def deactivate_overlay(self, situation_id: str) -> None:
        """Deactivate an overlay."""
        if situation_id in self._active_overlays:
            self._active_overlays.remove(situation_id)
    
    def get_active_overlays(self) -> List[SituationalOverlay]:
        """Get all currently active overlays."""
        return [self._overlays[sid] for sid in self._active_overlays if sid in self._overlays]
    
    def apply_overlays(self, reasoning_input: Any, domain_knowledge: Dict[str, Any]) -> Any:
        """
        Apply all active overlays to reasoning input.
        
        Args:
            reasoning_input: Input to the reasoning process
            domain_knowledge: Domain knowledge from tier2
            
        Returns:
            Modified reasoning input with overlays applied
        """
        result = reasoning_input
        
        for overlay in self.get_active_overlays():
            result = overlay.apply_overlay(result, domain_knowledge)
        
        return result
    
    def fork_overlay(self, situation_id: str, new_name: str) -> Optional[str]:
        """
        Fork an existing overlay to create a new one.
        
        Args:
            situation_id: ID of the overlay to fork
            new_name: Name for the new overlay
            
        Returns:
            Situation ID of the forked overlay, or None if original not found
        """
        if situation_id not in self._overlays:
            return None
        
        original = self._overlays[situation_id]
        forked = original.fork(new_name)
        
        self._overlays[forked.situation_id] = forked
        return forked.situation_id
    
    def remove_overlay(self, situation_id: str) -> None:
        """Remove an overlay."""
        if situation_id in self._overlays:
            # Deactivate first
            self.deactivate_overlay(situation_id)
            # Remove from storage
            del self._overlays[situation_id]
    
    def list_overlays(self) -> List[Dict[str, Any]]:
        """List all overlays with their information."""
        return [
            {
                "situation_id": overlay.situation_id,
                "name": overlay.name,
                "type": overlay.get_situation_type(),
                "active": overlay.situation_id in self._active_overlays
            }
            for overlay in self._overlays.values()
        ]
    
    def get_situation_info(self, situation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a situation."""
        if situation_id not in self._overlays:
            return None
        
        overlay = self._overlays[situation_id]
        context = overlay.get_context()
        
        return {
            "situation_id": situation_id,
            "name": overlay.name,
            "type": overlay.get_situation_type(),
            "active": situation_id in self._active_overlays,
            "context": context.to_dict()
        }