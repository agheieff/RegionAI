#!/usr/bin/env python3
"""Interactive 2D visualization of concept hierarchies."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter


def main():
    """Run the interactive 2D visualization."""
    print("RegionAI - Interactive 2D Concept Visualization")
    print("=" * 50)
    print("Click on any region to select it and see its properties")
    print("=" * 50)
    
    # Create a concept space with a hierarchy
    space = ConceptSpace2D()
    
    # Define the hierarchy: THING > ANIMAL > MAMMAL > CAT
    space.add_region("THING", Box2D(0, 0, 100, 100))
    space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
    space.add_region("MAMMAL", Box2D(20, 20, 80, 80))
    space.add_region("CAT", Box2D(30, 30, 50, 50))
    
    # Add some other concepts
    space.add_region("PLANT", Box2D(15, 50, 35, 70))  # Overlaps with ANIMAL
    space.add_region("DOG", Box2D(60, 60, 75, 75))   # Another mammal
    
    # Create and show the interactive plotter
    plotter = InteractivePlotter(space)
    plotter.show()


if __name__ == "__main__":
    main()