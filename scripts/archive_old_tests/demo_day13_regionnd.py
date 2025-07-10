#!/usr/bin/env python3
"""Day 13 Demo: RegionND - N-dimensional regions.

This demo showcases the new dimension-agnostic RegionND class
that can handle regions in any number of dimensions.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from regionai.geometry.region import RegionND, Box2D


def demo_2d():
    """Demonstrate 2D regions (backward compatible)."""
    print("\n2D Region Demo:")
    print("-" * 50)
    
    # Using new RegionND
    region1 = RegionND([0, 0], [10, 10])
    region2 = RegionND([5, 5], [15, 15])
    
    print(f"Region 1: {region1}")
    print(f"Region 2: {region2}")
    print(f"Region 1 volume (area): {region1.volume()}")
    print(f"Regions overlap: {region1.overlaps(region2)}")
    
    # Backward compatibility
    box = Box2D(0, 0, 5, 5)
    print(f"\nBox2D (backward compat): {box}")


def demo_3d():
    """Demonstrate 3D regions."""
    print("\n\n3D Region Demo:")
    print("-" * 50)
    
    # Create 3D cubes
    cube1 = RegionND([0, 0, 0], [10, 10, 10])
    cube2 = RegionND([2, 2, 2], [8, 8, 8])
    
    print(f"Outer cube: {cube1}")
    print(f"Inner cube: {cube2}")
    print(f"Outer volume: {cube1.volume()}")
    print(f"Inner volume: {cube2.volume()}")
    print(f"Outer contains inner: {cube1.contains(cube2)}")
    
    # Intersection
    cube3 = RegionND([5, 5, 5], [15, 15, 15])
    intersection = cube1.intersection(cube3)
    print(f"\nIntersection volume: {intersection.volume() if intersection else 'No intersection'}")


def demo_high_dimensional():
    """Demonstrate high-dimensional regions."""
    print("\n\nHigh-Dimensional Region Demo:")
    print("-" * 50)
    
    # 5D hypercubes
    dims = 5
    hyper1 = RegionND([0]*dims, [10]*dims)
    hyper2 = RegionND([2]*dims, [8]*dims)
    
    print(f"5D Hypercube 1: dims={hyper1.dims}, volume={hyper1.volume()}")
    print(f"5D Hypercube 2: dims={hyper2.dims}, volume={hyper2.volume()}")
    print(f"Containment: {hyper1.contains(hyper2)}")
    
    # 10D example
    dims = 10
    region10d = RegionND([0]*dims, [2]*dims)
    print(f"\n10D Region: dims={region10d.dims}, volume={region10d.volume()}")
    print(f"  (2^10 = {2**10})")
    
    # Show center and size work in any dimension
    center = region10d.center().tolist()
    size = region10d.size().tolist()
    print(f"  Center: [{', '.join(f'{c:.1f}' for c in center[:3])}...] (first 3 of {dims})")
    print(f"  Size: [{', '.join(f'{s:.1f}' for s in size[:3])}...] (first 3 of {dims})")


def demo_mixed_dimensions():
    """Demonstrate dimension safety."""
    print("\n\nDimension Safety Demo:")
    print("-" * 50)
    
    region2d = RegionND([0, 0], [10, 10])
    region3d = RegionND([0, 0, 0], [10, 10, 10])
    
    print(f"2D region: dims={region2d.dims}")
    print(f"3D region: dims={region3d.dims}")
    
    # This should raise an error
    try:
        region2d.contains(region3d)
    except ValueError as e:
        print(f"\nExpected error when comparing different dimensions:")
        print(f"  {e}")


def demo_operations():
    """Demonstrate geometric operations in N-D."""
    print("\n\nGeometric Operations Demo:")
    print("-" * 50)
    
    # 4D example
    dims = 4
    r1 = RegionND([0, 0, 0, 0], [6, 6, 6, 6])
    r2 = RegionND([3, 3, 3, 3], [9, 9, 9, 9])
    
    print(f"Region 1 (4D): volume={r1.volume()}")
    print(f"Region 2 (4D): volume={r2.volume()}")
    
    # Union
    union = r1.union(r2)
    print(f"\nUnion: volume={union.volume()}")
    print(f"  Min corner: {union.min_corner.tolist()}")
    print(f"  Max corner: {union.max_corner.tolist()}")
    
    # Intersection
    intersection = r1.intersection(r2)
    if intersection:
        print(f"\nIntersection: volume={intersection.volume()}")
        print(f"  Min corner: {intersection.min_corner.tolist()}")
        print(f"  Max corner: {intersection.max_corner.tolist()}")
    
    # Expansion
    expanded = r1.expand(1.5)
    print(f"\nExpanded by 1.5x: volume={expanded.volume()}")
    print(f"  Original volume * 1.5^4 = {r1.volume() * (1.5**4)}")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("RegionND: N-Dimensional Regions Demo")
    print("="*60)
    
    demo_2d()
    demo_3d()
    demo_high_dimensional()
    demo_mixed_dimensions()
    demo_operations()
    
    print("\n" + "="*60)
    print("Day 13 Complete: RegionND is now dimension-agnostic!")
    print("The visualization is broken, but the backend is more powerful than ever.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()