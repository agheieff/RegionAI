#!/usr/bin/env python3
"""
Test that our refactoring maintained system integrity.
"""
import sys
sys.path.insert(0, '.')

def test_abstract_domains():
    """Test abstract domain functionality."""
    print("=== Testing Abstract Domains ===")
    
    from src.regionai.discovery import Sign, sign_add, sign_multiply
    
    # Test sign operations
    assert sign_add(Sign.POSITIVE, Sign.POSITIVE) == Sign.POSITIVE
    assert sign_add(Sign.POSITIVE, Sign.NEGATIVE) == Sign.TOP
    assert sign_multiply(Sign.NEGATIVE, Sign.NEGATIVE) == Sign.POSITIVE
    print("✓ Sign domain operations work correctly")
    
    # Test new base class features
    assert Sign.POSITIVE.join(Sign.NEGATIVE) == Sign.TOP
    assert Sign.POSITIVE.meet(Sign.POSITIVE) == Sign.POSITIVE
    assert Sign.BOTTOM <= Sign.POSITIVE <= Sign.TOP
    print("✓ Abstract domain base class methods work")
    
    from src.regionai.discovery import Nullability
    assert Nullability.NOT_NULL.join(Nullability.DEFINITELY_NULL) == Nullability.NULLABLE
    print("✓ Nullability domain works")
    
    from src.regionai.discovery import Range, check_array_bounds
    r = Range(0, 10)
    assert r.contains(5)
    assert not r.contains(15)
    assert check_array_bounds(r, 20) == ""  # Safe
    print("✓ Range domain works")
    
    return True


def test_discovery_engine():
    """Test discovery engine basics."""
    print("\n=== Testing Discovery Engine ===")
    
    from src.regionai.discovery import DiscoveryEngine
    from src.regionai.data import Problem
    
    engine = DiscoveryEngine()
    print("✓ Discovery engine instantiates")
    
    # Test strategy access
    assert 'sequential' in engine.engine.strategies
    assert 'conditional' in engine.engine.strategies
    assert 'iterative' in engine.engine.strategies
    print("✓ All discovery strategies available")
    
    return True


def test_curriculum_factory():
    """Test curriculum factory."""
    print("\n=== Testing Curriculum Factory ===")
    
    from src.regionai.data import create_curriculum, list_curricula
    
    curricula = list_curricula()
    assert len(curricula) > 0
    print(f"✓ {len(curricula)} curriculum types available")
    
    # Test generation
    problems = create_curriculum('transformation', difficulty='basic')
    assert len(problems) > 0
    print("✓ Can generate transformation curriculum")
    
    problems = create_curriculum('sign_analysis', difficulty='basic')
    assert len(problems) > 0
    print("✓ Can generate sign analysis curriculum")
    
    return True


def test_backward_compatibility():
    """Test backward compatibility."""
    print("\n=== Testing Backward Compatibility ===")
    
    # Test old discovery function
    from src.regionai.discovery import discover_concept_from_failures
    assert callable(discover_concept_from_failures)
    print("✓ Legacy discovery function available")
    
    # Test old curriculum imports
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from src.regionai.data import SignAnalysisCurriculumGenerator
        gen = SignAnalysisCurriculumGenerator()
        problems = gen.generate_basic_sign_curriculum()
        assert len(problems) > 0
    print("✓ Legacy curriculum generators work")
    
    return True


def main():
    """Run all integrity tests."""
    print("RegionAI Refactoring Integrity Tests")
    print("=" * 50)
    
    tests = [
        ("Abstract Domains", test_abstract_domains),
        ("Discovery Engine", test_discovery_engine),
        ("Curriculum Factory", test_curriculum_factory),
        ("Backward Compatibility", test_backward_compatibility)
    ]
    
    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"Summary: {passed}/{len(tests)} integrity tests passed")
    
    if passed == len(tests):
        print("\n✅ All refactoring maintained system integrity!")
        print("The core functionality works exactly as before.")
    else:
        print("\n⚠️  Some tests failed - investigation needed")


if __name__ == "__main__":
    main()