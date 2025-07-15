#!/usr/bin/env python3
"""
Simple test runner for path sensitivity without pytest
"""
import ast
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.regionai.analysis.fixpoint import PathSensitiveFixpointAnalyzer
from src.regionai.analysis.cfg import build_cfg
from src.regionai.analysis.context import AnalysisContext
from src.regionai.discovery.abstract_domains import AbstractState, Sign


def test_simple_if_else():
    """Test basic if-else path sensitivity."""
    print("Testing simple if-else path sensitivity...")
    
    code = """
if flag > 0:
    x = 1
else:
    x = -1
"""
    
    tree = ast.parse(code)
    cfg = build_cfg(tree)
    
    # Print CFG info
    print(f"CFG has {len(cfg.blocks)} blocks")
    for block_id, block in cfg.blocks.items():
        print(f"Block {block_id}: type={block.type}, successors={block.successors}")
        if block.branch_condition:
            print(f"  Branch condition: {ast.dump(block.branch_condition)}")
        for succ_id, (cond, is_true) in block.successor_conditions.items():
            print(f"  Successor {succ_id}: {'true' if is_true else 'false'} branch")
    
    # Create analyzer
    context = AnalysisContext()
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    # Initial state
    initial_state = AbstractState()
    initial_state.set_sign('flag', Sign.TOP)
    
    # Analyze
    try:
        block_states = analyzer.analyze(initial_state)
        
        print(f"\nAnalysis complete. States per block:")
        for block_id, states in block_states.items():
            print(f"Block {block_id}: {len(states)} states")
            for i, state in enumerate(states):
                print(f"  State {i}:")
                print(f"    Signs: {state.abstract_state.sign_state}")
                print(f"    Constraints: {[str(c) for c in state.path_constraints]}")
        
        # Check results
        exit_states = block_states.get(cfg.exit_block, [])
        if exit_states:
            print(f"\nExit block has {len(exit_states)} states")
            x_signs = set()
            for state in exit_states:
                x_sign = state.abstract_state.get_sign('x')
                x_signs.add(x_sign)
                print(f"  x = {x_sign}")
            
            if Sign.POSITIVE in x_signs and Sign.NEGATIVE in x_signs:
                print("✅ SUCCESS: Found both positive and negative paths for x")
                return True
            else:
                print("❌ FAIL: Did not find both paths")
                return False
        else:
            print("❌ FAIL: No exit states found")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_constraint_application():
    """Test that path constraints refine values."""
    print("\nTesting path constraint refinement...")
    
    code = """
if y > 10:
    z = y
else:
    z = 0
"""
    
    tree = ast.parse(code)
    cfg = build_cfg(tree)
    
    context = AnalysisContext()
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    initial_state = AbstractState()
    initial_state.set_sign('y', Sign.TOP)
    
    try:
        block_states = analyzer.analyze(initial_state)
        
        # Look for states where y > 10 constraint was applied
        found_refined = False
        for block_id, states in block_states.items():
            for state in states:
                for constraint in state.path_constraints:
                    if constraint.is_true and hasattr(constraint.condition, 'left'):
                        if (isinstance(constraint.condition.left, ast.Name) and 
                            constraint.condition.left.id == 'y'):
                            y_sign = state.abstract_state.get_sign('y')
                            if y_sign == Sign.POSITIVE:
                                print(f"✅ Found refined state: y is {y_sign} when y > 10")
                                found_refined = True
        
        return found_refined
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=== Path Sensitivity Tests ===\n")
    
    results = []
    tests = [
        ("Simple if-else", test_simple_if_else),
        ("Path constraint refinement", test_path_constraint_application)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except AssertionError as e:
            print(f"\n❌ {test_name} assertion failed: {str(e)}")
            results.append((test_name, False))
        except Exception as e:
            print(f"\n❌ {test_name} error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Assert all tests passed
    assert passed == total, f"Only {passed}/{total} tests passed"
    
    print("\n🎉 Path sensitivity is working!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)