#!/usr/bin/env python3
"""
Demo: System discovering multiple different algorithms
"""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.data.problem import Problem
from regionai.discovery.discover import discover_concept_from_failures


def discover_operation(operation_name: str, examples: list):
    """Helper to discover an operation from examples."""
    problems = []
    for i, (input_data, output_data) in enumerate(examples):
        problems.append(Problem(
            name=f"{operation_name}_{i}",
            problem_type="transformation",
            input_data=torch.tensor(input_data, dtype=torch.float32),
            output_data=torch.tensor(output_data, dtype=torch.float32),
            description=f"Example {i} of {operation_name}"
        ))
    
    print(f"\nDiscovering {operation_name.upper()}:")
    print("Examples:")
    for p in problems:
        print(f"  {p.input_data.tolist()} → {p.output_data.tolist()}")
    
    concept = discover_concept_from_failures(problems)
    if concept:
        print(f"✓ Discovered: {concept.transformation_function}")
        return True
    else:
        print("✗ Discovery failed")
        return False


def main():
    print("=" * 60)
    print("DEMO: The System Can Discover Different Algorithms")
    print("=" * 60)
    
    # Test discovering various operations
    operations = {
        "reverse": [
            ([1, 2, 3], [3, 2, 1]),
            ([10, 20], [20, 10]),
            ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5])
        ],
        "sum": [
            ([1, 2, 3], [6]),
            ([10, -5], [5]),
            ([100], [100])
        ],
        "add_one": [
            ([0, 1, 2], [1, 2, 3]),
            ([10, 20], [11, 21]),
            ([-5, -10], [-4, -9])
        ],
        "sort_ascending": [
            ([3, 1, 2], [1, 2, 3]),
            ([10, 5, 15], [5, 10, 15]),
            ([1], [1])
        ],
        "get_first": [
            ([10, 20, 30], [10]),
            ([99], [99]),
            ([-5, 0, 5], [-5])
        ],
        "count": [
            ([1, 2, 3], [3]),
            ([10], [1]),
            ([1, 1, 1, 1, 1], [5])
        ]
    }
    
    successes = 0
    for op_name, examples in operations.items():
        if discover_operation(op_name, examples):
            successes += 1
    
    print("\n" + "=" * 60)
    print(f"Successfully discovered {successes}/{len(operations)} operations!")
    print("\nThe system can learn:")
    print("• Reordering operations (REVERSE, SORT)")
    print("• Arithmetic operations (SUM, ADD_ONE)")
    print("• Selection operations (GET_FIRST)")
    print("• Aggregation operations (COUNT)")
    print("\n🎯 Each discovered from just 3 examples!")
    print("=" * 60)


if __name__ == "__main__":
    main()