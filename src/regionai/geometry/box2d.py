"""Box2D implementation for 2D concept regions."""

from typing import Tuple
import torch
from ..core.interfaces import Region
from ..config.settings import Config


class Box2D:
    """A 2D axis-aligned bounding box representing a concept region."""
    
    def __init__(
        self, 
        x_min: float, 
        y_min: float, 
        x_max: float, 
        y_max: float,
        device: str = None
    ):
        """Initialize a 2D box with min and max corners.
        
        Args:
            x_min: Minimum x coordinate
            y_min: Minimum y coordinate
            x_max: Maximum x coordinate
            y_max: Maximum y coordinate
            device: Torch device (defaults to config)
        """
        if device is None:
            device = Config().device
            
        self.device = device
        
        # Store as torch tensors for GPU support
        self.min_corner = torch.tensor([x_min, y_min], dtype=torch.float32, device=device)
        self.max_corner = torch.tensor([x_max, y_max], dtype=torch.float32, device=device)
        
        # Validate box
        if torch.any(self.min_corner > self.max_corner):
            raise ValueError(f"Invalid box: min corner {self.min_corner} > max corner {self.max_corner}")
    
    @classmethod
    def from_corners(cls, min_corner: Tuple[float, float], max_corner: Tuple[float, float], device: str = None):
        """Create a Box2D from corner tuples."""
        return cls(min_corner[0], min_corner[1], max_corner[0], max_corner[1], device)
    
    @classmethod
    def from_center_size(cls, center: Tuple[float, float], size: Tuple[float, float], device: str = None):
        """Create a Box2D from center point and size."""
        half_size = (size[0] / 2, size[1] / 2)
        return cls(
            center[0] - half_size[0],
            center[1] - half_size[1],
            center[0] + half_size[0],
            center[1] + half_size[1],
            device
        )
    
    def contains(self, other: 'Region') -> bool:
        """Check if this box contains another region.
        
        Args:
            other: Another region (must be Box2D)
            
        Returns:
            True if this box fully contains the other
        """
        if not isinstance(other, Box2D):
            return NotImplemented
            
        # A contains B if A.min <= B.min AND B.max <= A.max
        return (torch.all(self.min_corner <= other.min_corner) and 
                torch.all(other.max_corner <= self.max_corner)).item()
    
    def overlaps(self, other: 'Region') -> bool:
        """Check if this box overlaps with another region.
        
        Args:
            other: Another region (must be Box2D)
            
        Returns:
            True if the boxes overlap
        """
        if not isinstance(other, Box2D):
            return NotImplemented
            
        # Boxes overlap if they are not separated along any axis
        # Using strict inequalities - boxes only overlap if they share interior points
        separated = (torch.any(self.max_corner <= other.min_corner) or 
                    torch.any(other.max_corner <= self.min_corner))
        return not separated.item()
    
    def volume(self) -> float:
        """Calculate the area of this 2D box.
        
        Returns:
            The area (volume in 2D) of the box
        """
        dimensions = self.max_corner - self.min_corner
        return torch.prod(dimensions).item()
    
    def center(self) -> torch.Tensor:
        """Get the center point of the box."""
        return (self.min_corner + self.max_corner) / 2
    
    def size(self) -> torch.Tensor:
        """Get the size (width, height) of the box."""
        return self.max_corner - self.min_corner
    
    def intersection(self, other: 'Box2D') -> 'Box2D':
        """Calculate the intersection of two boxes.
        
        Args:
            other: Another Box2D
            
        Returns:
            A new Box2D representing the intersection, or None if no intersection
        """
        if not self.overlaps(other):
            return None
            
        # Intersection is the box with max of mins and min of maxes
        new_min = torch.maximum(self.min_corner, other.min_corner)
        new_max = torch.minimum(self.max_corner, other.max_corner)
        
        return Box2D(
            new_min[0].item(), new_min[1].item(),
            new_max[0].item(), new_max[1].item(),
            self.device
        )
    
    def union(self, other: 'Box2D') -> 'Box2D':
        """Calculate the bounding box containing both boxes.
        
        Args:
            other: Another Box2D
            
        Returns:
            A new Box2D containing both boxes
        """
        # Union is the box with min of mins and max of maxes
        new_min = torch.minimum(self.min_corner, other.min_corner)
        new_max = torch.maximum(self.max_corner, other.max_corner)
        
        return Box2D(
            new_min[0].item(), new_min[1].item(),
            new_max[0].item(), new_max[1].item(),
            self.device
        )
    
    def expand(self, factor: float) -> 'Box2D':
        """Expand the box by a factor from its center.
        
        Args:
            factor: Expansion factor (1.0 = no change, 2.0 = double size)
            
        Returns:
            A new expanded Box2D
        """
        center = self.center()
        new_size = self.size() * factor
        half_size = new_size / 2
        
        return Box2D(
            (center[0] - half_size[0]).item(),
            (center[1] - half_size[1]).item(),
            (center[0] + half_size[0]).item(),
            (center[1] + half_size[1]).item(),
            self.device
        )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Box2D(min={self.min_corner.tolist()}, "
                f"max={self.max_corner.tolist()}, "
                f"area={self.volume():.2f})")
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        center = self.center().tolist()
        size = self.size().tolist()
        return (f"Box2D(center=[{center[0]:.2f}, {center[1]:.2f}], "
                f"size=[{size[0]:.2f}, {size[1]:.2f}])")
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another Box2D."""
        if not isinstance(other, Box2D):
            return NotImplemented
        return (torch.allclose(self.min_corner, other.min_corner) and
                torch.allclose(self.max_corner, other.max_corner))