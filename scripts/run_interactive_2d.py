#!/usr/bin/env python3
"""Interactive 2D visualization of concept hierarchies."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.plotter import ConceptPlotter


def create_hierarchy_example():
    """Create a simple concept hierarchy: THING > ANIMAL > MAMMAL > CAT."""
    space = ConceptSpace2D()
    
    # Define the hierarchy with nested boxes
    space.add_region("THING", Box2D(0, 0, 100, 100))
    space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
    space.add_region("MAMMAL", Box2D(20, 20, 80, 80))
    space.add_region("CAT", Box2D(30, 30, 50, 50))
    
    # Add some other concepts at different levels
    space.add_region("PLANT", Box2D(10, 10, 40, 40))  # Overlaps with ANIMAL
    space.add_region("DOG", Box2D(60, 60, 80, 80))   # Another mammal
    space.add_region("BIRD", Box2D(15, 60, 35, 80))  # Non-mammal animal
    
    return space


def create_overlapping_example():
    """Create an example with overlapping concepts."""
    space = ConceptSpace2D()
    
    # Create overlapping regions to show multiple inheritance
    space.add_region("LIVING_THING", Box2D(0, 0, 100, 100))
    space.add_region("FLYING_THING", Box2D(40, 20, 120, 80))
    space.add_region("MAMMAL", Box2D(10, 30, 70, 90))
    space.add_region("BAT", Box2D(45, 40, 65, 60))  # In both FLYING_THING and MAMMAL
    
    return space


def main():
    """Run the interactive 2D visualization."""
    print("RegionAI - 2D Concept Visualization")
    print("=" * 40)
    
    # Create plotter
    plotter = ConceptPlotter()
    
    # Example 1: Hierarchical concepts
    print("\n1. Creating hierarchical concept space...")
    hierarchy_space = create_hierarchy_example()
    
    # Analyze relationships
    relationships = hierarchy_space.get_hierarchical_relationships()
    print("\nHierarchical relationships:")
    for parent, children in relationships.items():
        if children:
            print(f"  {parent} contains: {', '.join(children)}")
    
    # Plot hierarchy
    fig1 = plotter.plot(
        hierarchy_space,
        title="Concept Hierarchy Example",
        show_hierarchy=True
    )
    
    # Example 2: Overlapping concepts
    print("\n2. Creating overlapping concept space...")
    overlap_space = create_overlapping_example()
    
    # Check what contains BAT
    bat_region = overlap_space.get_region("BAT")
    containers = overlap_space.find_containing_regions(bat_region)
    print(f"\nBAT is contained in: {', '.join(containers)}")
    
    # Plot overlapping concepts
    fig2 = plotter.plot(
        overlap_space,
        title="Overlapping Concepts (Multiple Inheritance)",
        show_hierarchy=False
    )
    
    # Show all plots
    print("\nDisplaying visualizations...")
    plotter.show()
    
    # Save examples
    print("\nSaving visualizations...")
    fig1.savefig("concept_hierarchy.png", dpi=150, bbox_inches='tight')
    fig2.savefig("concept_overlap.png", dpi=150, bbox_inches='tight')
    print("Saved: concept_hierarchy.png, concept_overlap.png")


if __name__ == "__main__":
    main()