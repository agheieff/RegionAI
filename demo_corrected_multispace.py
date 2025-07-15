#!/usr/bin/env python3
"""
RegionAI Corrected Multi-Space Architecture Demo

Demonstrates the properly structured three-tier architecture:
- Tier 1: Universal reasoning engine (brains, region algebra, discovery)
- Tier 2: Domain knowledge modules (physics, chemistry, mathematics, etc.)
- Tier 3: Situational overlays (user contexts, world contexts, scenarios)
"""

import sys
from pathlib import Path

# Add tier directories to Python path
sys.path.insert(0, str(Path(__file__).parent))

def demo_tier1_universal_reasoning():
    """Demo 1: Universal reasoning engine (Tier 1)"""
    print("=== Demo 1: Universal Reasoning Engine (Tier 1) ===")
    
    # Mock the universal reasoning kernel
    class MockUniversalKernel:
        def __init__(self):
            self.version = "1.0.0"
            self.brains = ["bayesian", "logic", "utility", "observer", "temporal", "sensorimotor"]
            self.signature = "mock_universal_kernel_abcd1234"
        
        def reason(self, problem, domain_knowledge=None):
            return {
                "result": f"Universal reasoning applied to: {problem}",
                "brains_used": self.brains,
                "domain_knowledge_used": domain_knowledge is not None
            }
    
    kernel = MockUniversalKernel()
    print(f"Universal Reasoning Kernel v{kernel.version}")
    print(f"Available brains: {kernel.brains}")
    print(f"Signature: {kernel.signature}")
    
    # Test universal reasoning
    problem = "How to optimize energy usage?"
    result = kernel.reason(problem)
    print(f"Problem: {problem}")
    print(f"Result: {result['result']}")
    print(f"Brains used: {result['brains_used']}")
    print()

def demo_tier2_domain_knowledge():
    """Demo 2: Domain knowledge modules (Tier 2)"""
    print("=== Demo 2: Domain Knowledge Modules (Tier 2) ===")
    
    # Mock domain knowledge modules
    class MockDomainHub:
        def __init__(self):
            self.domains = {
                "physics": {
                    "concepts": ["energy", "momentum", "force", "thermodynamics"],
                    "laws": ["conservation_of_energy", "newtons_laws"],
                    "constants": {"c": 299792458, "G": 6.67430e-11}
                },
                "chemistry": {
                    "concepts": ["atoms", "molecules", "reactions", "bonds"],
                    "laws": ["conservation_of_mass", "periodic_law"],
                    "constants": {"avogadro": 6.022e23}
                },
                "mathematics": {
                    "concepts": ["algebra", "calculus", "statistics", "geometry"],
                    "theorems": ["pythagorean", "fundamental_theorem_calculus"],
                    "constants": {"pi": 3.14159, "e": 2.71828}
                }
            }
        
        def get_domain_knowledge(self, domain_name):
            return self.domains.get(domain_name, {})
        
        def query_concept(self, domain_name, concept_name):
            domain = self.domains.get(domain_name, {})
            return domain.get("concepts", []).count(concept_name) > 0
    
    hub = MockDomainHub()
    print("Available domain modules:")
    for domain_name, knowledge in hub.domains.items():
        print(f"  {domain_name}: {len(knowledge.get('concepts', []))} concepts")
    
    # Query domain knowledge
    print("\nQuerying domain knowledge:")
    print(f"Physics has 'energy' concept: {hub.query_concept('physics', 'energy')}")
    print(f"Chemistry has 'reactions' concept: {hub.query_concept('chemistry', 'reactions')}")
    print(f"Mathematics constants: {hub.get_domain_knowledge('mathematics').get('constants', {})}")
    print()

def demo_tier3_situational_overlays():
    """Demo 3: Situational overlays (Tier 3)"""
    print("=== Demo 3: Situational Overlays (Tier 3) ===")
    
    # Mock situational overlays
    class MockSituationManager:
        def __init__(self):
            self.overlays = {}
            self.active_overlays = []
        
        def create_user_context(self, name, preferences=None):
            overlay_id = f"user_{name}"
            self.overlays[overlay_id] = {
                "type": "user_context",
                "name": name,
                "preferences": preferences or {}
            }
            return overlay_id
        
        def create_world_context(self, name, world_params=None):
            overlay_id = f"world_{name}"
            self.overlays[overlay_id] = {
                "type": "world_context",
                "name": name,
                "parameters": world_params or {}
            }
            return overlay_id
        
        def create_scenario(self, name, scenario_type, params=None):
            overlay_id = f"scenario_{name}"
            self.overlays[overlay_id] = {
                "type": "scenario",
                "name": name,
                "scenario_type": scenario_type,
                "parameters": params or {}
            }
            return overlay_id
        
        def activate_overlay(self, overlay_id):
            if overlay_id not in self.active_overlays:
                self.active_overlays.append(overlay_id)
        
        def list_overlays(self):
            return [
                {
                    "id": overlay_id,
                    "active": overlay_id in self.active_overlays,
                    **overlay_data
                }
                for overlay_id, overlay_data in self.overlays.items()
            ]
    
    manager = MockSituationManager()
    
    # Create different types of overlays
    alice_id = manager.create_user_context("alice", {"favorite_color": "blue", "risk_tolerance": "low"})
    physics_world_id = manager.create_world_context("physics_world", {"gravity": 9.81, "friction": 0.1})
    fantasy_world_id = manager.create_world_context("fantasy_world", {"gravity": 2.0, "magic": True})
    embodied_scenario_id = manager.create_scenario("robot_task", "embodiment", {"robot_type": "humanoid"})
    
    # Activate some overlays
    manager.activate_overlay(alice_id)
    manager.activate_overlay(physics_world_id)
    manager.activate_overlay(embodied_scenario_id)
    
    print("Created situational overlays:")
    for overlay in manager.list_overlays():
        status = "ACTIVE" if overlay["active"] else "inactive"
        print(f"  {overlay['name']} ({overlay['type']}) - {status}")
    
    print()

def demo_integrated_reasoning():
    """Demo 4: Integrated reasoning across all tiers"""
    print("=== Demo 4: Integrated Multi-Tier Reasoning ===")
    
    # Mock integrated system
    class MockIntegratedSystem:
        def __init__(self):
            self.universal_kernel = self._create_kernel()
            self.domain_hub = self._create_domain_hub()
            self.situation_manager = self._create_situation_manager()
        
        def _create_kernel(self):
            return {"version": "1.0.0", "brains": ["bayesian", "logic", "utility", "observer", "temporal", "sensorimotor"]}
        
        def _create_domain_hub(self):
            return {"physics": {"gravity": 9.81}, "chemistry": {"ph_neutral": 7.0}, "mathematics": {"pi": 3.14159}}
        
        def _create_situation_manager(self):
            return {"active_overlays": ["alice_preferences", "physics_world", "embodied_scenario"]}
        
        def solve_problem(self, problem):
            # Simulate integrated reasoning
            return {
                "problem": problem,
                "tier1_reasoning": f"Universal reasoning applied with {len(self.universal_kernel['brains'])} brains",
                "tier2_knowledge": f"Used knowledge from {len(self.domain_hub)} domains",
                "tier3_context": f"Applied {len(self.situation_manager['active_overlays'])} situational overlays",
                "solution": f"Integrated solution for: {problem}"
            }
    
    system = MockIntegratedSystem()
    
    # Test integrated reasoning
    problem = "How should Alice's robot navigate a physical environment?"
    result = system.solve_problem(problem)
    
    print(f"Problem: {result['problem']}")
    print(f"Tier 1 (Universal): {result['tier1_reasoning']}")
    print(f"Tier 2 (Domain): {result['tier2_knowledge']}")
    print(f"Tier 3 (Situational): {result['tier3_context']}")
    print(f"Solution: {result['solution']}")
    print()

def main():
    """Run all demonstrations of the corrected architecture."""
    print("RegionAI Corrected Multi-Space Architecture Demo")
    print("=" * 55)
    print()
    
    demo_tier1_universal_reasoning()
    demo_tier2_domain_knowledge()
    demo_tier3_situational_overlays()
    demo_integrated_reasoning()
    
    print("Architecture Summary:")
    print("- Tier 1: Universal reasoning engine (brains, region algebra, discovery)")
    print("- Tier 2: Domain knowledge modules (physics, chemistry, mathematics, etc.)")
    print("- Tier 3: Situational overlays (user contexts, world contexts, scenarios)")
    print()
    print("Key Benefits:")
    print("1. Universal reasoning works across all domains")
    print("2. Domain knowledge is modular and specialized")
    print("3. Situational overlays provide context without changing core systems")
    print("4. Clean separation of concerns enables scalability")
    print("5. Each tier can be developed and tested independently")
    print()
    print("Demo completed successfully!")

if __name__ == "__main__":
    main()