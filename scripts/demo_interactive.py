#!/usr/bin/env python3
"""Interactive demo showcasing all RegionAI features."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter, VisualizationMode
from regionai.visualization.selection import SelectionManager, SelectionMode, HighlightStrategy
from regionai.analysis.relationships import RelationshipAnalyzer
from regionai.visualization.events import EventType, Event


def create_complex_hierarchy():
    """Create a complex concept hierarchy demonstrating all features."""
    space = ConceptSpace2D()
    
    # Universe of discourse
    space.add_region("ENTITY", Box2D(0, 0, 200, 200))
    
    # Major divisions
    space.add_region("ABSTRACT", Box2D(5, 5, 95, 195))
    space.add_region("PHYSICAL", Box2D(105, 5, 195, 195))
    
    # Abstract concepts
    space.add_region("INFORMATION", Box2D(10, 10, 50, 90))
    space.add_region("MATHEMATICS", Box2D(55, 10, 90, 90))
    space.add_region("COMPUTATION", Box2D(30, 50, 70, 90))  # Overlaps INFO and MATH
    
    # Physical concepts
    space.add_region("MATTER", Box2D(110, 10, 190, 90))
    space.add_region("ENERGY", Box2D(110, 100, 190, 180))
    space.add_region("LIVING", Box2D(120, 20, 180, 80))
    
    # Living things hierarchy
    space.add_region("PLANT", Box2D(125, 25, 145, 45))
    space.add_region("ANIMAL", Box2D(150, 25, 175, 75))
    space.add_region("MAMMAL", Box2D(155, 30, 170, 50))
    space.add_region("BIRD", Box2D(155, 55, 170, 70))
    
    # Specific instances
    space.add_region("DOG", Box2D(157, 32, 162, 37))
    space.add_region("CAT", Box2D(163, 32, 168, 37))
    space.add_region("EAGLE", Box2D(157, 57, 162, 62))
    space.add_region("PENGUIN", Box2D(163, 57, 168, 62))
    
    # Cross-domain concepts (Abstract + Physical)
    space.add_region("QUANTUM", Box2D(90, 95, 120, 125))  # Math/Physics boundary
    space.add_region("BIOINFORMATICS", Box2D(45, 85, 75, 115))  # Info + Living
    
    return space


def print_analysis_report(space):
    """Print a comprehensive analysis of the concept space."""
    print("\n" + "="*60)
    print("CONCEPT SPACE ANALYSIS REPORT")
    print("="*60)
    
    analyzer = RelationshipAnalyzer(space)
    results = analyzer.analyze_all()
    
    print(f"\nTotal Concepts: {results.statistics['total_regions']:.0f}")
    print(f"Total Relationships: {results.statistics['total_relationships']:.0f}")
    print(f"Maximum Hierarchy Depth: {results.statistics['max_hierarchy_depth']:.0f}")
    print(f"Coverage Overlap: {results.statistics['overlap_percentage']:.1f}%")
    
    print("\nHierarchical Chains:")
    for chain in results.hierarchies[:5]:  # Show top 5
        print(f"  {chain}")
    
    if results.inconsistencies:
        print("\nInconsistencies Detected:")
        for issue in results.inconsistencies:
            print(f"  - {issue}")
    else:
        print("\nNo inconsistencies detected ✓")


def demonstrate_selection_modes(space, plotter):
    """Demonstrate different selection modes."""
    print("\n" + "="*60)
    print("SELECTION MODE DEMONSTRATION")
    print("="*60)
    
    selection_mgr = SelectionManager(space, plotter.event_manager)
    
    # Single selection mode
    print("\n1. Single Selection Mode:")
    selection_mgr.set_mode(SelectionMode.SINGLE)
    selection_mgr.select_region("ANIMAL")
    info = selection_mgr.get_selection_info()
    print(f"   Selected: {info['selected']}")
    
    # Hierarchical selection
    print("\n2. Hierarchical Selection:")
    selection_mgr.clear_selection()
    selection_mgr.select_hierarchy("MAMMAL", include_ancestors=True, include_descendants=True)
    info = selection_mgr.get_selection_info()
    print(f"   Selected chain: {' > '.join(sorted(info['selected']))}")
    
    # Multiple selection with different highlight strategies
    print("\n3. Multiple Selection with Highlights:")
    selection_mgr.set_mode(SelectionMode.MULTIPLE)
    selection_mgr.clear_selection()
    selection_mgr.select_region("COMPUTATION")
    selection_mgr.select_region("QUANTUM")
    
    for strategy in [HighlightStrategy.OVERLAPPING, HighlightStrategy.RELATED]:
        selection_mgr.set_highlight_strategy(strategy)
        info = selection_mgr.get_selection_info()
        print(f"   Strategy '{strategy.value}': highlights {info['highlighted']}")


def main():
    """Run the interactive demo."""
    print("RegionAI - Advanced Interactive Demo")
    print("====================================")
    
    # Create concept space
    print("\nCreating complex concept hierarchy...")
    space = create_complex_hierarchy()
    
    # Analyze the space
    print_analysis_report(space)
    
    # Create interactive plotter
    print("\nLaunching interactive visualization...")
    plotter = InteractivePlotter(space)
    
    # Add custom event handler for demonstration
    def on_selection_change(event):
        if event.event_type == EventType.REGION_SELECTED:
            region_name = event.data['region_name']
            region = space.get_region(region_name)
            print(f"\nSelected: {region_name}")
            print(f"  Volume: {region.volume():.1f}")
            print(f"  Center: {region.center().tolist()}")
            
            # Show relationships
            contained = space.find_contained_regions(region)
            if contained:
                print(f"  Contains: {', '.join(contained)}")
            
            containers = space.find_containing_regions(region)
            if containers:
                print(f"  Contained by: {', '.join(containers)}")
    
    plotter.event_manager.register(EventType.REGION_SELECTED, on_selection_change)
    
    # Demonstrate selection modes
    demonstrate_selection_modes(space, plotter)
    
    # Create the interactive plot
    print("\n" + "="*60)
    print("INTERACTIVE CONTROLS:")
    print("="*60)
    print("  Mouse:")
    print("    - Click: Select/deselect region")
    print("    - Hover: Highlight related regions")
    print("  Keyboard:")
    print("    - ESC: Clear selection")
    print("    - H: Hierarchy visualization mode")
    print("    - O: Overlap visualization mode") 
    print("    - D: Debug mode (shows coordinates)")
    print("    - TAB: Cycle through regions")
    print("="*60)
    
    fig = plotter.create_interactive_plot(
        title="RegionAI - Interactive Concept Space Explorer"
    )
    
    # Set initial mode
    plotter.set_mode(VisualizationMode.HIERARCHY)
    
    # Show the plot
    plotter.show()
    
    print("\nDemo completed. Close the plot window to exit.")


if __name__ == "__main__":
    main()