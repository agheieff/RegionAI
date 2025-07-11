#!/usr/bin/env python3
"""
Test suite to verify the refactored analysis code using AnalysisContext.
"""
import sys
import os
import ast

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.analysis.context import AnalysisContext, RegionAIConfig
from regionai.analysis.fixpoint import analyze_with_fixpoint
from regionai.discovery.abstract_domains import (
    Sign, Nullability, analyze_sign, check_null_dereference,
    prove_property, analyze_assignment
)


def test_analysis_context_creation():
    """Test creating and using an AnalysisContext."""
    print("Testing AnalysisContext creation...")
    
    context = AnalysisContext()
    
    # Test basic state operations
    context.abstract_state.update_sign('x', Sign.POSITIVE)
    context.abstract_state.update_nullability('ptr', Nullability.NOT_NULL)
    
    assert context.abstract_state.get_sign('x') == Sign.POSITIVE
    assert context.abstract_state.get_nullability('ptr') == Nullability.NOT_NULL
    
    # Test error/warning tracking
    context.add_error("Test error")
    context.add_warning("Test warning")
    
    assert len(context.errors) == 1
    assert len(context.warnings) == 1
    
    # Test reset
    context.reset()
    assert context.abstract_state.get_sign('x') is None
    assert len(context.errors) == 0
    
    print("✓ AnalysisContext works correctly")


def test_analyze_sign_with_context():
    """Test the refactored analyze_sign function with context."""
    print("\nTesting analyze_sign with context...")
    
    context = AnalysisContext()
    
    # Test constant
    node = ast.parse("5").body[0].value
    sign = analyze_sign(node, context)
    assert sign == Sign.POSITIVE
    
    # Test variable lookup
    context.abstract_state.update_sign('x', Sign.NEGATIVE)
    node = ast.parse("x").body[0].value
    sign = analyze_sign(node, context)
    assert sign == Sign.NEGATIVE
    
    # Test negation
    node = ast.parse("-5").body[0].value
    sign = analyze_sign(node, context)
    assert sign == Sign.NEGATIVE
    
    print("✓ analyze_sign with context works correctly")


def test_check_null_dereference_with_context():
    """Test null dereference checking with context."""
    print("\nTesting null dereference checking with context...")
    
    context = AnalysisContext()
    
    # Set up some nullability states
    context.abstract_state.update_nullability('ptr', Nullability.DEFINITELY_NULL)
    context.abstract_state.update_nullability('maybe_null', Nullability.NULLABLE)
    context.abstract_state.update_nullability('safe', Nullability.NOT_NULL)
    
    # Test definitely null access
    code = "ptr.field"
    tree = ast.parse(code)
    errors = check_null_dereference(tree, context)
    assert len(errors) > 0
    assert "Null pointer exception" in errors[0]
    
    # Test nullable access
    code = "maybe_null.field"
    tree = ast.parse(code)
    errors = check_null_dereference(tree, context)
    assert len(errors) > 0
    assert "Potential null pointer" in errors[0]
    
    # Test safe access
    code = "safe.field"
    tree = ast.parse(code)
    errors = check_null_dereference(tree, context)
    assert len(errors) == 0
    
    print("✓ Null dereference checking with context works correctly")


def test_prove_property_with_context():
    """Test property proving with context."""
    print("\nTesting prove_property with context...")
    
    context = AnalysisContext()
    
    code = """
x = 5
y = -x
z = x + y
"""
    tree = ast.parse(code)
    
    initial_state = {}
    result = prove_property(tree, initial_state, context)
    
    # x should be positive (5)
    assert 'x' in result
    assert result['x'] == True  # Has definite sign
    
    # y should be negative (-5)
    assert 'y' in result
    assert result['y'] == True  # Has definite sign
    
    # z should be TOP (5 + -5 could be any value in abstract interpretation)
    # The abstract domain conservatively approximates POSITIVE + NEGATIVE as TOP
    assert 'z' in result
    assert result['z'] == False  # Has TOP sign (not a definite sign)
    
    print("✓ prove_property with context works correctly")


def test_analyze_assignment_with_context():
    """Test the new analyze_assignment function."""
    print("\nTesting analyze_assignment with context...")
    
    context = AnalysisContext()
    
    # Test sign assignment
    code = "x = 10"
    node = ast.parse(code).body[0]
    analyze_assignment(node, context)
    
    assert context.abstract_state.get_sign('x') == Sign.POSITIVE
    assert context.abstract_state.get_nullability('x') == Nullability.NOT_NULL
    
    # Test null assignment
    code = "ptr = None"
    node = ast.parse(code).body[0]
    analyze_assignment(node, context)
    
    assert context.abstract_state.get_nullability('ptr') == Nullability.DEFINITELY_NULL
    
    print("✓ analyze_assignment with context works correctly")


def test_fixpoint_analysis_with_context():
    """Test fixpoint analysis with context."""
    print("\nTesting fixpoint analysis with context...")
    
    code = """
x = 10
while x > 0:
    x = x - 1
"""
    tree = ast.parse(code)
    
    context = AnalysisContext()
    result = analyze_with_fixpoint(tree, context=context)
    
    assert 'final_state' in result
    assert 'cfg' in result
    assert 'loops' in result
    assert result['context'] is context
    
    # Check that we got some analysis results
    final_state = result['final_state']
    if final_state:
        # x should have been analyzed
        x_sign = final_state.get_sign('x')
        assert x_sign is not None
    
    print("✓ Fixpoint analysis with context works correctly")


def test_config_usage():
    """Test using RegionAIConfig in context."""
    print("\nTesting RegionAIConfig usage...")
    
    config = RegionAIConfig(
        widening_threshold=5,
        max_fixpoint_iterations=50,
        enable_path_sensitivity=True
    )
    
    context = AnalysisContext(config=config)
    
    assert context.config.widening_threshold == 5
    assert context.config.max_fixpoint_iterations == 50
    assert context.config.enable_path_sensitivity == True
    
    print("✓ RegionAIConfig works correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Context Refactoring Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_analysis_context_creation,
        test_analyze_sign_with_context,
        test_check_null_dereference_with_context,
        test_prove_property_with_context,
        test_analyze_assignment_with_context,
        test_fixpoint_analysis_with_context,
        test_config_usage
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print(f"\n✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)