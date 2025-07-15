"""
Base strategy class for discovery strategies.
"""
from typing import List, Optional
from abc import ABC, abstractmethod
import torch

from ...data.problem import Problem
from ...core.region import RegionND
from ...core.transformation import TransformationSequence


class DiscoveryStrategy(ABC):
    """Abstract base class for discovery strategies."""
    
    @abstractmethod
    def discover(self, problems: List[Problem]) -> Optional[RegionND]:
        """
        Discover a new concept/transformation from failed problems.
        
        Args:
            problems: List of problems that failed with existing transformations
            
        Returns:
            A new RegionND representing the discovered concept, or None
        """
    
    def _create_concept_region(self, 
                             transformation: TransformationSequence,
                             concept_name: str,
                             dims: int) -> RegionND:
        """Helper to create a region for a discovered concept."""
        min_corner = torch.rand(dims) * 0.1
        max_corner = min_corner + 0.1
        
        region = RegionND(
            min_corner=min_corner,
            max_corner=max_corner,
            region_type='transformation',
            transformation_function=transformation
        )
        region.name = concept_name
        return region