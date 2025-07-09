#!/usr/bin/env python3
"""Day 11-12 Demo: Enhanced UI with Accessibility Features.

This demo showcases the complete interactive visualization with:
- Dynamic status titles
- Parent/child relationship visualization
- Accessibility features (line styles)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter


def main():
    """Run the Day 11-12 demo."""
    print("\nRegionAI - Days 11-12: Enhanced UI & Accessibility")
    print("=" * 60)
    print("\nNew features in this demo:")
    print("• Dynamic title shows current state")
    print("• Parent/child relationships visualized when selecting")
    print("• Accessibility: Different line styles for relationships")
    print("  - Parents: Light blue with dashed lines")
    print("  - Children: Light green with dotted lines")
    print("\n" + "=" * 60)
    print("\nInstructions:")
    print("1. Left-click 'MAMMAL' to see its parents and children")
    print("2. Notice the dynamic title updates")
    print("3. Try pathfinding from inner to outer regions")
    print("4. Observe the different line styles for accessibility")
    print("\n" + "=" * 60 + "\n")
    
    # Create a rich hierarchy to demonstrate parent/child visualization
    space = ConceptSpace2D()
    
    # Main hierarchy
    space.add_region("ENTITY", Box2D(0, 0, 200, 200))
    space.add_region("LIVING", Box2D(10, 10, 190, 190))
    space.add_region("ANIMAL", Box2D(20, 20, 100, 180))
    space.add_region("MAMMAL", Box2D(30, 30, 90, 90))
    
    # Mammals branch
    space.add_region("CAT", Box2D(35, 35, 55, 55))
    space.add_region("DOG", Box2D(60, 60, 85, 85))
    space.add_region("SIAMESE", Box2D(40, 40, 50, 50))
    space.add_region("BEAGLE", Box2D(65, 65, 80, 80))
    
    # Other animals
    space.add_region("BIRD", Box2D(30, 100, 90, 160))
    space.add_region("EAGLE", Box2D(40, 110, 60, 130))
    space.add_region("SPARROW", Box2D(65, 135, 85, 155))
    
    # Plants branch
    space.add_region("PLANT", Box2D(110, 20, 180, 180))
    space.add_region("TREE", Box2D(120, 30, 170, 90))
    space.add_region("FLOWER", Box2D(120, 100, 170, 170))
    space.add_region("OAK", Box2D(130, 40, 160, 80))
    space.add_region("ROSE", Box2D(130, 110, 160, 160))
    
    # Create and show the interactive plotter
    plotter = InteractivePlotter(space)
    
    print("Launching interactive visualization...")
    print("\nTip: Click on 'MAMMAL' first to see parent/child highlighting!")
    
    plotter.show()


if __name__ == "__main__":
    main()