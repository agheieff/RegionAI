"""ConceptSpace2D implementation for managing 2D concept regions."""

from typing import Dict, List, Optional
from ..core.interfaces import ConceptSpace, Region
from ..geometry.box2d import Box2D


class ConceptSpace2D:
    """Manages a collection of named 2D concept regions."""
    
    def __init__(self):
        """Initialize an empty concept space."""
        self._regions: Dict[str, Box2D] = {}
    
    def add_region(self, name: str, region: Region) -> None:
        """Add a named region to the concept space.
        
        Args:
            name: Name identifier for the region
            region: The region to add (must be Box2D)
            
        Raises:
            TypeError: If region is not a Box2D
            ValueError: If name already exists
        """
        if not isinstance(region, Box2D):
            raise TypeError(f"Expected Box2D, got {type(region).__name__}")
        
        if name in self._regions:
            raise ValueError(f"Region '{name}' already exists")
            
        self._regions[name] = region
    
    def get_region(self, name: str) -> Region:
        """Get a region by name.
        
        Args:
            name: Name of the region to retrieve
            
        Returns:
            The region associated with the given name
            
        Raises:
            KeyError: If no region exists with the given name
        """
        if name not in self._regions:
            raise KeyError(f"No region found with name '{name}'")
        return self._regions[name]
    
    def list_regions(self) -> List[str]:
        """List all region names in the concept space.
        
        Returns:
            List of region names
        """
        return list(self._regions.keys())
    
    def find_containing_regions(self, region: Box2D) -> List[str]:
        """Find all regions that contain the given region.
        
        Args:
            region: The region to check
            
        Returns:
            List of names of regions that contain the given region
        """
        containing = []
        for name, concept_region in self._regions.items():
            if concept_region.contains(region):
                containing.append(name)
        return containing
    
    def find_overlapping_regions(self, region: Box2D) -> List[str]:
        """Find all regions that overlap with the given region.
        
        Args:
            region: The region to check
            
        Returns:
            List of names of regions that overlap with the given region
        """
        overlapping = []
        for name, concept_region in self._regions.items():
            if concept_region.overlaps(region):
                overlapping.append(name)
        return overlapping
    
    def find_contained_regions(self, region: Box2D) -> List[str]:
        """Find all regions contained within the given region.
        
        Args:
            region: The region to check
            
        Returns:
            List of names of regions contained within the given region
        """
        contained = []
        for name, concept_region in self._regions.items():
            if region.contains(concept_region):
                contained.append(name)
        return contained
    
    def get_hierarchical_relationships(self) -> Dict[str, List[str]]:
        """Analyze hierarchical containment relationships between all regions.
        
        Returns:
            Dictionary mapping each region name to list of regions it contains
        """
        relationships = {}
        for parent_name, parent_region in self._regions.items():
            children = []
            for child_name, child_region in self._regions.items():
                if parent_name != child_name and parent_region.contains(child_region):
                    children.append(child_name)
            relationships[parent_name] = children
        return relationships
    
    def remove_region(self, name: str) -> None:
        """Remove a region from the concept space.
        
        Args:
            name: Name of the region to remove
            
        Raises:
            KeyError: If no region exists with the given name
        """
        if name not in self._regions:
            raise KeyError(f"No region found with name '{name}'")
        del self._regions[name]
    
    def clear(self) -> None:
        """Remove all regions from the concept space."""
        self._regions.clear()
    
    def __len__(self) -> int:
        """Return the number of regions in the concept space."""
        return len(self._regions)
    
    def __contains__(self, name: str) -> bool:
        """Check if a region with the given name exists."""
        return name in self._regions
    
    def __iter__(self):
        """Iterate over region names."""
        return iter(self._regions)
    
    def items(self):
        """Iterate over (name, region) pairs."""
        return self._regions.items()