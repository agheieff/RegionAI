"""Simple ConceptSpace2D implementation for managing 2D concept regions."""

from typing import Dict, Iterator, Tuple
from ..geometry.box2d import Box2D


class ConceptSpace2D:
    """Simple container for named 2D concept regions."""
    
    def __init__(self):
        """Initialize an empty concept space."""
        self._regions: Dict[str, Box2D] = {}
    
    def add_region(self, name: str, region: Box2D) -> None:
        """Add a named region to the concept space.
        
        Args:
            name: Name identifier for the region
            region: The Box2D region to add
        """
        self._regions[name] = region
    
    def get_region(self, name: str) -> Box2D:
        """Get a region by name.
        
        Args:
            name: Name of the region to retrieve
            
        Returns:
            The Box2D region
            
        Raises:
            KeyError: If no region exists with the given name
        """
        return self._regions[name]
    
    def items(self) -> Iterator[Tuple[str, Box2D]]:
        """Iterate over (name, region) pairs."""
        return iter(self._regions.items())
    
    def __len__(self) -> int:
        """Return the number of regions."""
        return len(self._regions)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over region names."""
        return iter(self._regions)