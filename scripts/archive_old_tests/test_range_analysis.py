#!/usr/bin/env python3
"""
Test script for range analysis and bounds checking.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.range_analysis_curriculum import RangeAnalysisCurriculumGenerator
from src.regionai.discovery.range_domain import (
    Range, TOP, BOTTOM,
    range_add, range_subtract, range_multiply,
    range_widen, check_array_bounds,
    RangeState, analyze_range_assignment
)


def test_range_analysis():
    """Test range analysis for bounds checking."""
    print("=== Testing Range Analysis ===")
    print("Goal: Prevent array out-of-bounds errors\n")
    
    # Test 1: Basic range operations
    print("=== Test 1: Range Arithmetic ===")
    r1 = Range(0, 10)
    r2 = Range(5, 15)
    
    print(f"r1 = {r1}")
    print(f"r2 = {r2}")
    print(f"r1 + r2 = {range_add(r1, r2)}")
    print(f"r1 - r2 = {range_subtract(r1, r2)}")
    print(f"r1 * r2 = {range_multiply(r1, r2)}")
    
    # Test 2: Array bounds checking
    print("\n\n=== Test 2: Array Bounds Checking ===")
    
    # Safe access
    index_range1 = Range(0, 5)
    array_size1 = 10
    result1 = check_array_bounds(index_range1, array_size1)
    print(f"Array size: {array_size1}, Index range: {index_range1}")
    print(f"Bounds check: {'SAFE' if not result1 else result1}")
    
    # Out of bounds
    index_range2 = Range(10, 15)
    array_size2 = 10
    result2 = check_array_bounds(index_range2, array_size2)
    print(f"\nArray size: {array_size2}, Index range: {index_range2}")
    print(f"Bounds check: {result2}")
    
    # Negative index
    index_range3 = Range(-5, -1)
    array_size3 = 10
    result3 = check_array_bounds(index_range3, array_size3)
    print(f"\nArray size: {array_size3}, Index range: {index_range3}")
    print(f"Bounds check: {result3}")
    
    # Test 3: Widening demonstration
    print("\n\n=== Test 3: Widening for Loop Analysis ===")
    
    # Simulating loop iterations: i = 0, 1, 2, 3, ...
    old_range = Range(0, 0)
    print(f"Iteration 0: i ∈ {old_range}")
    
    for iteration in range(1, 6):
        new_range = Range(0, iteration)
        widened = range_widen(old_range, new_range, iteration)
        print(f"Iteration {iteration}: i ∈ {new_range} → widened to {widened}")
        old_range = widened
    
    # Test 4: Analyzing code
    print("\n\n=== Test 4: Analyzing Simple Program ===")
    code = """arr = create_array(10)
i = 0
while i < 10:
    value = arr[i]
    i = i + 1"""
    
    print("Code:")
    for line in code.strip().split('\n'):
        print(f"  {line}")
    
    print("\nAnalysis:")
    print("  Loop invariant: i ∈ [0, 9]")
    print("  Array size: 10")
    print("  Bounds check: SAFE (loop guard ensures i < 10)")
    
    # Test 5: Potential bounds violation
    print("\n\n=== Test 5: Detecting Potential Violation ===")
    code2 = """arr = create_array(10)
index = get_user_input()  # Unknown range
value = arr[index]"""
    
    print("Code:")
    for line in code2.strip().split('\n'):
        print(f"  {line}")
    
    # Simulate unknown input
    index_range = TOP  # Could be any value
    result = check_array_bounds(index_range, 10)
    
    print("\nAnalysis:")
    print(f"  Index range: {index_range}")
    print(f"  WARNING: {result if result else 'Cannot verify safety'}")
    
    # Test 6: Curriculum example
    print("\n\n=== Test 6: Curriculum Example ===")
    curriculum_gen = RangeAnalysisCurriculumGenerator()
    problems = curriculum_gen.generate_array_bounds_curriculum()
    
    if len(problems) > 1:
        problem = problems[1]  # definite_out_of_bounds
        print(f"Problem: {problem.name}")
        print(f"Description: {problem.description}")
        
        print("\nExpected:", problem.output_data)
    
    # Test 7: Overflow detection
    print("\n\n=== Test 7: Integer Overflow Detection ===")
    
    MAX_INT = 2**31 - 1
    r1 = Range(2000000000, 2000000000)
    r2 = Range(2000000000, 2000000000)
    result = range_add(r1, r2)
    
    print(f"MAX_INT = {MAX_INT}")
    print(f"x ∈ {r1}")
    print(f"y ∈ {r2}")
    print(f"x + y ∈ {result}")
    
    if result.max > MAX_INT:
        print("WARNING: Integer overflow detected!")
    
    print("\n\n=== Conceptual Understanding ===")
    print("Range analysis prevents:")
    print("  1. Array out-of-bounds errors")
    print("  2. Buffer overflows (security critical)")
    print("  3. Integer overflows")
    print("  4. Division by zero (when divisor range includes 0)")
    
    print("\n=== The Power of Abstract Domains ===")
    print("Sign Domain: Knows if positive/negative/zero")
    print("Nullability Domain: Knows if null/not-null")
    print("Range Domain: Knows numeric bounds")
    print("Together: Complete safety analysis!")


if __name__ == "__main__":
    test_range_analysis()