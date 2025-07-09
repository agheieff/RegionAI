"""Core interfaces for RegionAI."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class Region(Protocol):
    """Interface for any region in n-dimensional space."""
    
    @abstractmethod
    def contains(self, other: 'Region') -> bool:
        """Check if this region contains another region.
        
        Args:
            other: Another region to check containment for
            
        Returns:
            True if this region contains the other region
        """
        ...
    
    @abstractmethod
    def overlaps(self, other: 'Region') -> bool:
        """Check if this region overlaps with another region.
        
        Args:
            other: Another region to check overlap with
            
        Returns:
            True if the regions overlap
        """
        ...
    
    @abstractmethod
    def volume(self) -> float:
        """Calculate the volume (area in 2D, volume in 3D, etc.) of this region.
        
        Returns:
            The volume of the region
        """
        ...


@runtime_checkable
class ConceptSpace(Protocol):
    """Interface for managing collections of regions."""
    
    @abstractmethod
    def add_region(self, name: str, region: Region) -> None:
        """Add a named region to the concept space.
        
        Args:
            name: Name identifier for the region
            region: The region to add
        """
        ...
    
    @abstractmethod
    def get_region(self, name: str) -> Region:
        """Get a region by name.
        
        Args:
            name: Name of the region to retrieve
            
        Returns:
            The region associated with the given name
            
        Raises:
            KeyError: If no region exists with the given name
        """
        ...