#!/usr/bin/env python3
"""
Defines the data structures for representing algorithmic transformations
as sequences of primitive operations.
"""

from dataclasses import dataclass
from typing import List, Callable, Optional, Dict, Any, Union
import torch
import ast


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


@dataclass(frozen=True)
class ConditionalTransformation:
    """
    A special transformation that executes different sequences based on a condition.
    This enables if/else logic in discovered algorithms.
    """
    name: str
    condition: AppliedTransformation  # A boolean-producing transformation
    if_true_sequence: 'TransformationSequence'
    if_false_sequence: 'TransformationSequence'
    input_type: str = "dict_list"
    output_type: str = "dict_list"
    
    def apply(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply conditional logic to each item in the data."""
        results = []
        for item in data:
            # Evaluate condition for this item
            condition_result = self.condition.transformation.operation(item, self.condition.arguments)
            
            if condition_result:
                # Apply true branch - need to handle single item
                result = self.if_true_sequence.apply([item])
                results.extend(result if isinstance(result, list) else [result])
            else:
                # Apply false branch
                result = self.if_false_sequence.apply([item])
                results.extend(result if isinstance(result, list) else [result])
        
        return results
    
    def __repr__(self) -> str:
        return f"IF({self.condition}) THEN {self.if_true_sequence} ELSE {self.if_false_sequence}"


@dataclass(frozen=True)
class ForEachTransformation:
    """
    A higher-order transformation that applies a sequence to each item in a list.
    This enables iteration over collections with complex per-item processing.
    """
    name: str
    loop_body: 'TransformationSequence'  # Sequence to apply to each item
    input_type: str = "dict_list"
    output_type: str = "dict_list"
    
    def apply(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply the loop body to each item in the data."""
        results = []
        for item in data:
            # The loop body operates on a single item
            # We need to ensure it returns a single modified item
            transformed = self.loop_body.apply(item)
            if isinstance(transformed, dict):
                results.append(transformed)
            elif isinstance(transformed, list) and len(transformed) == 1:
                results.append(transformed[0])
            else:
                # Handle unexpected output
                results.append(item)  # Fallback to original
        
        return results
    
    def __repr__(self) -> str:
        return f"FOR_EACH(item) DO {self.loop_body}"

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
    
    def apply(self, x: Union[torch.Tensor, List[Dict[str, Any]], Dict[str, Any], int, float]) -> Union[torch.Tensor, List[Dict[str, Any]], Dict[str, Any], int, float]:
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
        operation=lambda x: torch.sum(x).unsqueeze(0) if x.numel() > 0 else torch.tensor([0.0], dtype=x.dtype),
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
    
    # --- Structured Data Operations ---
    Transformation(
        name="MAP_GET",
        # Extracts values for a given key from a list of dictionaries
        operation=lambda data, args: torch.tensor([float(item[args[0]]) for item in data if args[0] in item], dtype=torch.float32),
        input_type="dict_list",
        output_type="vector",
        num_args=1  # Requires the key to extract
    ),
    Transformation(
        name="FILTER_BY_VALUE",
        # Filters a list of dictionaries based on a key-value match
        operation=lambda data, args: [item for item in data if args[0] in item and item[args[0]] == args[1]],
        input_type="dict_list",
        output_type="dict_list",
        num_args=2  # Requires key and value to filter by
    ),
    
    # --- Boolean Primitives ---
    Transformation(
        name="HAS_KEY",
        # Checks if a dictionary contains a specific key
        operation=lambda item, args: args[0] in item if isinstance(item, dict) else False,
        input_type="dict",
        output_type="boolean",
        num_args=1  # Requires the key to check
    ),
    Transformation(
        name="VALUE_EQUALS",
        # Checks if a dictionary's value for a key equals a given value
        operation=lambda item, args: args[0] in item and item[args[0]] == args[1] if isinstance(item, dict) else False,
        input_type="dict",
        output_type="boolean",
        num_args=2  # Requires key and value to check
    ),
    
    # --- Arithmetic Operations ---
    Transformation(
        name="MULTIPLY",
        # Multiplies a tensor by a scalar
        operation=lambda x, args: x * args[0],
        input_type="vector",
        output_type="vector",
        num_args=1  # Requires the multiplier
    ),
    Transformation(
        name="UPDATE_FIELD",
        # Updates a field in each dictionary in a list
        operation=lambda data, args: [{**item, args[0]: args[1] if not callable(args[1]) else args[1](item.get(args[0], 0))} for item in data],
        input_type="dict_list",
        output_type="dict_list",
        num_args=2  # Requires field name and new value or update function
    ),
    
    # --- Single Item Operations ---
    Transformation(
        name="GET_FIELD",
        # Extracts a value from a single dictionary
        operation=lambda item, args: item.get(args[0]) if isinstance(item, dict) else None,
        input_type="dict",
        output_type="scalar",
        num_args=1  # Requires the field name
    ),
    Transformation(
        name="SET_FIELD",
        # Sets a value in a dictionary and returns the modified dictionary
        operation=lambda item, args: {**item, args[0]: args[1]} if isinstance(item, dict) else item,
        input_type="dict",
        output_type="dict",
        num_args=2  # Requires field name and value
    ),
    Transformation(
        name="MULTIPLY_SCALAR",
        # Multiplies a scalar by another scalar
        operation=lambda x, args: x * args[0] if isinstance(x, (int, float)) else x,
        input_type="scalar",
        output_type="scalar",
        num_args=1  # Requires the multiplier
    ),
    Transformation(
        name="ADD_SCALAR",
        # Adds a scalar to another scalar
        operation=lambda x, args: x + args[0] if isinstance(x, (int, float)) else x,
        input_type="scalar",
        output_type="scalar",
        num_args=1  # Requires the value to add
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