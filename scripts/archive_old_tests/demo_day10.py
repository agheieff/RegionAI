#!/usr/bin/env python3
"""Day 10 Demo: Visualizing the Reasoning Process.

This demo showcases the complete interactive 2D visualization
with pathfinding capabilities.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.region import Box2D
from regionai.spaces.concept_space import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter


def main():
    """Run the Day 10 demo."""
    print("\nRegionAI - Day 10: Visualizing the Reasoning Process")
    print("=" * 60)
    print("\nThis demo shows the complete 2D visualization with:")
    print("• Interactive selection (left-click)")
    print("• Pathfinding between concepts (right-click)")
    print("• Visual highlighting of reasoning paths")
    print("\n" + "=" * 60)
    print("\nInstructions:")
    print("1. Left-click any region to select it (turns red)")
    print("2. Right-click a region to start pathfinding (turns purple)")
    print("3. Right-click another region to find path (path turns orange)")
    print("4. Press 'C' to clear all selections")
    print("\n" + "=" * 60)
    print("\nExample to try:")
    print("1. Right-click on 'LAPTOP' (innermost region)")
    print("2. Right-click on 'ENTITY' (outermost region)")
    print("3. Watch the hierarchical path light up in orange!")
    print("\n" + "=" * 60 + "\n")

    # Create a rich concept hierarchy
    space = ConceptSpace2D()

    # Top level
    space.add_region("ENTITY", Box2D(0, 0, 200, 200))

    # Second level - physical vs abstract
    space.add_region("PHYSICAL", Box2D(10, 10, 95, 190))
    space.add_region("ABSTRACT", Box2D(105, 10, 190, 190))

    # Physical branch
    space.add_region("OBJECT", Box2D(20, 20, 85, 85))
    space.add_region("DEVICE", Box2D(30, 30, 75, 75))
    space.add_region("COMPUTER", Box2D(40, 40, 65, 65))
    space.add_region("LAPTOP", Box2D(45, 45, 60, 60))

    # Living things branch
    space.add_region("LIVING", Box2D(20, 100, 85, 180))
    space.add_region("ANIMAL", Box2D(25, 110, 80, 170))
    space.add_region("MAMMAL", Box2D(30, 120, 75, 160))
    space.add_region("HUMAN", Box2D(35, 130, 70, 150))

    # Abstract branch
    space.add_region("CONCEPT", Box2D(115, 20, 180, 85))
    space.add_region("MATHEMATICS", Box2D(125, 30, 170, 75))
    space.add_region("ALGEBRA", Box2D(135, 40, 160, 65))

    space.add_region("EMOTION", Box2D(115, 100, 180, 180))
    space.add_region("HAPPINESS", Box2D(125, 110, 170, 170))
    space.add_region("JOY", Box2D(135, 120, 160, 160))

    # Create and show the interactive plotter
    plotter = InteractivePlotter(space)
    plotter.show()


if __name__ == "__main__":
    main()
