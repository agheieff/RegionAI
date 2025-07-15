#!/usr/bin/env python3
"""
Simple RegionAI Multi-Space Architecture Demo

A minimal demonstration of the three-tier architecture without
external dependencies.
"""

import numpy as np
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Simple mock region for demo purposes
class MockRegion:
    def __init__(self, center, radius):
        self.center = np.array(center)
        self.radius = radius
    
    def __str__(self):
        return f"Region(center={self.center}, radius={self.radius})"

# Mock the kernel components for demo
class MockKernel:
    def __init__(self, version="1.0.0"):
        self.version = version
        self.signature = f"mock_{version}_abcd1234"
    
    def create_region(self, center, radius, **kwargs):
        return MockRegion(center, radius)
    
    def get_signature(self):
        return self.signature
    
    def verify_integrity(self):
        return True
    
    def __str__(self):
        return f"MockKernel v{self.version}"

# Simple module bundle
class MockModuleBundle:
    def __init__(self, name, regions):
        self.name = name
        self.regions = regions
        self.signature = f"{name}_bundle_{hash(str(regions))}"
    
    def list_regions(self):
        return list(self.regions.keys())
    
    def get_signature(self):
        return self.signature

# Simple workspace
class MockWorkspace:
    def __init__(self, name, kernel):
        self.name = name
        self.kernel = kernel
        self.preferences = {}
        self.loaded_modules = {}
        self.id = f"ws_{hash(name)}"
    
    def set_preference(self, key, value):
        self.preferences[key] = value
    
    def get_preference(self, key, default=None):
        return self.preferences.get(key, default)
    
    def list_preferences(self):
        return dict(self.preferences)
    
    def fork(self, name):
        child = MockWorkspace(name, self.kernel)
        child.preferences = dict(self.preferences)
        return child
    
    def load_module(self, name):
        if name == "mathematics":
            regions = {
                "positive_number": self.kernel.create_region([1.0], 1000.0),
                "negative_number": self.kernel.create_region([-1.0], 1000.0),
                "zero": self.kernel.create_region([0.0], 1e-10)
            }
            bundle = MockModuleBundle(name, regions)
            self.loaded_modules[name] = bundle
            return bundle
        return None
    
    def __str__(self):
        return f"MockWorkspace({self.name})"

def demo_kernel_immutability():
    """Demo 1: Kernel immutability and versioning."""
    print("=== Demo 1: Kernel Immutability ===")
    
    kernel = MockKernel(version="1.0.0")
    print(f"Kernel: {kernel}")
    print(f"Signature: {kernel.get_signature()}")
    print(f"Integrity: {kernel.verify_integrity()}")
    
    kernel2 = MockKernel(version="1.0.0")
    print(f"Same version, same signature: {kernel.get_signature() == kernel2.get_signature()}")
    print()

def demo_workspace_isolation():
    """Demo 2: Workspace isolation and forking."""
    print("=== Demo 2: Workspace Isolation ===")
    
    kernel = MockKernel(version="1.0.0")
    
    # Create base workspace
    base_ws = MockWorkspace("base_reality", kernel)
    base_ws.load_module("mathematics")
    base_ws.set_preference("gravity", 9.81)
    
    print(f"Base workspace: {base_ws}")
    print(f"Base preferences: {base_ws.list_preferences()}")
    
    # Fork for Alice
    alice_ws = base_ws.fork("alice_prefs")
    alice_ws.set_preference("favorite_color", "blue")
    
    # Fork for fantasy world
    fantasy_ws = base_ws.fork("fantasy_world")
    fantasy_ws.set_preference("gravity", 2.0)
    fantasy_ws.set_preference("magic_exists", True)
    
    print(f"Alice workspace: {alice_ws}")
    print(f"Alice preferences: {alice_ws.list_preferences()}")
    print(f"Fantasy workspace: {fantasy_ws}")
    print(f"Fantasy preferences: {fantasy_ws.list_preferences()}")
    
    print(f"Base gravity: {base_ws.get_preference('gravity')}")
    print(f"Fantasy gravity: {fantasy_ws.get_preference('gravity')}")
    print()

def demo_module_loading():
    """Demo 3: Module loading."""
    print("=== Demo 3: Module Loading ===")
    
    kernel = MockKernel(version="1.0.0")
    ws = MockWorkspace("test", kernel)
    
    print("Loading mathematics module...")
    math_bundle = ws.load_module("mathematics")
    print(f"Mathematics regions: {math_bundle.list_regions()}")
    
    for region_name in math_bundle.list_regions():
        region = math_bundle.regions[region_name]
        print(f"  {region_name}: {region}")
    print()

def demo_multi_space_concept():
    """Demo 4: Multi-space concept illustration."""
    print("=== Demo 4: Multi-Space Concept ===")
    
    kernel = MockKernel(version="1.0.0")
    
    # Create different spaces for different domains
    physics_ws = MockWorkspace("physics", kernel)
    physics_ws.set_preference("speed_of_light", 299792458)
    physics_ws.set_preference("planck_constant", 6.626e-34)
    
    fantasy_ws = MockWorkspace("fantasy", kernel)
    fantasy_ws.set_preference("magic_constant", 42)
    fantasy_ws.set_preference("dragon_scale_factor", 1.5)
    
    alice_ws = MockWorkspace("alice_personal", kernel)
    alice_ws.set_preference("favorite_color", "blue")
    alice_ws.set_preference("coffee_preference", "dark_roast")
    
    workspaces = [physics_ws, fantasy_ws, alice_ws]
    
    print("Created three isolated epistemic spaces:")
    for ws in workspaces:
        print(f"  {ws.name}: {list(ws.preferences.keys())}")
    
    print("\nEach space can have different 'physics' without conflict:")
    print(f"  Physics speed of light: {physics_ws.get_preference('speed_of_light')}")
    print(f"  Fantasy magic constant: {fantasy_ws.get_preference('magic_constant')}")
    print(f"  Alice's coffee preference: {alice_ws.get_preference('coffee_preference')}")
    print()

def main():
    """Run all demonstrations."""
    print("RegionAI Multi-Space Architecture Demo (Simplified)")
    print("=" * 55)
    
    demo_kernel_immutability()
    demo_workspace_isolation()
    demo_module_loading()
    demo_multi_space_concept()
    
    print("Key Benefits of Multi-Space Architecture:")
    print("1. Inconsistent Ontologies: Fantasy physics vs real physics isolated")
    print("2. Preference Fragmentation: Each user gets their own preference space")
    print("3. Hypothesis Exploration: Multiple scientific theories can coexist")
    print("4. Kernel Immutability: Core logic never changes, ensuring stability")
    print("5. Hot-Swappable Modules: Domain knowledge can be loaded/unloaded")
    print("\nDemo completed successfully!")

if __name__ == "__main__":
    main()