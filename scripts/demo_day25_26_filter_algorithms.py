#!/usr/bin/env python3
"""
Demo: Discovering Complex Algorithms with Filtering
Shows how the FILTER primitive enables sophisticated data processing.
"""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.data.problem import Problem
from regionai.discovery.discover import discover_concept_from_failures
from regionai.spaces.concept_space import ConceptSpaceND
from regionai.engine.main import ReasoningEngine


def discover_and_test(name: str, examples: list, test_cases: list):
    """Discover an algorithm and test it on new cases."""
    print(f"\n{'='*60}")
    print(f"Discovering: {name}")
    print('='*60)
    
    # Create training problems
    problems = []
    for i, (input_data, output_data, desc) in enumerate(examples):
        problems.append(Problem(
            name=f"{name}_{i}",
            problem_type="transformation",
            input_data=torch.tensor(input_data, dtype=torch.float32),
            output_data=torch.tensor(output_data, dtype=torch.float32),
            description=desc
        ))
    
    print("\nTraining examples:")
    for p in problems:
        print(f"  • {p.description}")
    
    # Discover algorithm
    concept = discover_concept_from_failures(problems)
    if not concept:
        print("✗ Discovery failed!")
        return False
    
    print(f"\n✓ Discovered: {concept.transformation_function}")
    
    # Test on new cases
    print("\nTesting on new inputs:")
    space = ConceptSpaceND()
    space.add_region(concept.name, concept)
    engine = ReasoningEngine(space)
    
    for input_data, expected, desc in test_cases:
        test_problem = Problem(
            name="test",
            problem_type="transformation",
            input_data=torch.tensor(input_data, dtype=torch.float32),
            output_data=torch.tensor(expected, dtype=torch.float32),
            description=desc
        )
        
        solution = engine.solve_problem(test_problem)
        if solution:
            print(f"  ✓ {desc}")
        else:
            result = concept.transformation_function.apply(test_problem.input_data)
            print(f"  ✗ {desc} (got {result})")
    
    return True


def main():
    print("=" * 70)
    print("COMPLEX ALGORITHM DISCOVERY WITH FILTERING")
    print("=" * 70)
    print("\nThe FILTER_GT_5 primitive enables discovering algorithms that")
    print("selectively process data based on value, not just position.")
    
    # 1. Sum of large elements (FILTER_GT_5 → SUM)
    discover_and_test(
        "SUM_OF_LARGE",
        [
            ([3, 8, 2, 10], [18], "Sum elements >5 in [3,8,2,10] → 18"),
            ([1, 2, 3, 4], [0], "Sum elements >5 in [1,2,3,4] → 0"),
            ([6, 7], [13], "Sum elements >5 in [6,7] → 13"),
        ],
        [
            ([100, 1, 50], [150], "Sum >5 in [100,1,50] → 150"),
            ([5, 5, 5], [0], "Sum >5 in [5,5,5] → 0 (boundary)"),
            ([10], [10], "Sum >5 in [10] → 10"),
        ]
    )
    
    # 2. Count large elements (FILTER_GT_5 → COUNT)
    discover_and_test(
        "COUNT_LARGE",
        [
            ([1, 6, 2, 8, 3], [2], "Count elements >5 in [1,6,2,8,3] → 2"),
            ([1, 2, 3], [0], "Count elements >5 in [1,2,3] → 0"),
            ([10, 20, 30], [3], "Count elements >5 in [10,20,30] → 3"),
        ],
        [
            ([6, 5, 6], [2], "Count >5 in [6,5,6] → 2"),
            ([100], [1], "Count >5 in [100] → 1"),
            ([0, 0, 0], [0], "Count >5 in [0,0,0] → 0"),
        ]
    )
    
    # 3. Average of large elements (FILTER_GT_5 → [SUM, COUNT] → DIVIDE)
    # This would require 3+ steps and division, so let's try something else
    
    # 4. Find minimum of large elements (FILTER_GT_5 → SORT_ASCENDING → GET_FIRST)
    print("\n" + "="*60)
    print("Attempting 3-step composition: MIN_OF_LARGE")
    print("="*60)
    
    problems = [
        Problem(
            name="min_large_1",
            problem_type="transformation",
            input_data=torch.tensor([3, 8, 2, 10, 6], dtype=torch.float32),
            output_data=torch.tensor([6], dtype=torch.float32),
            description="Min of elements >5 in [3,8,2,10,6] → 6"
        ),
        Problem(
            name="min_large_2", 
            problem_type="transformation",
            input_data=torch.tensor([1, 20, 15, 3], dtype=torch.float32),
            output_data=torch.tensor([15], dtype=torch.float32),
            description="Min of elements >5 in [1,20,15,3] → 15"
        ),
    ]
    
    print("\nTraining examples:")
    for p in problems:
        print(f"  • {p.description}")
    
    concept = discover_concept_from_failures(problems)
    if concept:
        print(f"\n✓ Discovered: {concept.transformation_function}")
        if len(concept.transformation_function) == 3:
            print("  🎉 Successfully discovered a 3-step algorithm!")
    else:
        print("\n✗ Discovery failed (might need deeper search)")
    
    print("\n" + "="*70)
    print("KEY INSIGHTS:")
    print("• FILTER enables value-based selection (not just position)")
    print("• Combined with aggregation, creates powerful algorithms")
    print("• System discovers these compositions automatically")
    print("• Real-world applications: data analysis, statistics, ML preprocessing")
    print("="*70)


if __name__ == "__main__":
    main()