#!/usr/bin/env python3
"""
Structured data primitive operations for RegionAI.

This module contains primitive transformations that operate on dictionaries
and lists of dictionaries, enabling manipulation of structured data.
"""

import torch
from typing import List
from .transformation import Transformation


# --- List of Dictionaries Operations ---
DICT_LIST_PRIMITIVES: List[Transformation] = [
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
    Transformation(
        name="UPDATE_FIELD",
        # Updates a field in each dictionary in a list
        operation=lambda data, args: [{**item, args[0]: args[1] if not callable(args[1]) else args[1](item.get(args[0], 0))} for item in data],
        input_type="dict_list",
        output_type="dict_list",
        num_args=2  # Requires field name and new value or update function
    ),
]

# --- Single Dictionary Operations ---
SINGLE_DICT_PRIMITIVES: List[Transformation] = [
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
]

# --- Boolean Primitives for Structured Data ---
STRUCTURED_BOOLEAN_PRIMITIVES: List[Transformation] = [
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
]

# --- Scalar Operations (for fields extracted from dicts) ---
SCALAR_PRIMITIVES: List[Transformation] = [
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

# Combine all structured data primitives
STRUCTURED_DATA_PRIMITIVES: List[Transformation] = (
    DICT_LIST_PRIMITIVES +
    SINGLE_DICT_PRIMITIVES +
    STRUCTURED_BOOLEAN_PRIMITIVES +
    SCALAR_PRIMITIVES
)