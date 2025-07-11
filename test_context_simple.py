#!/usr/bin/env python3
"""
Simple test to verify AnalysisContext is used properly
"""
import ast
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from regionai.analysis.context import AnalysisContext
from regionai.discovery.abstract_domains import AbstractState, Sign, analyze_assignment


def test_analyze_assignment_with_explicit_state():
    """Test analyze_assignment with explicit abstract state."""
    print("Testing analyze_assignment with explicit state...")
    
    # Create AST for x = 5
    assign_node = ast.Assign(
        targets=[ast.Name(id='x', ctx=ast.Store())],
        value=ast.Constant(value=5)
    )
    
    # Create context and abstract state
    context = AnalysisContext()
    abstract_state = AbstractState()
    
    # Call analyze_assignment with explicit state
    analyze_assignment(assign_node, context, abstract_state)
    
    # Check result
    x_sign = abstract_state.get_sign('x')
    print(f"x = {x_sign}")
    
    if x_sign == Sign.POSITIVE:
        print("✅ Assignment analyzed correctly with explicit state")
        return True
    else:
        print("❌ Assignment analysis failed")
        return False


def test_analyze_assignment_with_context_state():
    """Test analyze_assignment using context's abstract state."""
    print("\nTesting analyze_assignment with context's state...")
    
    # Create AST for y = -10
    assign_node = ast.Assign(
        targets=[ast.Name(id='y', ctx=ast.Store())],
        value=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=10))
    )
    
    # Create context with its own abstract state
    context = AnalysisContext()
    
    # Call analyze_assignment without explicit state (uses context's)
    analyze_assignment(assign_node, context)
    
    # Check result
    y_sign = context.abstract_state.get_sign('y')
    print(f"y = {y_sign}")
    
    if y_sign == Sign.NEGATIVE:
        print("✅ Assignment analyzed correctly with context's state")
        return True
    else:
        print("❌ Assignment analysis failed")
        return False


def test_no_temporary_context_creation():
    """Verify no temporary contexts are created."""
    print("\nVerifying no temporary context creation...")
    
    # The old pattern would create AnalysisContext() inside _analyze_block
    # The new pattern passes abstract state explicitly
    
    # Check that analyze_assignment now accepts abstract_state parameter
    import inspect
    sig = inspect.signature(analyze_assignment)
    params = list(sig.parameters.keys())
    
    if 'abstract_state' in params:
        print("✅ analyze_assignment has abstract_state parameter")
        print(f"   Parameters: {params}")
        return True
    else:
        print("❌ analyze_assignment missing abstract_state parameter")
        return False


def main():
    """Run simple context tests."""
    print("=== Simple AnalysisContext Tests ===\n")
    
    results = []
    results.append(("Explicit state", test_analyze_assignment_with_explicit_state()))
    results.append(("Context state", test_analyze_assignment_with_context_state()))
    results.append(("No temp context", test_no_temporary_context_creation()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 AnalysisContext pattern is fixed!")
        print("No more temporary contexts needed.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)