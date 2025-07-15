#!/usr/bin/env python3
"""
RegionAI Multi-Space Architecture Demo

Demonstrates the three-tier architecture with:
- Tier 1: Immutable kernel
- Tier 2: Domain modules  
- Tier 3: Epistemic workspaces

Shows workspace forking, module loading, and cross-space morphisms.
"""

import numpy as np
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tier1.kernel import Kernel
from tier2.module_hub import ModuleHub
from tier3.workspace import Workspace
from tier3.morphism import Morphism, LinearTransform, FunctionTransform


def demo_kernel_immutability():
    """Demo 1: Kernel immutability and versioning."""
    print("=== Demo 1: Kernel Immutability ===")
    
    # Create kernel with specific version
    kernel = Kernel(version="1.0.0")
    print(f"Kernel: {kernel}")
    print(f"Signature: {kernel.get_signature()}")
    print(f"Integrity: {kernel.verify_integrity()}")
    
    # Kernel behavior never changes for same version
    kernel2 = Kernel(version="1.0.0")
    print(f"Same version, same signature: {kernel.get_signature() == kernel2.get_signature()}")
    
    print()


def demo_module_loading():
    """Demo 2: Hot-swappable domain modules."""
    print("=== Demo 2: Module Loading ===")
    
    kernel = Kernel(version="1.0.0")
    hub = ModuleHub(kernel)
    
    # Load mathematics module
    print("Loading mathematics module...")
    math_bundle = hub.load_module("mathematics")
    print(f"Mathematics regions: {math_bundle.list_regions()}")
    
    # Load with overrides
    print("Loading with custom parameters...")
    custom_math = hub.load_module("mathematics", overrides={"positive_radius": 500.0})
    print(f"Custom math signature: {custom_math.get_signature()}")
    print(f"Different from default: {math_bundle.get_signature() != custom_math.get_signature()}")
    
    print()


def demo_workspace_isolation():
    """Demo 3: Workspace isolation and forking."""
    print("=== Demo 3: Workspace Isolation ===")
    
    kernel = Kernel(version="1.0.0")
    
    # Create base workspace
    base_ws = Workspace("base_reality", kernel)
    base_ws.load_module("mathematics")
    base_ws.set_preference("gravity", 9.81)
    
    print(f"Base workspace: {base_ws}")
    print(f"Base preferences: {base_ws.list_preferences()}")
    
    # Fork for Alice
    alice_ws = base_ws.fork("alice_prefs")
    alice_ws.set_preference("favorite_color", "blue")
    alice_ws.set_preference("gravity", 9.81)  # Same as base
    
    # Fork for fantasy world
    fantasy_ws = base_ws.fork("fantasy_world")
    fantasy_ws.set_preference("gravity", 2.0)  # Lower gravity
    fantasy_ws.set_preference("magic_exists", True)
    
    print(f"Alice workspace: {alice_ws}")
    print(f"Alice preferences: {alice_ws.list_preferences()}")
    print(f"Fantasy workspace: {fantasy_ws}")
    print(f"Fantasy preferences: {fantasy_ws.list_preferences()}")
    
    # Workspaces are isolated
    print(f"Base gravity: {base_ws.get_preference('gravity')}")
    print(f"Fantasy gravity: {fantasy_ws.get_preference('gravity')}")
    
    print()


def demo_cross_space_morphisms():
    """Demo 4: Cross-space morphisms."""
    print("=== Demo 4: Cross-Space Morphisms ===")
    
    kernel = Kernel(version="1.0.0")
    
    # Create two workspaces
    physics_ws = Workspace("physics", kernel)
    physics_ws.load_module("mathematics")
    
    magic_ws = Workspace("magic", kernel)
    magic_ws.load_module("mathematics")
    
    # Create a morphism from physics to magic
    # In magic world, distances are scaled by 0.5 (everything closer)
    magic_matrix = np.array([[0.5, 0.0], [0.0, 0.5]])
    magic_transform = LinearTransform(magic_matrix)
    
    morphism = Morphism("physics", "magic", magic_transform)
    physics_ws.morphism_registry.register(morphism)
    
    # Create a region in physics space
    physics_region = kernel.create_region(center=np.array([10.0, 20.0]), radius=5.0)
    print(f"Physics region: center={physics_region.center}, radius={physics_region.radius}")
    
    # Transform to magic space
    magic_region = morphism.apply(physics_region)
    print(f"Magic region: center={magic_region.center}, radius={magic_region.radius}")
    
    # Transform back
    back_to_physics = morphism.inverse(magic_region)
    print(f"Back to physics: center={back_to_physics.center}, radius={back_to_physics.radius}")
    
    print()


def demo_hypothesis_exploration():
    """Demo 5: Hypothesis exploration workflow."""
    print("=== Demo 5: Hypothesis Exploration ===")
    
    kernel = Kernel(version="1.0.0")
    
    # Create base scientific workspace
    science_ws = Workspace("science_base", kernel)
    science_ws.load_module("mathematics")
    science_ws.set_preference("speed_of_light", 299792458)  # m/s
    
    # Fork for testing different physics hypotheses
    hypothesis1 = science_ws.fork("variable_c_hypothesis")
    hypothesis1.set_module_override("mathematics", "speed_of_light_factor", 0.9)
    
    hypothesis2 = science_ws.fork("extra_dimensions")
    hypothesis2.set_module_override("mathematics", "dimensions", 11)
    
    # Each hypothesis can explore independently
    print(f"Base science: {science_ws.get_preference('speed_of_light')}")
    print(f"Hypothesis 1 overrides: {hypothesis1.module_overrides}")
    print(f"Hypothesis 2 overrides: {hypothesis2.module_overrides}")
    
    # Create snapshots for reproducibility
    snap1 = hypothesis1.create_snapshot()
    snap2 = hypothesis2.create_snapshot()
    
    print(f"Snapshot 1: {snap1.workspace_id[:8]}... at {snap1.timestamp}")
    print(f"Snapshot 2: {snap2.workspace_id[:8]}... at {snap2.timestamp}")
    
    print()


def demo_api_usage():
    """Demo 6: API usage as shown in design document."""
    print("=== Demo 6: API Usage ===")
    
    # Tier-1 Kernel (immutable)
    kernel = Kernel(version="1.0.0")
    print(f"Kernel version: {kernel.version}")
    
    # Tier-2 Module Management
    hub = ModuleHub(kernel=kernel)
    math_bundle = hub.load_module("mathematics")
    print(f"Loaded mathematics bundle: {math_bundle.metadata.name}")
    
    # Tier-3 Workspace API
    ws = Workspace("demo_workspace", kernel=kernel)
    ws.load_module("mathematics")
    print(f"Workspace loaded modules: {ws.list_loaded_modules()}")
    
    # Forking
    alice = ws.fork("alice_prefs")
    alice.set_preference("favorite_number", 42)
    print(f"Alice's favorite number: {alice.get_preference('favorite_number')}")
    
    # Morphism registration
    identity_transform = LinearTransform(np.eye(2))
    morphism = Morphism("demo_workspace", "alice_prefs", identity_transform)
    signature = ws.morphism_registry.register(morphism)
    print(f"Registered morphism: {signature}")
    
    print()


def main():
    """Run all demonstrations."""
    print("RegionAI Multi-Space Architecture Demo")
    print("=" * 50)
    
    try:
        demo_kernel_immutability()
        demo_module_loading()
        demo_workspace_isolation()
        demo_cross_space_morphisms()
        demo_hypothesis_exploration()
        demo_api_usage()
        
        print("All demos completed successfully!")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()