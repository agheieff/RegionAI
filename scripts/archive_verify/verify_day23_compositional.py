#!/usr/bin/env python3
"""
Day 23: Verification of Compositional Algorithm Discovery
This script proves that the system can discover multi-step algorithms.
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


def test_compositional_discovery():
    """Test that the system can discover multi-step algorithms."""
    print("=" * 70)
    print("DAY 23: COMPOSITIONAL ALGORITHM DISCOVERY")
    print("=" * 70)
    
    # Verify SORT_DESCENDING is not available as a primitive
    print("\n1. SETUP - Verifying constraints")
    print("-" * 50)
    primitive_names = [p.name for p in PRIMITIVE_OPERATIONS]
    print(f"Available primitives: {', '.join(primitive_names)}")
    if "SORT_DESCENDING" in primitive_names:
        print("❌ ERROR: SORT_DESCENDING should not be available!")
        return False
    print("✓ SORT_DESCENDING is not available (as intended)")
    
    # Create problems that require sorting in descending order
    print("\n\n2. PROBLEM DEFINITION - Sort in descending order")
    print("-" * 50)
    problems = [
        Problem(
            name="desc_sort_1",
            problem_type="transformation",
            input_data=torch.tensor([3.0, 1.0, 4.0, 1.0, 5.0]),
            output_data=torch.tensor([5.0, 4.0, 3.0, 1.0, 1.0]),
            description="Sort [3,1,4,1,5] → [5,4,3,1,1]"
        ),
        Problem(
            name="desc_sort_2",
            problem_type="transformation",
            input_data=torch.tensor([2.0, 7.0, 1.0, 8.0]),
            output_data=torch.tensor([8.0, 7.0, 2.0, 1.0]),
            description="Sort [2,7,1,8] → [8,7,2,1]"
        ),
        Problem(
            name="desc_sort_3",
            problem_type="transformation",
            input_data=torch.tensor([10.0, -5.0, 0.0]),
            output_data=torch.tensor([10.0, 0.0, -5.0]),
            description="Sort [10,-5,0] → [10,0,-5]"
        ),
    ]
    
    print("Test problems:")
    for p in problems:
        print(f"  • {p.description}")
    
    # Run discovery
    print("\n\n3. DISCOVERY PHASE - Finding compositional solution")
    print("-" * 50)
    discovered = discover_concept_from_failures(problems)
    
    if not discovered:
        print("❌ Discovery failed!")
        return False
    
    print(f"\n✓ Discovered concept: {discovered.name}")
    print(f"  Algorithm: {discovered.transformation_function}")
    
    # Analyze the discovered algorithm
    seq = discovered.transformation_function
    if not isinstance(seq, TransformationSequence):
        print("❌ Expected TransformationSequence!")
        return False
    
    if len(seq) != 2:
        print(f"❌ Expected 2-step sequence, got {len(seq)} steps")
        return False
    
    step_names = [t.name for t in seq.transformations]
    if step_names != ["SORT_ASCENDING", "REVERSE"]:
        print(f"❌ Expected [SORT_ASCENDING, REVERSE], got {step_names}")
        return False
    
    print("\n✓ Correctly discovered: SORT_ASCENDING → REVERSE")
    
    # Test generalization
    print("\n\n4. GENERALIZATION TEST - Novel inputs")
    print("-" * 50)
    
    # Create engine with discovered concept
    space = ConceptSpaceND()
    space.add_region(discovered.name, discovered)
    engine = ReasoningEngine(space)
    
    test_cases = [
        ([100.0, 50.0, 75.0, 25.0], [100.0, 75.0, 50.0, 25.0]),
        ([1.0], [1.0]),  # Single element
        ([3.0, 3.0, 3.0], [3.0, 3.0, 3.0]),  # All same
        ([-10.0, -20.0, -5.0, -15.0], [-5.0, -10.0, -15.0, -20.0]),  # All negative
        ([0.1, 0.5, 0.3, 0.7, 0.2], [0.7, 0.5, 0.3, 0.2, 0.1]),  # Decimals
    ]
    
    successes = 0
    for input_list, expected_list in test_cases:
        test_problem = Problem(
            name="test",
            problem_type="transformation",
            input_data=torch.tensor(input_list),
            output_data=torch.tensor(expected_list),
            description=f"{input_list} → {expected_list}"
        )
        
        solution = engine.solve_problem(test_problem)
        if solution:
            print(f"  ✓ {test_problem.description}")
            successes += 1
        else:
            print(f"  ✗ FAILED: {test_problem.description}")
    
    print(f"\nResult: {successes}/{len(test_cases)} novel problems solved!")
    
    return successes == len(test_cases)


def demonstrate_compositional_power():
    """Show other possible compositions the system could discover."""
    print("\n\n5. THE POWER OF COMPOSITION")
    print("-" * 50)
    
    print("With just 8 primitives, we can create many algorithms:")
    print("\n• SORT_DESCENDING = SORT_ASCENDING → REVERSE")
    print("• FIND_MAX = SORT_ASCENDING → GET_LAST")
    print("• FIND_MIN = SORT_ASCENDING → GET_FIRST")
    print("• FIND_SECOND_MAX = SORT_ASCENDING → REVERSE → GET_SECOND")
    print("• COUNT_PLUS_ONE = COUNT → ADD_ONE")
    print("\nAnd with deeper search:")
    print("• MEDIAN (for odd length) = SORT → GET_MIDDLE")
    print("• RANGE = SORT → [GET_LAST, GET_FIRST] → SUBTRACT")
    
    print("\n🚀 Compositional discovery enables emergent problem-solving!")


def trace_discovery_process():
    """Show step-by-step how BFS discovers the composition."""
    print("\n\n6. HOW BFS DISCOVERS COMPOSITIONS")
    print("-" * 50)
    
    print("Search process for SORT_DESCENDING:")
    print("\nDepth 1 - Single operations:")
    print("  • Try REVERSE → ❌ [3,1,2] becomes [2,1,3], not [3,2,1]")
    print("  • Try SORT_ASCENDING → ❌ [3,1,2] becomes [1,2,3], not [3,2,1]")
    print("  • Try ADD_ONE → ❌ Wrong operation type")
    print("  • ... (all single ops fail)")
    
    print("\nDepth 2 - Two-operation sequences:")
    print("  • Try [REVERSE, REVERSE] → ❌ Back to original")
    print("  • Try [REVERSE, SORT_ASCENDING] → ❌ Wrong order") 
    print("  • Try [SORT_ASCENDING, REVERSE] → ✓ [3,1,2]→[1,2,3]→[3,2,1] ✓")
    print("\n💡 Found it! The BFS ensures we find the shortest solution.")


if __name__ == "__main__":
    if test_compositional_discovery():
        demonstrate_compositional_power()
        trace_discovery_process()
        print("\n" + "=" * 70)
        print("✨ Day 23 verification complete!")
        print("🎯 The system discovers compositional algorithms!")
        print("=" * 70)
    else:
        print("\n❌ Compositional discovery test failed!")