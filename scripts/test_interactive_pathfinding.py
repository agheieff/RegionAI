#!/usr/bin/env python3
"""Test the interactive pathfinding functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter


def main():
    """Run the interactive pathfinding demo."""
    print("RegionAI - Interactive Pathfinding Demo")
    print("=" * 50)
    print("Controls:")
    print("  Left-click: Select a region")
    print("  Right-click: Set pathfinding start/end")
    print("  C key: Clear all selections")
    print("=" * 50)
    print("\nTry right-clicking on CAT, then right-clicking on THING!")
    print("=" * 50)
    
    # Create a hierarchical concept space
    space = ConceptSpace2D()
    
    # Build a hierarchy
    space.add_region("THING", Box2D(0, 0, 100, 100))
    space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
    space.add_region("MAMMAL", Box2D(20, 20, 80, 80))
    space.add_region("CAT", Box2D(30, 30, 50, 50))
    space.add_region("DOG", Box2D(60, 60, 75, 75))
    space.add_region("SIAMESE", Box2D(35, 35, 45, 45))
    
    # Add a separate branch
    space.add_region("PLANT", Box2D(15, 70, 35, 85))
    
    # Create and show the interactive plotter
    plotter = InteractivePlotter(space)
    plotter.show()


if __name__ == "__main__":
    main()