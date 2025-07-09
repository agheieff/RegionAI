#!/usr/bin/env python3
"""Day 20 Demo: The Transformation Language in Action"""

import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.discovery import (
    Transformation,
    TransformationSequence,
    PRIMITIVE_OPERATIONS
)


def demo_primitives():
    """Demonstrate each primitive operation."""
    print("\n1. Primitive Operations - The Alphabet")
    print("-" * 50)
    print("Each primitive is a basic, indivisible operation:")
    print()
    
    data = torch.tensor([3.0, 1.0, 4.0, 1.0, 5.0])
    print(f"Starting data: {data}")
    print()
    
    # Show a few key primitives
    examples = ["REVERSE", "SORT_ASCENDING", "ADD_ONE", "SUM"]
    for name in examples:
        op = next(p for p in PRIMITIVE_OPERATIONS if p.name == name)
        result = op.operation(data)
        print(f"  {name:15} → {result}")
    
    print(f"\n  ... and {len(PRIMITIVE_OPERATIONS) - len(examples)} more primitives")


def demo_composition():
    """Demonstrate composing operations into algorithms."""
    print("\n\n2. Composition - Building Algorithms")
    print("-" * 50)
    print("We can chain primitives to create complex behaviors:")
    print()
    
    data = torch.tensor([3.0, 1.0, 4.0, 1.0, 5.0])
    print(f"Starting data: {data}")
    print()
    
    # Example 1: Sort descending
    ops1 = [
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "SORT_ASCENDING"),
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "REVERSE")
    ]
    seq1 = TransformationSequence(ops1)
    result1 = seq1.apply(data)
    print(f"  {seq1}")
    print(f"  Result: {result1}")
    print(f"  (This creates a sort-descending algorithm!)")
    
    print()
    
    # Example 2: Find the maximum
    ops2 = [
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "SORT_ASCENDING"),
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "GET_LAST")
    ]
    seq2 = TransformationSequence(ops2)
    result2 = seq2.apply(data)
    print(f"  {seq2}")
    print(f"  Result: {result2}")
    print(f"  (This finds the maximum value!)")
    
    print()
    
    # Example 3: Count elements greater than original first element
    # This is trickier - shows the need for more primitives in real use
    ops3 = [
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "SUBTRACT_ONE"),
        next(p for p in PRIMITIVE_OPERATIONS if p.name == "COUNT")
    ]
    seq3 = TransformationSequence(ops3)
    result3 = seq3.apply(data)
    print(f"  {seq3}")
    print(f"  Result: {result3}")
    print(f"  (Counts elements after subtracting 1)")


def demo_discovery_preview():
    """Preview how discovery will work."""
    print("\n\n3. Discovery Preview")
    print("-" * 50)
    print("With this language, the system can discover algorithms by:")
    print()
    print("  1. Trying different sequences of primitives")
    print("  2. Testing if they produce the desired output")
    print("  3. Finding the shortest/best sequence")
    print()
    print("For example, to reverse a list:")
    print("  - Try: [ADD_ONE] → Nope!")
    print("  - Try: [SORT_ASCENDING] → Nope!")
    print("  - Try: [REVERSE] → Yes! ✓")
    print()
    print("Or to find the minimum:")
    print("  - Try: [GET_FIRST] → Nope!")
    print("  - Try: [SORT_ASCENDING -> GET_FIRST] → Yes! ✓")


def main():
    """Run the demo."""
    print("\n" + "="*60)
    print("Day 20 Demo: The Transformation Language")
    print("="*60)
    
    print("\nWe've created a formal language for algorithms:")
    print("• Primitives = Letters")
    print("• Sequences = Words/Programs")
    print("• Discovery = Finding the right sequence")
    
    demo_primitives()
    demo_composition()
    demo_discovery_preview()
    
    print("\n" + "="*60)
    print("The transformation language is ready!")
    print("Next: Teaching the system to discover algorithms automatically")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()