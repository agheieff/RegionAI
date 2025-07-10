#!/usr/bin/env python3
"""Days 15-16 Demo: N-Dimensional Visualization with 2D Projections.

This demo shows the interactive plotter working with N-dimensional
concept spaces, projecting them onto 2D for visualization.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.region import RegionND
from regionai.spaces.concept_space import ConceptSpaceND
from regionai.visualization.interactive_plotter import InteractivePlotter


def demo_3d_visualization():
    """Demo 3D space projected to 2D."""
    print("\n3D Space Visualization Demo")
    print("-" * 50)
    print("Creating a 3D concept hierarchy...")
    print("Use X and Y keys to cycle through dimension pairs!")
    
    space = ConceptSpaceND()
    
    # Create 3D regions with interesting structure
    # Dimensions: width, height, depth
    space.add_region("UNIVERSE", RegionND([0, 0, 0], [100, 100, 100]))
    space.add_region("GALAXY", RegionND([10, 10, 10], [90, 90, 90]))
    space.add_region("SYSTEM", RegionND([20, 20, 20], [80, 80, 80]))
    
    # Add some variety in different dimensions
    space.add_region("PLANET_A", RegionND([30, 30, 30], [50, 50, 50]))
    space.add_region("PLANET_B", RegionND([60, 30, 60], [80, 50, 80]))
    space.add_region("MOON", RegionND([35, 35, 35], [45, 45, 45]))
    
    print("\nRegions created:")
    for name, region in space.items():
        print(f"  {name}: {region}")
    
    print("\nLaunching interactive visualization...")
    print("\nControls:")
    print("  Left-click: Select region")
    print("  Right-click: Pathfinding")
    print("  C: Clear selections")
    print("  X: Cycle X dimension (0→1→2→0...)")
    print("  Y: Cycle Y dimension (0→1→2→0...)")
    print("\nTry pressing X or Y to see different 2D slices of the 3D space!")
    
    plotter = InteractivePlotter(space)
    plotter.show()


def demo_5d_visualization():
    """Demo 5D space with dimension cycling."""
    print("\n5D Space Visualization Demo")
    print("-" * 50)
    print("Creating a 5D knowledge hierarchy...")
    
    space = ConceptSpaceND()
    
    # 5D space with varying positions in different dimensions
    space.add_region("KNOWLEDGE", RegionND([0, 0, 0, 0, 0], [100, 100, 100, 100, 100]))
    
    # Science branch - strong in dimensions 0,1
    space.add_region("SCIENCE", RegionND([10, 10, 40, 40, 40], [90, 90, 60, 60, 60]))
    space.add_region("PHYSICS", RegionND([20, 20, 45, 45, 45], [80, 80, 55, 55, 55]))
    
    # Arts branch - strong in dimensions 2,3
    space.add_region("ARTS", RegionND([40, 40, 10, 10, 40], [60, 60, 90, 90, 60]))
    space.add_region("MUSIC", RegionND([45, 45, 20, 20, 45], [55, 55, 80, 80, 55]))
    
    # Philosophy - centered in all dimensions
    space.add_region("PHILOSOPHY", RegionND([30, 30, 30, 30, 30], [70, 70, 70, 70, 70]))
    
    print("\n5D Regions created - they overlap differently in different dimensions!")
    print("\nDimension meanings (hypothetical):")
    print("  0: Analytical thinking")
    print("  1: Empirical observation")
    print("  2: Creative expression")
    print("  3: Emotional depth")
    print("  4: Abstract reasoning")
    
    print("\nLaunching interactive visualization...")
    print("\nTry cycling through dimensions to see how relationships change!")
    print("For example:")
    print("  - Dims 0,1: Science dominates")
    print("  - Dims 2,3: Arts dominates")
    print("  - Any dim with 4: More balanced view")
    
    plotter = InteractivePlotter(space, dim_x=0, dim_y=1)
    plotter.show()


def demo_backward_compatibility():
    """Show that 2D spaces still work."""
    print("\n2D Backward Compatibility Demo")
    print("-" * 50)
    print("Testing with traditional 2D regions...")
    
    from regionai.geometry.region import Box2D
    space = ConceptSpaceND()
    
    # Using Box2D (which creates 2D RegionND internally)
    space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
    space.add_region("MAMMAL", Box2D(20, 20, 80, 80))
    space.add_region("CAT", Box2D(30, 30, 50, 50))
    space.add_region("DOG", Box2D(60, 60, 80, 80))
    
    print("2D space created using Box2D - works seamlessly!")
    print("(X/Y keys won't do anything since there are only 2 dimensions)")
    
    plotter = InteractivePlotter(space)
    plotter.show()


def main():
    """Run demos based on user choice."""
    print("\n" + "="*60)
    print("Days 15-16: N-Dimensional Interactive Visualization")
    print("="*60)
    
    print("\nChoose a demo:")
    print("1. 3D Space Visualization")
    print("2. 5D Knowledge Space")
    print("3. 2D Backward Compatibility")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            demo_3d_visualization()
        elif choice == "2":
            demo_5d_visualization()
        elif choice == "3":
            demo_backward_compatibility()
        elif choice == "4":
            print("\nExiting...")
            break
        else:
            print("Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()