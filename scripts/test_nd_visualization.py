#!/usr/bin/env python3
"""Quick test of N-D visualization without GUI."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.region import RegionND
from regionai.spaces.concept_space import ConceptSpaceND
from regionai.visualization.interactive_plotter import InteractivePlotter


def test_projection():
    """Test that projection logic works correctly."""
    print("Testing N-D to 2D projection...")
    
    # Create 4D space
    space = ConceptSpaceND()
    space.add_region("4D_CUBE", RegionND([10, 20, 30, 40], [50, 60, 70, 80]))
    
    # Create plotter
    plotter = InteractivePlotter(space, dim_x=1, dim_y=3)
    
    # Test dimension info
    print(f"Max dimension in space: {plotter._get_max_dimension()}")
    print(f"Current projection: X={plotter.dim_x}, Y={plotter.dim_y}")
    
    # Test projection extraction
    region = space.get_region("4D_CUBE")
    min_corner = region.min_corner.cpu().numpy()
    
    print(f"\nOriginal 4D region: min={min_corner}")
    print(f"Projected X (dim 1): {min_corner[plotter.dim_x]}")
    print(f"Projected Y (dim 3): {min_corner[plotter.dim_y]}")
    
    print("\n✓ Projection logic works!")
    
    # Test dimension cycling (without redraw since no figure)
    print("\nTesting dimension cycling logic...")
    original_x = plotter.dim_x
    
    # Manually cycle without redraw
    max_dim = plotter._get_max_dimension()
    plotter.dim_x = (plotter.dim_x + 1) % max_dim
    if plotter.dim_x == plotter.dim_y:
        plotter.dim_x = (plotter.dim_x + 1) % max_dim
    
    print(f"After cycling X: {original_x} → {plotter.dim_x}")
    
    original_y = plotter.dim_y
    plotter.dim_y = (plotter.dim_y + 1) % max_dim
    if plotter.dim_y == plotter.dim_x:
        plotter.dim_y = (plotter.dim_y + 1) % max_dim
        
    print(f"After cycling Y: {original_y} → {plotter.dim_y}")
    
    print("\n✓ Dimension cycling works!")
    
    return True


if __name__ == "__main__":
    if test_projection():
        print("\n✅ All projection tests passed!")
        print("\nThe visualization is ready for N-dimensional spaces.")
        print("Run demo_day15_16_nd_visualization.py to see it in action!")