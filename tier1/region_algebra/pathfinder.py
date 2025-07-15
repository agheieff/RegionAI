"""Pathfinder module for finding hierarchical paths between concepts."""

from typing import TYPE_CHECKING, List, Optional
from collections import deque

if TYPE_CHECKING:
    from tier1.spaces.concept_space import ConceptSpaceND


class Pathfinder:
    """Stateless utility class for finding paths between concepts in a concept space."""

    @staticmethod
    def find_path(
        start_region_name: str, end_region_name: str, space: "ConceptSpaceND"
    ) -> Optional[List[str]]:
        """Find the shortest hierarchical path from start region to end region.

        This method implements a Breadth-First Search (BFS) algorithm to find the shortest
        path through the concept hierarchy. The search moves "up" the hierarchy, following
        parent-child relationships where a child can move to its parent.

        Args:
            start_region_name: Name of the starting region
            end_region_name: Name of the target region
            space: The concept space containing the regions

        Returns:
            A list of region names representing the path from start to end (inclusive),
            or None if no path exists.

        Example:
            If SIAMESE is inside CAT, which is inside ANIMAL:
            find_path("SIAMESE", "ANIMAL", space) -> ["SIAMESE", "CAT", "ANIMAL"]
        """
        # Handle edge case: start and end are the same
        if start_region_name == end_region_name:
            return [start_region_name]

        # Verify both regions exist
        if start_region_name not in space or end_region_name not in space:
            return None

        # BFS data structures
        queue = deque([(start_region_name, [start_region_name])])
        visited = {start_region_name}

        while queue:
            current_name, path = queue.popleft()

            # Find parent of current region
            parent_name = space.get_parent(current_name)

            if parent_name is None:
                # No parent, can't continue up this branch
                continue

            # Check if we've reached the target
            if parent_name == end_region_name:
                return path + [parent_name]

            # Check if we've already visited this parent
            if parent_name not in visited:
                visited.add(parent_name)
                queue.append((parent_name, path + [parent_name]))

        # No path found
        return None
