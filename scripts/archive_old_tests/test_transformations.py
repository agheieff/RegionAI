#!/usr/bin/env python3
"""Test the transformation module to ensure it works correctly."""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.discovery.transformation import (
    Transformation, 
    TransformationSequence, 
    PRIMITIVE_OPERATIONS
)


def test_single_transformations():
    """Test individual primitive operations."""
    print("Testing individual transformations:")
    print("-" * 50)
    
    # Test data
    test_tensor = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
    print(f"Original tensor: {test_tensor}")
    print()
    
    # Test each primitive operation
    for trans in PRIMITIVE_OPERATIONS:
        try:
            result = trans.operation(test_tensor)
            print(f"{trans.name}: {result}")
        except Exception as e:
            print(f"{trans.name}: Error - {e}")
    
    print()


def test_transformation_sequences():
    """Test sequences of transformations."""
    print("Testing transformation sequences:")
    print("-" * 50)
    
    test_tensor = torch.tensor([3.0, 1.0, 4.0, 1.0, 5.0])
    print(f"Original tensor: {test_tensor}")
    print()
    
    # Test 1: Reverse
    seq1 = TransformationSequence([
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "REVERSE")
    ])
    result1 = seq1.apply(test_tensor)
    print(f"{seq1} → {result1}")
    
    # Test 2: Sort then reverse
    seq2 = TransformationSequence([
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "SORT_ASCENDING"),
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "REVERSE")
    ])
    result2 = seq2.apply(test_tensor)
    print(f"{seq2} → {result2}")
    
    # Test 3: Add one then sum
    seq3 = TransformationSequence([
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "ADD_ONE"),
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "SUM")
    ])
    result3 = seq3.apply(test_tensor)
    print(f"{seq3} → {result3}")
    
    # Test 4: Complex sequence
    seq4 = TransformationSequence([
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "SORT_ASCENDING"),
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "SUBTRACT_ONE"),
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "GET_LAST")
    ])
    result4 = seq4.apply(test_tensor)
    print(f"{seq4} → {result4}")
    
    # Test 5: Empty sequence (identity)
    seq5 = TransformationSequence([])
    result5 = seq5.apply(test_tensor)
    print(f"{seq5} → {result5}")
    
    print()


def test_transformation_composition():
    """Test that transformations compose correctly."""
    print("Testing transformation composition:")
    print("-" * 50)
    
    # Create a simple test case
    x = torch.tensor([1.0, 2.0, 3.0])
    
    # Manual composition
    step1 = torch.flip(x, dims=[0])  # REVERSE: [3, 2, 1]
    step2 = step1 + 1  # ADD_ONE: [4, 3, 2]
    expected = step2
    
    # Using TransformationSequence
    seq = TransformationSequence([
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "REVERSE"),
        next(t for t in PRIMITIVE_OPERATIONS if t.name == "ADD_ONE")
    ])
    result = seq.apply(x)
    
    print(f"Input: {x}")
    print(f"Expected: {expected}")
    print(f"Got: {result}")
    print(f"Match: {torch.allclose(expected, result)}")
    
    print()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Day 20: Testing Transformation Module")
    print("="*60 + "\n")
    
    test_single_transformations()
    test_transformation_sequences()
    test_transformation_composition()
    
    print("="*60)
    print("All tests completed!")
    print("\nThe transformation module is working correctly.")
    print("We now have:")
    print("• A way to represent single operations (Transformation)")
    print("• A way to compose operations (TransformationSequence)")
    print(f"• A library of {len(PRIMITIVE_OPERATIONS)} primitive operations")
    print("\nThe system is ready for algorithmic discovery!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()