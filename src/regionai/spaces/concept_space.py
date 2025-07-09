"""ConceptSpaceND implementation for managing N-dimensional concept regions."""

from typing import Dict, Iterator, Tuple, Optional
from ..geometry.region import RegionND


class ConceptSpaceND:
    """Container for named N-dimensional concept regions."""

    def __init__(self):
        """Initialize an empty concept space."""
        self._regions: Dict[str, RegionND] = {}

    def add_region(self, name: str, region: RegionND) -> None:
        """Add a named region to the concept space.

        Args:
            name: Name identifier for the region
            region: The RegionND region to add
        """
        self._regions[name] = region

    def get_region(self, name: str) -> RegionND:
        """Get a region by name.

        Args:
            name: Name of the region to retrieve

        Returns:
            The RegionND region

        Raises:
            KeyError: If no region exists with the given name
        """
        return self._regions[name]

    def get_parent(self, region_name: str) -> Optional[str]:
        """Find the direct parent of a given region.

        This method finds which other region in the space directly contains
        the given region. It returns the smallest container that is not the
        region itself, avoiding grandparents or larger containers.

        Args:
            region_name: Name of the region to find parent for

        Returns:
            Name of the parent region, or None if no parent exists
        """
        if region_name not in self._regions:
            return None

        target_region = self._regions[region_name]

        # Find all regions that contain the target
        parent_candidates = []
        for name, region in self._regions.items():
            if name != region_name and region.contains(target_region):
                parent_candidates.append((name, region.volume()))

        # If no containers found, region has no parent
        if not parent_candidates:
            return None

        # Return the smallest container (direct parent)
        parent_candidates.sort(key=lambda x: x[1])
        return parent_candidates[0][0]

    def items(self) -> Iterator[Tuple[str, RegionND]]:
        """Iterate over (name, region) pairs."""
        return iter(self._regions.items())

    def __len__(self) -> int:
        """Return the number of regions."""
        return len(self._regions)

    def __iter__(self) -> Iterator[str]:
        """Iterate over region names."""
        return iter(self._regions)

    def __contains__(self, name: str) -> bool:
        """Check if a region name exists in the space."""
        return name in self._regions


# Backward compatibility alias
ConceptSpace2D = ConceptSpaceND
