#!/usr/bin/env python3
"""Test script to demonstrate pathfinding functionality."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.region import Box2D
from regionai.spaces.concept_space import ConceptSpace2D
from regionai.engine.pathfinder import Pathfinder


def main():
    """Demonstrate the pathfinding functionality."""
    print("RegionAI - Pathfinder Test")
    print("=" * 50)

    # Create a concept hierarchy
    space = ConceptSpace2D()

    # Build a more complex hierarchy
    space.add_region("ENTITY", Box2D(0, 0, 200, 200))
    space.add_region("LIVING", Box2D(10, 10, 190, 190))
    space.add_region("ANIMAL", Box2D(20, 20, 100, 100))
    space.add_region("MAMMAL", Box2D(30, 30, 90, 90))
    space.add_region("CAT", Box2D(40, 40, 60, 60))
    space.add_region("SIAMESE", Box2D(45, 45, 55, 55))

    # Also add a plant branch
    space.add_region("PLANT", Box2D(110, 110, 180, 180))
    space.add_region("TREE", Box2D(120, 120, 170, 170))
    space.add_region("OAK", Box2D(130, 130, 160, 160))

    # Test various paths
    test_cases = [
        ("SIAMESE", "CAT"),
        ("SIAMESE", "MAMMAL"),
        ("SIAMESE", "ENTITY"),
        ("CAT", "ANIMAL"),
        ("OAK", "LIVING"),
        ("SIAMESE", "OAK"),  # Should fail - no path
        ("ENTITY", "CAT"),  # Should fail - wrong direction
    ]

    for start, end in test_cases:
        path = Pathfinder.find_path(start, end, space)
        if path:
            print(f"Path from {start} to {end}: {' → '.join(path)}")
        else:
            print(f"No path from {start} to {end}")

    print("\n" + "=" * 50)
    print("Parent relationships:")
    for name in space:
        parent = space.get_parent(name)
        if parent:
            print(f"  {name} → {parent}")
        else:
            print(f"  {name} (root)")


if __name__ == "__main__":
    main()
