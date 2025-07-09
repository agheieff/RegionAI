#!/usr/bin/env python3
"""
Day 25-26: Verification of Deep Compositional Discovery with Filtering
This script proves the system can discover complex multi-step algorithms.
"""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.spaces.concept_space import ConceptSpaceND
from regionai.engine.main import ReasoningEngine
from regionai.data.problem import Problem
from regionai.discovery.discover import discover_concept_from_failures
from regionai.discovery.transformation import PRIMITIVE_OPERATIONS, TransformationSequence


def test_filter_sum_discovery():
    """Test discovery of FILTER_GT_5 -> SUM composition."""
    print("=" * 70)
    print("DAY 25-26: DEEP COMPOSITIONAL DISCOVERY WITH FILTERING")
    print("=" * 70)
    
    # Verify our new primitive exists
    print("\n1. NEW PRIMITIVE VERIFICATION")
    print("-" * 50)
    primitive_names = [p.name for p in PRIMITIVE_OPERATIONS]
    if "FILTER_GT_5" in primitive_names:
        print("✓ FILTER_GT_5 primitive is available")
        # Test the primitive
        test_data = torch.tensor([1.0, 6.0, 3.0, 10.0, 4.0])
        filter_op = next(p for p in PRIMITIVE_OPERATIONS if p.name == "FILTER_GT_5")
        filtered = filter_op.operation(test_data)
        print(f"  Test: {test_data.tolist()} → {filtered.tolist()}")
    else:
        print("❌ FILTER_GT_5 not found!")
        return False
    
    # Create problems requiring FILTER -> SUM
    print("\n\n2. PROBLEM DEFINITION - Sum elements greater than 5")
    print("-" * 50)
    problems = [
        Problem(
            name="filter_sum_1",
            problem_type="transformation",
            input_data=torch.tensor([2.0, 7.0, 1.0, 9.0, 3.0]),
            output_data=torch.tensor([16.0]),  # 7 + 9 = 16
            description="Sum of [2,7,1,9,3] where >5 → 16"
        ),
        Problem(
            name="filter_sum_2",
            problem_type="transformation",
            input_data=torch.tensor([10.0, 4.0, 6.0, 2.0]),
            output_data=torch.tensor([16.0]),  # 10 + 6 = 16
            description="Sum of [10,4,6,2] where >5 → 16"
        ),
        Problem(
            name="filter_sum_3",
            problem_type="transformation",
            input_data=torch.tensor([1.0, 2.0, 3.0]),
            output_data=torch.tensor([0.0]),  # Nothing > 5
            description="Sum of [1,2,3] where >5 → 0"
        ),
    ]
    
    print("Test problems:")
    for p in problems:
        print(f"  • {p.description}")
    
    # Run discovery
    print("\n\n3. DISCOVERY PHASE - Finding multi-step solution")
    print("-" * 50)
    discovered = discover_concept_from_failures(problems)
    
    if not discovered:
        print("❌ Discovery failed!")
        return False
    
    print(f"\n✓ Discovered concept: {discovered.name}")
    print(f"  Algorithm: {discovered.transformation_function}")
    
    # Analyze the discovered algorithm
    seq = discovered.transformation_function
    if len(seq) != 2:
        print(f"❌ Expected 2-step sequence, got {len(seq)} steps")
        return False
    
    step_names = [t.name for t in seq.transformations]
    if step_names != ["FILTER_GT_5", "SUM"]:
        print(f"❌ Expected [FILTER_GT_5, SUM], got {step_names}")
        return False
    
    print("\n✓ Correctly discovered: FILTER_GT_5 → SUM")
    
    # Test generalization
    print("\n\n4. GENERALIZATION TEST - Novel inputs")
    print("-" * 50)
    
    # Create engine with discovered concept
    space = ConceptSpaceND()
    space.add_region(discovered.name, discovered)
    engine = ReasoningEngine(space)
    
    test_cases = [
        ([100.0, 5.0, 6.0, 1.0], [106.0]),  # 100 + 6
        ([6.0, 7.0, 8.0], [21.0]),  # All > 5
        ([0.0, -10.0, 20.0], [20.0]),  # With negatives
        ([5.0, 5.0, 5.0], [0.0]),  # Exactly 5 (not greater)
        ([8.0], [8.0]),  # Single element > 5
    ]
    
    successes = 0
    for input_list, expected_list in test_cases:
        test_problem = Problem(
            name="test",
            problem_type="transformation",
            input_data=torch.tensor(input_list),
            output_data=torch.tensor(expected_list),
            description=f"{input_list} → {expected_list[0]}"
        )
        
        solution = engine.solve_problem(test_problem)
        if solution:
            print(f"  ✓ {test_problem.description}")
            successes += 1
        else:
            # Check what the algorithm actually produces
            result = seq.apply(test_problem.input_data)
            print(f"  ✗ FAILED: {test_problem.description} (got {result.item():.1f})")
    
    print(f"\nResult: {successes}/{len(test_cases)} novel problems solved!")
    
    return successes == len(test_cases)


def demonstrate_search_process():
    """Show how BFS explores to find the solution."""
    print("\n\n5. SEARCH PROCESS VISUALIZATION")
    print("-" * 50)
    
    print("How BFS discovers FILTER_GT_5 → SUM:")
    print("\nDepth 1 - Single operations:")
    print("  • FILTER_GT_5 alone → ❌ Returns [7,9] not [16]")
    print("  • SUM alone → ❌ Returns [22] not [16]")
    print("  • REVERSE, SORT, etc. → ❌ Wrong type of operation")
    
    print("\nDepth 2 - Two-operation sequences:")
    print("  • [REVERSE, SUM] → ❌ Still sums everything")
    print("  • [SORT_ASCENDING, SUM] → ❌ Still sums everything")
    print("  • [FILTER_GT_5, REVERSE] → ❌ Returns filtered but reversed")
    print("  • [FILTER_GT_5, SUM] → ✓ Filters then sums!")
    
    print("\n💡 The system systematically tried combinations until finding the solution.")


def explore_other_filter_compositions():
    """Test other interesting filter-based compositions."""
    print("\n\n6. OTHER FILTER COMPOSITIONS")
    print("-" * 50)
    
    # Count elements > 5
    print("\nTesting FILTER_GT_5 → COUNT:")
    problems = [
        Problem(
            name="count_large",
            problem_type="transformation",
            input_data=torch.tensor([1.0, 6.0, 10.0, 3.0, 8.0]),
            output_data=torch.tensor([3.0]),  # 3 elements > 5
            description="Count elements > 5"
        ),
    ]
    
    concept = discover_concept_from_failures(problems)
    if concept:
        print(f"✓ Discovered: {concept.transformation_function}")
    
    # Find max of elements > 5
    print("\nTesting FILTER_GT_5 → SORT_ASCENDING → GET_LAST:")
    problems = [
        Problem(
            name="max_large",
            problem_type="transformation",
            input_data=torch.tensor([1.0, 7.0, 3.0, 9.0, 6.0]),
            output_data=torch.tensor([9.0]),  # Max of [7,9,6]
            description="Max of elements > 5"
        ),
    ]
    
    concept = discover_concept_from_failures(problems)
    if concept:
        print(f"✓ Discovered: {concept.transformation_function}")


def analyze_computational_complexity():
    """Discuss the search space complexity."""
    print("\n\n7. COMPUTATIONAL COMPLEXITY")
    print("-" * 50)
    
    num_primitives = len(PRIMITIVE_OPERATIONS)
    print(f"With {num_primitives} primitives:")
    print(f"• Depth 1: {num_primitives} possibilities")
    print(f"• Depth 2: {num_primitives**2} = {num_primitives**2} possibilities")
    print(f"• Depth 3: {num_primitives**3} = {num_primitives**3} possibilities")
    
    print(f"\nTotal search space up to depth 3: {sum(num_primitives**i for i in range(1,4))} sequences")
    print("\nBFS guarantees finding the shortest solution, but the search")
    print("space grows exponentially. Future optimizations needed:")
    print("• Heuristics to guide search")
    print("• Pruning invalid combinations")
    print("• Learning from previous discoveries")


if __name__ == "__main__":
    if test_filter_sum_discovery():
        demonstrate_search_process()
        explore_other_filter_compositions()
        analyze_computational_complexity()
        print("\n" + "=" * 70)
        print("✨ Day 25-26 verification complete!")
        print("🎯 The system discovers complex filtering + aggregation algorithms!")
        print("=" * 70)
    else:
        print("\n❌ Deep compositional discovery test failed!")