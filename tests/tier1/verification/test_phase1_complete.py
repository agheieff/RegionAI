#!/usr/bin/env python3
"""
Test to verify Phase 1 (Foundation Fixes) is complete.
Tests both critical fixes from Phase 1:
1. Interprocedural null dereference detection
2. AnalysisContext refactoring (no global state)
"""
import ast
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.regionai.analysis.interprocedural import InterproceduralAnalyzer
from src.regionai.analysis.context import AnalysisContext
from src.regionai.discovery import ast_primitives

def test_interprocedural_null_detection():
    """Test that interprocedural null detection works correctly."""
    print("Testing interprocedural null detection...")
    
    code = """
def get_data():
    return None

def process():
    data = get_data()
    result = data.value  # Should detect null pointer error here!
    return result
"""
    
    tree = ast.parse(code)
    analyzer = InterproceduralAnalyzer()
    result = analyzer.analyze_program(tree)
    
    # Check for null pointer error
    if result.errors:
        print(f"✅ Found {len(result.errors)} errors: {result.errors}")
        return True
    else:
        print("❌ No errors found - interprocedural null detection not working")
        return False

def test_analysis_context_refactoring():
    """Test that AnalysisContext is properly integrated."""
    print("\nTesting AnalysisContext refactoring...")
    
    # Create context
    context = AnalysisContext()
    
    # Test that it has the required variable_state_map
    if not hasattr(context, 'variable_state_map'):
        print("❌ AnalysisContext missing variable_state_map")
        return False
    
    # Test constant propagation with context
    code = """
x = 5
y = x + 10
"""
    tree = ast.parse(code)
    
    # Test that propagate_constants accepts context
    try:
        ast_primitives.propagate_constants(tree, [context])
        print("✅ propagate_constants accepts AnalysisContext")
    except Exception as e:
        print(f"❌ propagate_constants failed: {e}")
        return False
    
    # Verify no ConstantPropagationContext exists
    if hasattr(ast_primitives, 'ConstantPropagationContext'):
        print("❌ ConstantPropagationContext still exists")
        return False
    else:
        print("✅ ConstantPropagationContext successfully removed")
    
    return True

def test_no_global_state():
    """Test that global state has been eliminated."""
    print("\nTesting global state elimination...")
    
    # Check ast_primitives for global state
    ast_primitives_source = open('src/regionai/discovery/ast_primitives.py').read()
    
    # These should not exist
    forbidden_patterns = [
        '_abstract_state =',
        '_state_map =',
        'global _abstract_state',
        'global _state_map',
        'reset_state_map()',
        'class ConstantPropagationContext'
    ]
    
    found_globals = []
    for pattern in forbidden_patterns:
        if pattern in ast_primitives_source:
            found_globals.append(pattern)
    
    if found_globals:
        print(f"❌ Found global state patterns: {found_globals}")
        return False
    else:
        print("✅ No global state found in ast_primitives.py")
        return True

def main():
    """Run all Phase 1 verification tests."""
    print("=== Phase 1 Verification Suite ===\n")
    
    results = []
    
    # Test 1: Interprocedural null detection
    results.append(("Interprocedural null detection", test_interprocedural_null_detection()))
    
    # Test 2: AnalysisContext refactoring
    results.append(("AnalysisContext refactoring", test_analysis_context_refactoring()))
    
    # Test 3: Global state elimination
    results.append(("Global state elimination", test_no_global_state()))
    
    # Summary
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Phase 1 is COMPLETE! All foundation fixes verified.")
        print("Ready for Phase 2: Enhanced Analysis Features")
    else:
        print("\n⚠️  Phase 1 is NOT complete. Fix failing tests before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)