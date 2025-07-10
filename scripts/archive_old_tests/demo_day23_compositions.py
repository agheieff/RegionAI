#!/usr/bin/env python3
"""
Demo: Discovering various compositional algorithms
"""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.data.problem import Problem
from regionai.discovery.discover import discover_concept_from_failures


def discover_composition(name: str, examples: list):
    """Helper to discover a compositional algorithm."""
    problems = []
    for i, (input_data, output_data, desc) in enumerate(examples):
        problems.append(Problem(
            name=f"{name}_{i}",
            problem_type="transformation",
            input_data=torch.tensor(input_data, dtype=torch.float32),
            output_data=torch.tensor(output_data, dtype=torch.float32),
            description=desc
        ))
    
    print(f"\nDiscovering {name}:")
    print("Examples:")
    for p in problems:
        print(f"  • {p.description}")
    
    concept = discover_concept_from_failures(problems)
    if concept:
        seq = concept.transformation_function
        print(f"✓ Discovered: {seq}")
        return True, seq
    else:
        print("✗ Discovery failed")
        return False, None


def main():
    print("=" * 60)
    print("DEMO: Compositional Algorithm Discovery")
    print("=" * 60)
    print("\nThe system can discover algorithms that require")
    print("combining multiple primitive operations.")
    
    # Test 1: Find Maximum (SORT_ASCENDING → GET_LAST)
    print("\n" + "-" * 60)
    success, seq = discover_composition("FIND_MAX", [
        ([3, 1, 4, 1, 5], [5], "Find max of [3,1,4,1,5] → 5"),
        ([10, 20, 15], [20], "Find max of [10,20,15] → 20"),
        ([-5, -2, -10], [-2], "Find max of [-5,-2,-10] → -2"),
    ])
    
    # Test 2: Find Minimum (SORT_ASCENDING → GET_FIRST)
    print("\n" + "-" * 60)
    success, seq = discover_composition("FIND_MIN", [
        ([3, 1, 4, 1, 5], [1], "Find min of [3,1,4,1,5] → 1"),
        ([10, 20, 15], [10], "Find min of [10,20,15] → 10"),
        ([-5, -2, -10], [-10], "Find min of [-5,-2,-10] → -10"),
    ])
    
    # Test 3: Count Plus One (COUNT → ADD_ONE)
    print("\n" + "-" * 60)
    success, seq = discover_composition("COUNT_PLUS_ONE", [
        ([1, 2, 3], [4], "Count [1,2,3] + 1 → 4"),
        ([10, 20], [3], "Count [10,20] + 1 → 3"),
        ([5], [2], "Count [5] + 1 → 2"),
    ])
    
    # Test 4: Something requiring SORT_DESC (which we removed!)
    print("\n" + "-" * 60)
    success, seq = discover_composition("SECOND_LARGEST", [
        ([3, 1, 4, 1, 5], [4], "Second largest of [3,1,4,1,5] → 4"),
        ([10, 30, 20], [20], "Second largest of [10,30,20] → 20"),
        ([1, 2], [1], "Second largest of [1,2] → 1"),
    ])
    
    print("\n" + "=" * 60)
    print("Key Insights:")
    print("• The system discovers multi-step solutions when needed")
    print("• BFS ensures it finds the shortest algorithm")
    print("• Complex behaviors emerge from simple primitives")
    print("• This is true creative problem-solving!")
    print("=" * 60)


if __name__ == "__main__":
    main()