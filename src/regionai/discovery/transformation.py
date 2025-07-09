#!/usr/bin/env python3
"""
Defines the data structures for representing algorithmic transformations
as sequences of primitive operations.
"""

from dataclasses import dataclass
from typing import List, Callable, Optional
import torch

@dataclass(frozen=True)
class Transformation:
    """
    Represents a single, primitive, named operation on a tensor.
    This is a single "instruction" in our transformation language.
    """
    name: str
    operation: Callable[[torch.Tensor], torch.Tensor]
    
    def __repr__(self) -> str:
        return self.name

class TransformationSequence:
    """
    Represents a sequence of Transformation objects that form a complete algorithm.
    """
    def __init__(self, transformations: List[Transformation]):
        """
        Initializes the sequence with a list of transformations.
        
        Args:
            transformations: The list of Transformation objects to apply in order.
        """
        self.transformations = transformations
    
    def apply(self, x: torch.Tensor) -> torch.Tensor:
        """
        Applies the full sequence of transformations to an input tensor.
        
        Args:
            x: The input tensor.
            
        Returns:
            The output tensor after all transformations have been applied.
        """
        current_value = x
        for trans in self.transformations:
            current_value = trans.operation(current_value)
        return current_value
    
    def __repr__(self) -> str:
        """
        Provides a human-readable representation of the algorithm.
        Example: "[REVERSE -> ADD_ONE]"
        """
        if not self.transformations:
            return "[IDENTITY]"
        return f"[{' -> '.join(map(str, self.transformations))}]"
    
    def __len__(self) -> int:
        return len(self.transformations)


# --- Library of Primitive Operations ---
# This list serves as the "alphabet" of our algorithmic language.
# The discovery engine will search for combinations of these primitives.

PRIMITIVE_OPERATIONS: List[Transformation] = [
    # --- Reordering Operations ---
    Transformation(
        name="REVERSE",
        # Flips the tensor along its first dimension.
        operation=lambda x: torch.flip(x, dims=[0])
    ),
    Transformation(
        name="SORT_ASCENDING", 
        # Sorts the tensor elements in ascending order.
        operation=lambda x: torch.sort(x, stable=True).values
    ),
    # SORT_DESCENDING removed to force compositional discovery
    # Transformation(
    #     name="SORT_DESCENDING",
    #     # Sorts the tensor elements in descending order.
    #     operation=lambda x: torch.sort(x, stable=True, descending=True).values
    # ),
    
    # --- Element-wise Arithmetic Operations ---
    Transformation(
        name="ADD_ONE",
        # Adds 1 to each element of the tensor.
        operation=lambda x: x + 1
    ),
    Transformation(
        name="SUBTRACT_ONE",
        # Subtracts 1 from each element of the tensor.
        operation=lambda x: x - 1
    ),
    
    # --- Selection Operations ---
    Transformation(
        name="GET_FIRST",
        # Selects the first element of the tensor.
        operation=lambda x: x[0].unsqueeze(0) if x.numel() > 0 else torch.empty(0)
    ),
    Transformation(
        name="GET_LAST",
        # Selects the last element of the tensor.
        operation=lambda x: x[-1].unsqueeze(0) if x.numel() > 0 else torch.empty(0)
    ),
    
    # --- Aggregation Operations ---
    Transformation(
        name="SUM",
        # Computes the sum of all elements and returns it as a single-element tensor.
        operation=lambda x: torch.sum(x).unsqueeze(0)
    ),
    Transformation(
        name="COUNT",
        # Counts the number of elements and returns it as a single-element tensor.
        operation=lambda x: torch.tensor([x.numel()], dtype=x.dtype, device=x.device)
    ),
    
    # --- Filtering Operations ---
    Transformation(
        name="FILTER_GT_5",
        # Selects all elements in the tensor greater than 5.
        operation=lambda x: x[x > 5] if (x > 5).any() else torch.tensor([], dtype=x.dtype, device=x.device)
    ),
]