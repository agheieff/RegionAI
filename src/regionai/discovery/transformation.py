#!/usr/bin/env python3
"""
Defines the data structures for representing algorithmic transformations
as sequences of primitive operations.
"""

from dataclasses import dataclass
from typing import List, Callable, Optional, Dict
import torch


@dataclass(frozen=True)
class AppliedTransformation:
    """
    Represents a Transformation with its concrete arguments.
    This binds a transformation to specific tensor arguments.
    """
    transformation: 'Transformation'
    arguments: List[torch.Tensor]
    
    def __repr__(self) -> str:
        if self.arguments:
            return f"{self.transformation.name}(args={len(self.arguments)})"
        return str(self.transformation)


@dataclass(frozen=True)
class Transformation:
    """
    Represents a single, primitive, named operation on a tensor.
    This is a single "instruction" in our transformation language.
    """
    name: str
    operation: Callable[..., torch.Tensor]  # Now accepts variable arguments
    input_type: str = "vector"  # Either "vector" or "scalar"
    output_type: str = "vector"  # Either "vector" or "scalar"
    num_args: int = 0  # Number of additional tensor arguments required
    
    def __repr__(self) -> str:
        return self.name

class TransformationSequence:
    """
    Represents a sequence of AppliedTransformation objects that form a complete algorithm.
    Now handles transformations with their arguments.
    """
    def __init__(self, applied_transformations: List[AppliedTransformation]):
        """
        Initializes the sequence with a list of applied transformations.
        
        Args:
            applied_transformations: The list of AppliedTransformation objects to apply in order.
        """
        self.applied_transformations = applied_transformations
        # Keep backward compatibility
        self.transformations = [at.transformation for at in applied_transformations]
    
    def apply(self, x: torch.Tensor) -> torch.Tensor:
        """
        Applies the full sequence of transformations to an input tensor.
        
        Args:
            x: The input tensor.
            
        Returns:
            The output tensor after all transformations have been applied.
        """
        current_value = x
        for applied_trans in self.applied_transformations:
            trans = applied_trans.transformation
            args = applied_trans.arguments
            
            if trans.num_args == 0:
                current_value = trans.operation(current_value)
            else:
                # Handle special marker for "use input as argument"
                processed_args = []
                for arg in args:
                    if isinstance(arg, torch.Tensor) and arg.numel() == 1 and arg.item() == -999.0:
                        # Use the current input as the argument
                        processed_args.append(x)
                    else:
                        processed_args.append(arg)
                current_value = trans.operation(current_value, processed_args)
        return current_value
    
    def __repr__(self) -> str:
        """
        Provides a human-readable representation of the algorithm.
        Example: "[REVERSE -> ADD_TENSOR(args=1)]"
        """
        if not self.applied_transformations:
            return "[IDENTITY]"
        return f"[{' -> '.join(map(str, self.applied_transformations))}]"
    
    def __len__(self) -> int:
        return len(self.applied_transformations)
    
    @classmethod
    def from_transformations(cls, transformations: List[Transformation]) -> 'TransformationSequence':
        """Create a TransformationSequence from a list of Transformations (no args)."""
        applied = [AppliedTransformation(t, []) for t in transformations]
        return cls(applied)


# --- Library of Primitive Operations ---
# This list serves as the "alphabet" of our algorithmic language.
# The discovery engine will search for combinations of these primitives.

PRIMITIVE_OPERATIONS: List[Transformation] = [
    # --- Reordering Operations ---
    Transformation(
        name="REVERSE",
        # Flips the tensor along its first dimension.
        operation=lambda x: torch.flip(x, dims=[0]),
        input_type="vector",
        output_type="vector"
    ),
    Transformation(
        name="SORT_ASCENDING", 
        # Sorts the tensor elements in ascending order.
        operation=lambda x: torch.sort(x, stable=True).values,
        input_type="vector",
        output_type="vector"
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
        operation=lambda x: x + 1,
        input_type="vector",
        output_type="vector"
    ),
    Transformation(
        name="SUBTRACT_ONE",
        # Subtracts 1 from each element of the tensor.
        operation=lambda x: x - 1,
        input_type="vector",
        output_type="vector"
    ),
    
    # --- Selection Operations ---
    Transformation(
        name="GET_FIRST",
        # Selects the first element of the tensor.
        operation=lambda x: x[0].unsqueeze(0) if x.numel() > 0 else torch.empty(0),
        input_type="vector",
        output_type="scalar"
    ),
    Transformation(
        name="GET_LAST",
        # Selects the last element of the tensor.
        operation=lambda x: x[-1].unsqueeze(0) if x.numel() > 0 else torch.empty(0),
        input_type="vector",
        output_type="scalar"
    ),
    
    # --- Aggregation Operations ---
    Transformation(
        name="SUM",
        # Computes the sum of all elements and returns it as a single-element tensor.
        operation=lambda x: torch.sum(x).unsqueeze(0),
        input_type="vector",
        output_type="scalar"
    ),
    Transformation(
        name="COUNT",
        # Counts the number of elements and returns it as a single-element tensor.
        operation=lambda x: torch.tensor([x.numel()], dtype=x.dtype, device=x.device),
        input_type="vector",
        output_type="scalar"
    ),
    
    # --- Filtering Operations ---
    Transformation(
        name="FILTER_GT_5",
        # Selects all elements in the tensor greater than 5.
        operation=lambda x: x[x > 5] if (x > 5).any() else torch.tensor([], dtype=x.dtype, device=x.device),
        input_type="vector",
        output_type="vector"
    ),
    
    # --- Parameterized Operations ---
    Transformation(
        name="ADD_TENSOR",
        # This operation takes the main input `x` and a list of args
        operation=lambda x, args: x + args[0],
        input_type="vector",
        output_type="vector",
        num_args=1  # This primitive requires one argument
    ),
]


# --- Heuristic Metadata ---
# This metadata will guide the search engine to be more intelligent.

# Defines pairs of operations that cancel each other out.
# The key is the name of an operation, the value is the name of its inverse.
INVERSE_OPERATIONS: Dict[str, str] = {
    "REVERSE": "REVERSE",
    "ADD_ONE": "SUBTRACT_ONE", 
    "SUBTRACT_ONE": "ADD_ONE",
}