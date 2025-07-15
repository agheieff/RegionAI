"""RegionND implementation for N-dimensional concept regions."""

from typing import Sequence, Union, TYPE_CHECKING, Optional
import torch

if TYPE_CHECKING:
    from .transformation import TransformationSequence


class RegionND:
    """An N-dimensional axis-aligned bounding box representing a concept region."""

    def __init__(
        self,
        min_corner: Union[torch.Tensor, Sequence[float]],
        max_corner: Union[torch.Tensor, Sequence[float]],
        device: str = None,
        region_type: str = "spatial",
        transformation_function: Optional['TransformationSequence'] = None,
    ):
        """Initialize an N-dimensional region with min and max corners.

        Args:
            min_corner: Minimum corner coordinates as tensor or sequence
            max_corner: Maximum corner coordinates as tensor or sequence
            device: Torch device (defaults to 'cpu')
            region_type: The type of region ('spatial' or 'transformation').
            transformation_function: A TransformationSequence for transformation regions.
        """
        self.device = device or "cpu"
        self.region_type = region_type
        self.transformation_function = transformation_function

        # Convert to tensors if needed
        if not isinstance(min_corner, torch.Tensor):
            min_corner = torch.tensor(min_corner, dtype=torch.float32, device=self.device)
        else:
            min_corner = min_corner.to(dtype=torch.float32, device=self.device)
            
        if not isinstance(max_corner, torch.Tensor):
            max_corner = torch.tensor(max_corner, dtype=torch.float32, device=self.device)
        else:
            max_corner = max_corner.to(dtype=torch.float32, device=self.device)

        # Ensure 1D tensors
        if min_corner.ndim != 1 or max_corner.ndim != 1:
            raise ValueError("Corners must be 1D tensors")
            
        # Validate same dimensionality
        if min_corner.shape != max_corner.shape:
            raise ValueError(
                f"Corner dimensions must match: {min_corner.shape} != {max_corner.shape}"
            )

        self.min_corner = min_corner
        self.max_corner = max_corner
        self.dims = min_corner.shape[0]

        # Validate box
        if torch.any(self.min_corner > self.max_corner):
            raise ValueError(
                f"Invalid region: min corner {self.min_corner} > max corner {self.max_corner}"
            )

    @classmethod
    def from_corners(
        cls,
        min_corner: Sequence[float],
        max_corner: Sequence[float],
        device: str = None,
    ):
        """Create a RegionND from corner sequences."""
        return cls(min_corner, max_corner, device)

    @classmethod
    def from_center_size(
        cls, center: Sequence[float], size: Sequence[float], device: str = None
    ):
        """Create a RegionND from center point and size."""
        center_t = torch.tensor(center, dtype=torch.float32)
        size_t = torch.tensor(size, dtype=torch.float32)
        half_size = size_t / 2
        min_corner = center_t - half_size
        max_corner = center_t + half_size
        return cls(min_corner, max_corner, device)

    def contains(self, other: "RegionND") -> bool:
        """Check if this region contains another region.

        Args:
            other: Another region (must be RegionND)

        Returns:
            True if this region fully contains the other
        """
        if not isinstance(other, RegionND):
            return NotImplemented
            
        if self.dims != other.dims:
            raise ValueError(f"Cannot compare regions of different dimensions: {self.dims} vs {other.dims}")

        # A contains B if A.min <= B.min AND B.max <= A.max
        return torch.all(self.min_corner <= other.min_corner) and torch.all(other.max_corner <= self.max_corner)

    def overlaps(self, other: "RegionND") -> bool:
        """Check if this region overlaps with another region.

        Args:
            other: Another region (must be RegionND)

        Returns:
            True if the regions overlap
        """
        if not isinstance(other, RegionND):
            return NotImplemented
            
        if self.dims != other.dims:
            raise ValueError(f"Cannot compare regions of different dimensions: {self.dims} vs {other.dims}")

        # Regions overlap if they are not separated along any axis
        # Using strict inequalities - regions only overlap if they share interior points
        separated = torch.any(self.max_corner <= other.min_corner) or torch.any(
            other.max_corner <= self.min_corner
        )
        return not separated

    def volume(self) -> float:
        """Calculate the volume of this N-dimensional region.

        Returns:
            The volume (product of all dimension sizes)
        """
        dimensions = self.max_corner - self.min_corner
        return torch.prod(dimensions).item()

    def center(self) -> torch.Tensor:
        """Get the center point of the box."""
        return (self.min_corner + self.max_corner) / 2

    def size(self) -> torch.Tensor:
        """Get the size (width, height) of the box."""
        return self.max_corner - self.min_corner

    def intersection(self, other: "RegionND") -> "RegionND":
        """Calculate the intersection of two regions.

        Args:
            other: Another RegionND

        Returns:
            A new RegionND representing the intersection, or None if no intersection
        """
        if not self.overlaps(other):
            return None

        # Intersection is the region with max of mins and min of maxes
        new_min = torch.maximum(self.min_corner, other.min_corner)
        new_max = torch.minimum(self.max_corner, other.max_corner)

        return RegionND(new_min, new_max, self.device)

    def union(self, other: "RegionND") -> "RegionND":
        """Calculate the bounding region containing both regions.

        Args:
            other: Another RegionND

        Returns:
            A new RegionND containing both regions
        """
        if self.dims != other.dims:
            raise ValueError(f"Cannot union regions of different dimensions: {self.dims} vs {other.dims}")
            
        # Union is the region with min of mins and max of maxes
        new_min = torch.minimum(self.min_corner, other.min_corner)
        new_max = torch.maximum(self.max_corner, other.max_corner)

        return RegionND(new_min, new_max, self.device)

    def expand(self, factor: float) -> "RegionND":
        """Expand the region by a factor from its center.

        Args:
            factor: Expansion factor (1.0 = no change, 2.0 = double size)

        Returns:
            A new expanded RegionND
        """
        center = self.center()
        new_size = self.size() * factor
        half_size = new_size / 2

        new_min = center - half_size
        new_max = center + half_size
        
        return RegionND(new_min, new_max, self.device)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"RegionND(dims={self.dims}, "
            f"min={self.min_corner.tolist()}, "
            f"max={self.max_corner.tolist()}, "
            f"volume={self.volume():.2f}, "
            f"type={self.region_type})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        center = self.center().tolist()
        size = self.size().tolist()
        
        # Format center and size with appropriate precision
        center_str = ", ".join(f"{c:.2f}" for c in center)
        size_str = ", ".join(f"{s:.2f}" for s in size)
        
        return (
            f"RegionND(dims={self.dims}, "
            f"center=[{center_str}], "
            f"size=[{size_str}])"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality with another RegionND."""
        if not isinstance(other, RegionND):
            return NotImplemented
        return (
            self.dims == other.dims and
            torch.allclose(self.min_corner, other.min_corner) and 
            torch.allclose(self.max_corner, other.max_corner)
        )


# Backward compatibility alias
class Box2D(RegionND):
    """Backward compatibility wrapper for 2D regions."""
    
    def __init__(self, x_min: float, y_min: float, x_max: float, y_max: float, device: str = None):
        """Initialize a 2D box with individual coordinates for backward compatibility."""
        super().__init__([x_min, y_min], [x_max, y_max], device)
