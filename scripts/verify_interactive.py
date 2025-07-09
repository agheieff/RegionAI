#!/usr/bin/env python3
"""Simple verification of the interactive plotter."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter


def main():
    # Create a simple hierarchy
    space = ConceptSpace2D()
    space.add_region("A", Box2D(0, 0, 100, 100))
    space.add_region("B", Box2D(20, 20, 80, 80))
    space.add_region("C", Box2D(40, 40, 60, 60))

    # Test the plotter
    plotter = InteractivePlotter(space)

    # Verify state initialization
    print("Initial state:")
    print(f"  pathfinding_start: {plotter.pathfinding_start}")
    print(f"  pathfinding_path: {plotter.pathfinding_path}")
    print(f"  selected_region: {plotter.selected_region}")

    # Test reset
    plotter.pathfinding_start = "TEST"
    plotter._reset_state()
    print("\nAfter reset:")
    print(f"  pathfinding_start: {plotter.pathfinding_start}")
    print(f"  pathfinding_path: {plotter.pathfinding_path}")
    print(f"  selected_region: {plotter.selected_region}")

    print("\nPlotter is ready for interactive use!")
    print("Remember: Right-click might require special handling in some terminals.")

    # Show the interactive plot
    plotter.show()


if __name__ == "__main__":
    main()
