#!/usr/bin/env python3
"""
Direct test of path sensitivity implementation
"""
import ast
import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Add the root directory to path for tier imports

# Import only what we need directly
from regionai.analysis.fixpoint import PathSensitiveFixpointAnalyzer, AnalysisState, PathConstraint
from regionai.analysis.cfg import build_cfg, BlockType
from regionai.domains.code.analysis.context import AnalysisContext
from regionai.core.abstract_domains import AbstractState, Sign


def test_path_constraint_creation():
    """Test that path constraints are created correctly."""
    print("Testing PathConstraint creation...")
    
    # Create a simple condition: x > 0
    condition = ast.Compare(
        left=ast.Name(id='x', ctx=ast.Load()),
        ops=[ast.Gt()],
        comparators=[ast.Constant(value=0)]
    )
    
    # Create constraints
    true_constraint = PathConstraint(condition, True)
    false_constraint = PathConstraint(condition, False)
    
    print(f"True constraint: {true_constraint}")
    print(f"False constraint: {false_constraint}")
    
    # Test equality
    another_true = PathConstraint(condition, True)
    assert true_constraint == another_true, "Equal constraints should be equal"
    assert true_constraint != false_constraint, "Different constraints should not be equal"
    
    print("✅ PathConstraint creation works")
    return True


def test_cfg_with_conditions():
    """Test that CFG correctly stores branch conditions."""
    print("\nTesting CFG with branch conditions...")
    
    code = """
if x > 5:
    y = 1
else:
    y = -1
"""
    
    tree = ast.parse(code)
    cfg = build_cfg(tree)
    
    # Find the conditional block
    conditional_block = None
    for block in cfg.blocks.values():
        if block.type == BlockType.CONDITIONAL or block.branch_condition is not None:
            conditional_block = block
            break
    
    if conditional_block:
        print(f"✅ Found conditional block {conditional_block.id}")
        print(f"  Branch condition: {ast.dump(conditional_block.branch_condition)}")
        print(f"  Successors: {conditional_block.successors}")
        print(f"  Successor conditions: {len(conditional_block.successor_conditions)}")
        
        for succ_id, (cond, is_true) in conditional_block.successor_conditions.items():
            print(f"    Successor {succ_id}: {'true' if is_true else 'false'} branch")
        
        return True
    else:
        print("❌ No conditional block found")
        return False


def test_state_forking():
    """Test that states are properly forked at branches."""
    print("\nTesting state forking...")
    
    # Create a simple state
    initial = AnalysisState(
        abstract_state=AbstractState(),
        iteration_count=0,
        path_constraints=[]
    )
    initial.abstract_state.set_sign('x', Sign.TOP)
    
    # Create a condition
    condition = ast.Compare(
        left=ast.Name(id='x', ctx=ast.Load()),
        ops=[ast.Gt()],
        comparators=[ast.Constant(value=0)]
    )
    
    # Fork the state
    true_branch = initial.copy()
    true_branch.path_constraints.append(PathConstraint(condition, True))
    
    false_branch = initial.copy()
    false_branch.path_constraints.append(PathConstraint(condition, False))
    
    # Check that they're different
    assert len(true_branch.path_constraints) == 1
    assert len(false_branch.path_constraints) == 1
    assert true_branch.path_constraints[0].is_true == True
    assert false_branch.path_constraints[0].is_true == False
    
    print("✅ State forking works correctly")
    return True


def test_constraint_application():
    """Test applying constraints to refine abstract values."""
    print("\nTesting constraint application...")
    
    # Create analyzer with a simple CFG
    code = "x = 1"  # dummy code
    tree = ast.parse(code)
    cfg = build_cfg(tree)
    context = AnalysisContext()
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    # Create a state with x = TOP
    state = AnalysisState(
        abstract_state=AbstractState(),
        iteration_count=0,
        path_constraints=[]
    )
    state.abstract_state.set_sign('x', Sign.TOP)
    
    # Create constraint x > 5
    constraint = PathConstraint(
        ast.Compare(
            left=ast.Name(id='x', ctx=ast.Load()),
            ops=[ast.Gt()],
            comparators=[ast.Constant(value=5)]
        ),
        True
    )
    
    # Apply the constraint
    refined_state = analyzer._apply_path_constraint(state, constraint)
    
    # Check that x is refined to positive
    x_sign = refined_state.abstract_state.get_sign('x')
    print(f"After applying x > 5: x is {x_sign}")
    
    if x_sign == Sign.POSITIVE:
        print("✅ Constraint correctly refined x to POSITIVE")
        return True
    else:
        print(f"❌ Expected POSITIVE, got {x_sign}")
        return False


def main():
    """Run all tests."""
    print("=== Direct Path Sensitivity Tests ===\n")
    
    results = []
    results.append(("PathConstraint creation", test_path_constraint_creation()))
    results.append(("CFG with conditions", test_cfg_with_conditions()))
    results.append(("State forking", test_state_forking()))
    results.append(("Constraint application", test_constraint_application()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Path sensitivity components are working!")
        print("Ready to proceed with full integration.")
    else:
        print("\n⚠️ Some components need fixing.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)