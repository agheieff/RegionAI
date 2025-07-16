#!/usr/bin/env python3
"""
Test state merging at reconvergence points
"""
import ast
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Add the root directory to path for tier imports

from regionai.analysis.fixpoint import PathSensitiveFixpointAnalyzer, AnalysisState
from regionai.analysis.cfg import build_cfg
from regionai.domains.code.analysis.context import AnalysisContext  
from regionai.core.abstract_domains import AbstractState, Sign


def test_simple_merge():
    """Test merging states after if-else."""
    print("Testing state merging after if-else...")
    
    code = """
def test_merge(cond):
    if cond > 0:
        x = 1
        y = 2
    else:
        x = -1
        y = 2
    # At this point: x could be 1 or -1, y is always 2
    z = y
    return z
"""
    
    tree = ast.parse(code)
    func_ast = tree.body[0]
    cfg = build_cfg(func_ast)
    
    context = AnalysisContext()
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    initial_state = AbstractState()
    initial_state.set_sign('cond', Sign.TOP)
    
    block_states = analyzer.analyze(initial_state)
    
    # Find the merge block (after if-else, before return)
    merge_block = None
    for block_id, block in cfg.blocks.items():
        if len(block.predecessors) > 1 and block.statements:
            # This is likely our merge point
            for stmt in block.statements:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
                    if stmt.targets[0].id == 'z':
                        merge_block = block_id
                        break
    
    if merge_block:
        states = block_states.get(merge_block, [])
        print(f"Merge block {merge_block} has {len(states)} states")
        
        # Check the values
        for i, state in enumerate(states):
            print(f"  State {i}:")
            print(f"    x: {state.abstract_state.get_sign('x')}")
            print(f"    y: {state.abstract_state.get_sign('y')}")
            print(f"    Constraints: {len(state.path_constraints)}")
        
        # Test merging manually
        if len(states) > 1:
            merged = analyzer.merge_states_at_join(states)
            print(f"\nAfter manual merge: {len(merged)} states")
            if merged:
                print(f"  x: {merged[0].abstract_state.get_sign('x')}")
                print(f"  y: {merged[0].abstract_state.get_sign('y')}")
        
        return True
    else:
        print("Could not find merge block")
        return False


def test_complex_merge():
    """Test merging with multiple variables."""
    print("\nTesting complex state merging...")
    
    code = """
def complex_merge(a, b):
    if a > 0:
        if b > 0:
            x = 1
            y = 1
        else:
            x = 1
            y = -1
    else:
        x = -1
        y = 0
    # Multiple paths converge here
    z = x + y
    return z
"""
    
    tree = ast.parse(code)
    func_ast = tree.body[0]
    cfg = build_cfg(func_ast)
    
    context = AnalysisContext()
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    initial_state = AbstractState()
    initial_state.set_sign('a', Sign.TOP)
    initial_state.set_sign('b', Sign.TOP)
    
    block_states = analyzer.analyze(initial_state)
    
    # Check how many distinct paths we track
    total_states = sum(len(states) for states in block_states.values())
    print(f"Total states across all blocks: {total_states}")
    
    # Test the merge function with different numbers of states
    test_states = []
    for i in range(7):  # Create more than MAX_STATES_PER_POINT
        state = AnalysisState(
            abstract_state=AbstractState(),
            iteration_count=0,
            path_constraints=[]
        )
        state.abstract_state.set_sign('var', Sign.POSITIVE if i % 2 == 0 else Sign.NEGATIVE)
        test_states.append(state)
    
    merged = analyzer.merge_states_at_join(test_states)
    print(f"\nMerging {len(test_states)} states -> {len(merged)} states")
    if merged:
        print(f"  var: {merged[0].abstract_state.get_sign('var')}")
        assert merged[0].abstract_state.get_sign('var') == Sign.TOP, "Should merge to TOP when values differ"
    
    return True


def main():
    """Run merge tests."""
    print("=== State Merging Tests ===\n")
    
    results = []
    results.append(("Simple merge", test_simple_merge()))
    results.append(("Complex merge", test_complex_merge()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)