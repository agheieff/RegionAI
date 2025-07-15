#!/usr/bin/env python3
"""
Basic architecture test to verify the new tier structure works.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tier1_config():
    """Test that tier1 config imports work."""
    try:
        from tier1 import RegionAIConfig
        config = RegionAIConfig()
        print(f"✓ Tier1 config works: {config}")
        return True
    except Exception as e:
        print(f"✗ Tier1 config failed: {e}")
        return False

def test_tier2_domain_system():
    """Test that tier2 domain system works."""
    try:
        from tier2.domain_hub import DomainHub
        from tier2.domain_module import DomainModule
        
        hub = DomainHub()
        available_domains = hub.list_available_domains()
        print(f"✓ Tier2 domain system works: {len(available_domains)} domains available")
        print(f"  Available domains: {available_domains}")
        return True
    except Exception as e:
        print(f"✗ Tier2 domain system failed: {e}")
        return False

def test_tier3_situation_system():
    """Test that tier3 situation system works."""
    try:
        from tier3.situation_manager import SituationManager
        from tier3.overlay import SituationalOverlay
        
        manager = SituationManager()
        alice_id = manager.create_user_context("alice", {"favorite_color": "blue"})
        overlays = manager.list_overlays()
        print(f"✓ Tier3 situation system works: {len(overlays)} overlays created")
        print(f"  Created overlay: {overlays[0]['name']}")
        return True
    except Exception as e:
        print(f"✗ Tier3 situation system failed: {e}")
        return False

def test_legacy_compatibility():
    """Test that legacy compatibility shim works."""
    try:
        # Suppress the deprecation warning output for cleaner test results
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        from src.regionai import RegionAIConfig, SituationManager, DomainModule
        print(f"✓ Legacy compatibility works: RegionAIConfig={RegionAIConfig is not None}")
        print(f"  SituationManager={SituationManager is not None}")
        print(f"  DomainModule={DomainModule is not None}")
        return True
    except Exception as e:
        print(f"✗ Legacy compatibility failed: {e}")
        return False

def main():
    """Run all basic architecture tests."""
    print("Testing RegionAI Three-Tier Architecture")
    print("=" * 50)
    
    results = []
    results.append(test_tier1_config())
    results.append(test_tier2_domain_system())
    results.append(test_tier3_situation_system())
    results.append(test_legacy_compatibility())
    
    print("\n" + "=" * 50)
    success_count = sum(results)
    total_count = len(results)
    print(f"Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All basic architecture tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Architecture needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())