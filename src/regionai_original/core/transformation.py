#!/usr/bin/env python3
"""
Defines the data structures for representing algorithmic transformations
as sequences of primitive operations.
"""

from dataclasses import dataclass
from typing import List, Callable, Dict, Any, Union
import torch


class UseInputAsArgument:
    """Marker class to indicate that the input tensor should be used as an argument."""


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
                    if isinstance(arg, UseInputAsArgument):
                        # Use the original input tensor as the argument
                        # This is used for operations like doubling (x + x)
                        if isinstance(x, torch.Tensor):
                            processed_args.append(x)
                        else:
                            processed_args.append(current_value)
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

# Import domain-specific primitives
from .tensor_primitives import TENSOR_PRIMITIVES
from .structured_data_primitives import STRUCTURED_DATA_PRIMITIVES

# Combine all primitives into the main list
PRIMITIVE_OPERATIONS: List[Transformation] = TENSOR_PRIMITIVES + STRUCTURED_DATA_PRIMITIVES

# --- Separate primitive lists by category ---
# These are subsets of PRIMITIVE_OPERATIONS for specific use cases

# Re-export the imported structured data primitives for backward compatibility
# (already imported above)

# Basic arithmetic and tensor operations
ARITHMETIC_PRIMITIVES: List[Transformation] = [
    t for t in PRIMITIVE_OPERATIONS
    if t.name in ['ADD_ONE', 'SUBTRACT_ONE', 'ADD_TENSOR', 'MULTIPLY', 'SUM', 'COUNT']
]

# Control flow primitives (for composition with conditionals)
CONTROL_PRIMITIVES: List[Transformation] = [
    t for t in PRIMITIVE_OPERATIONS
    if t.output_type == 'boolean' or t.name in ['HAS_KEY', 'VALUE_EQUALS']
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