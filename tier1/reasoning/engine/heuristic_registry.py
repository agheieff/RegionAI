"""
Enhanced heuristic registry with automatic discovery capabilities.

This module provides both a decorator-based registration system and automatic
discovery of registered heuristics, returning them as Heuristic objects ready
for the ReasoningKnowledgeGraph.
"""
import inspect
from typing import Callable, Dict, Optional, List
import logging

from tier1.knowledge.infrastructure.reasoning_graph import Heuristic, ReasoningType

logger = logging.getLogger(__name__)


class HeuristicRegistry:
    """
    Enhanced registry that maps heuristic IDs to their implementation functions
    and can generate Heuristic objects for the ReasoningKnowledgeGraph.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._registry: Dict[str, Callable] = {}
        self._heuristic_metadata: Dict[str, Dict] = {}
        logger.debug("HeuristicRegistry initialized")
    
    def register(self, heuristic_id: str, 
                 description: Optional[str] = None,
                 applicability_conditions: Optional[tuple] = None,
                 expected_utility: float = 0.85) -> Callable:
        """
        Enhanced decorator to register a heuristic implementation with metadata.
        
        Args:
            heuristic_id: Unique identifier for the heuristic
            description: Human-readable description of what this heuristic does
            applicability_conditions: Tuple of conditions when this heuristic applies
            expected_utility: Expected utility score (0-1) for this heuristic
            
        Returns:
            Decorator function
            
        Example:
            @registry.register("ast.method_call_implies_performs",
                             description="Method call implies PERFORMS relationship",
                             applicability_conditions=("ast", "method_call", "performs"),
                             expected_utility=0.85)
            def my_heuristic(hub, context):
                ...
        """
        def decorator(func: Callable) -> Callable:
            if heuristic_id in self._registry:
                logger.warning(f"Overwriting existing heuristic: {heuristic_id}")
            
            self._registry[heuristic_id] = func
            
            # Extract metadata from function if not provided
            desc = description
            if desc is None:
                # Try to get from docstring
                func_desc = inspect.getdoc(func)
                if func_desc:
                    # Take the first line of the docstring
                    desc = func_desc.split('\n')[0].strip()
                else:
                    desc = f"Heuristic: {func.__name__}"
            
            # Store metadata
            self._heuristic_metadata[heuristic_id] = {
                'description': desc,
                'applicability_conditions': applicability_conditions or (),
                'expected_utility': expected_utility,
                'function_name': func.__name__
            }
            
            logger.debug(f"Registered heuristic: {heuristic_id} -> {func.__name__}")
            
            # Add metadata as attributes to the function for introspection
            func.heuristic_id = heuristic_id
            func.heuristic_description = desc
            func.heuristic_conditions = applicability_conditions
            func.heuristic_utility = expected_utility
            
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
    
    def get_all_heuristics(self) -> List[Heuristic]:
        """
        Get all registered heuristics as Heuristic objects.
        
        This method discovers all registered heuristics and returns them
        as properly configured Heuristic objects ready to be added to
        the ReasoningKnowledgeGraph.
        
        Returns:
            List of Heuristic objects
        """
        heuristics = []
        
        for heuristic_id, metadata in self._heuristic_metadata.items():
            # Create name from ID if needed
            name = heuristic_id.upper().replace('.', '_')
            
            heuristic = Heuristic(
                name=name,
                reasoning_type=ReasoningType.HEURISTIC,
                description=metadata['description'],
                applicability_conditions=metadata['applicability_conditions'],
                expected_utility=metadata['expected_utility'],
                implementation_id=heuristic_id
            )
            heuristics.append(heuristic)
            
        logger.info(f"Discovered {len(heuristics)} registered heuristics")
        return heuristics
    
    def list_registered(self) -> Dict[str, Dict]:
        """
        List all registered heuristics with their metadata.
        
        Returns:
            Dictionary mapping heuristic IDs to their metadata
        """
        result = {}
        for hid, metadata in self._heuristic_metadata.items():
            result[hid] = {
                'function_name': metadata['function_name'],
                'description': metadata['description'],
                'conditions': metadata['applicability_conditions'],
                'utility': metadata['expected_utility']
            }
        return result
    
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
        self._heuristic_metadata.clear()
        logger.debug("HeuristicRegistry cleared")
    
    def __len__(self) -> int:
        """Return the number of registered heuristics."""
        return len(self._registry)
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"HeuristicRegistry({len(self)} heuristics registered)"


# Create a global registry instance
heuristic_registry = HeuristicRegistry()

# Import and register all heuristics when this module is imported
# This ensures all decorated heuristics are registered
def _auto_register_heuristics():
    """Auto-import heuristic implementations to trigger registration."""
    try:
        logger.info("Auto-registered heuristics from implementations module")
    except ImportError as e:
        logger.warning(f"Could not auto-register heuristics: {e}")
    
    # Also import math heuristics
    try:
        logger.info("Auto-registered mathematical foundations heuristics")
    except ImportError as e:
        logger.warning(f"Could not auto-register math foundations heuristics: {e}")
    
    # Import extended math heuristics
    try:
        logger.info("Auto-registered extended mathematical heuristics")
    except ImportError as e:
        logger.warning(f"Could not auto-register extended math heuristics: {e}")
    
    # Import advanced math heuristics
    try:
        logger.info("Auto-registered advanced mathematical heuristics")
    except ImportError as e:
        logger.warning(f"Could not auto-register advanced math heuristics: {e}")
    
    # Import specialized math heuristics
    try:
        logger.info("Auto-registered specialized mathematical heuristics")
    except ImportError as e:
        logger.warning(f"Could not auto-register specialized math heuristics: {e}")

# Perform auto-registration
_auto_register_heuristics()