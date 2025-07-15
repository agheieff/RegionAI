#!/usr/bin/env python3
"""
Tensor-based primitive operations for RegionAI.

This module contains primitive transformations that operate on PyTorch tensors,
including reordering, arithmetic, selection, aggregation, and filtering operations.
"""

import torch
from typing import List
from .transformation import Transformation


# --- Tensor Reordering Operations ---
TENSOR_REORDERING_PRIMITIVES: List[Transformation] = [
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
]

# --- Element-wise Arithmetic Operations ---
TENSOR_ARITHMETIC_PRIMITIVES: List[Transformation] = [
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
    Transformation(
        name="ADD_TENSOR",
        # This operation takes the main input `x` and a list of args
        operation=lambda x, args: x + args[0],
        input_type="vector",
        output_type="vector",
        num_args=1  # This primitive requires one argument
    ),
    Transformation(
        name="MULTIPLY",
        # Multiplies a tensor by a scalar
        operation=lambda x, args: x * args[0],
        input_type="vector",
        output_type="vector",
        num_args=1  # Requires the multiplier
    ),
]

# --- Selection Operations ---
TENSOR_SELECTION_PRIMITIVES: List[Transformation] = [
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
]

# --- Aggregation Operations ---
TENSOR_AGGREGATION_PRIMITIVES: List[Transformation] = [
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
]

# --- Filtering Operations ---
TENSOR_FILTERING_PRIMITIVES: List[Transformation] = [
    Transformation(
        name="FILTER_GT_5",
        # Selects all elements in the tensor greater than 5.
        operation=lambda x: x[x > 5] if (x > 5).any() else torch.tensor([], dtype=x.dtype, device=x.device),
        input_type="vector",
        output_type="vector"
    ),
]

# Combine all tensor primitives
TENSOR_PRIMITIVES: List[Transformation] = (
    TENSOR_REORDERING_PRIMITIVES +
    TENSOR_ARITHMETIC_PRIMITIVES +
    TENSOR_SELECTION_PRIMITIVES +
    TENSOR_AGGREGATION_PRIMITIVES +
    TENSOR_FILTERING_PRIMITIVES
)