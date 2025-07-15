"""
Registry for heuristic implementations.

This module provides a registry that maps heuristic IDs to their executable
functions, enabling the dynamic reasoning engine to execute heuristics based
on the ReasoningKnowledgeGraph.
"""
from typing import Callable, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HeuristicRegistry:
    """
    Registry that maps heuristic IDs to their implementation functions.
    
    This enables the reasoning engine to dynamically execute heuristics
    based on their ID in the ReasoningKnowledgeGraph.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._registry: Dict[str, Callable] = {}
        logger.debug("HeuristicRegistry initialized")
    
    def register(self, heuristic_id: str) -> Callable:
        """
        Decorator to register a heuristic implementation.
        
        Args:
            heuristic_id: Unique identifier for the heuristic
            
        Returns:
            Decorator function
            
        Example:
            @registry.register("ast.method_call_implies_performs")
            def my_heuristic(hub, context):
                ...
        """
        def decorator(func: Callable) -> Callable:
            if heuristic_id in self._registry:
                logger.warning(f"Overwriting existing heuristic: {heuristic_id}")
            
            self._registry[heuristic_id] = func
            logger.debug(f"Registered heuristic: {heuristic_id} -> {func.__name__}")
            
            # Add the ID as an attribute to the function for introspection
            func.heuristic_id = heuristic_id
            
            return func
        
        return decorator
    
    def get(self, heuristic_id: str) -> Optional[Callable]:
        """
        Retrieve a heuristic implementation by its ID.
        
        Args:
            heuristic_id: The ID of the heuristic to retrieve
            
        Returns:
            The heuristic function, or None if not found
        """
        func = self._registry.get(heuristic_id)
        if func is None:
            logger.warning(f"Heuristic not found: {heuristic_id}")
        return func
    
    def list_registered(self) -> Dict[str, str]:
        """
        List all registered heuristics.
        
        Returns:
            Dictionary mapping heuristic IDs to function names
        """
        return {
            hid: func.__name__ 
            for hid, func in self._registry.items()
        }
    
    def is_registered(self, heuristic_id: str) -> bool:
        """
        Check if a heuristic ID is registered.
        
        Args:
            heuristic_id: The ID to check
            
        Returns:
            True if registered, False otherwise
        """
        return heuristic_id in self._registry
    
    def clear(self):
        """Clear all registered heuristics (useful for testing)."""
        self._registry.clear()
        logger.debug("HeuristicRegistry cleared")
    
    def __len__(self) -> int:
        """Return the number of registered heuristics."""
        return len(self._registry)
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"HeuristicRegistry({len(self)} heuristics registered)"


# Create a global registry instance
heuristic_registry = HeuristicRegistry()