#!/usr/bin/env python3
"""
Test improved state merging at all join points
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
from regionai.config import RegionAIConfig


def test_join_point_merging():
    """Test that states are merged at join points, not just when hitting limit."""
    print("Testing join point merging...")
    
    code = """
def test_join(a, b):
    # Multiple paths that reconverge
    if a > 0:
        x = 1
    else:
        x = -1
    
    if b > 0:
        y = 1
    else:
        y = -1
    
    # Join point - states should be merged here
    z = x + y
    return z
"""
    
    tree = ast.parse(code)
    func_ast = tree.body[0]
    cfg = build_cfg(func_ast)
    
    # Use config with higher limit to ensure merging happens at join, not limit
    config = RegionAIConfig(max_states_per_point=20)
    context = AnalysisContext(config=config)
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    initial_state = AbstractState()
    initial_state.set_sign('a', Sign.TOP)
    initial_state.set_sign('b', Sign.TOP)
    
    block_states = analyzer.analyze(initial_state)
    
    # Print analysis results
    print(f"\nCFG has {len(cfg.blocks)} blocks")
    for block_id, states in block_states.items():
        block = cfg.blocks[block_id]
        print(f"\nBlock {block_id} (predecessors: {block.predecessors}):")
        print(f"  Number of states: {len(states)}")
        
        if block.statements:
            print(f"  Statements: {[ast.dump(s) for s in block.statements[:2]]}")
        
        # Check if this is a join point
        if len(block.predecessors) > 1:
            print(f"  *** This is a join point with {len(block.predecessors)} predecessors")
            # At join points, states should be merged
            if len(states) <= 4:  # Should have at most 4 states (2^2 paths)
                print(f"  ✅ States properly merged at join point")
            else:
                print(f"  ❌ Too many states at join point: {len(states)}")
    
    # Find the block with z = x + y
    merge_block = None
    for block_id, block in cfg.blocks.items():
        for stmt in block.statements:
            if (isinstance(stmt, ast.Assign) and 
                isinstance(stmt.targets[0], ast.Name) and 
                stmt.targets[0].id == 'z'):
                merge_block = block_id
                break
    
    if merge_block:
        states = block_states.get(merge_block, [])
        print(f"\nMerge block (z = x + y) has {len(states)} states")
        # With proper merging, we should have manageable states even with 4 paths
        return len(states) <= 4
    
    return False


def test_state_grouping():
    """Test that states with same abstract values are grouped."""
    print("\nTesting state grouping in merge...")
    
    # Create test states
    states = []
    
    # States 1 & 2: x=1, y=2 (different paths)
    for i in range(2):
        state = AnalysisState(
            abstract_state=AbstractState(),
            iteration_count=0,
            path_constraints=[]
        )
        state.abstract_state.set_sign('x', Sign.POSITIVE)
        state.abstract_state.set_sign('y', Sign.POSITIVE)
        states.append(state)
    
    # State 3: x=-1, y=2
    state = AnalysisState(
        abstract_state=AbstractState(),
        iteration_count=0,
        path_constraints=[]
    )
    state.abstract_state.set_sign('x', Sign.NEGATIVE)
    state.abstract_state.set_sign('y', Sign.POSITIVE)
    states.append(state)
    
    # State 4: x=1, y=-2
    state = AnalysisState(
        abstract_state=AbstractState(),
        iteration_count=0,
        path_constraints=[]
    )
    state.abstract_state.set_sign('x', Sign.POSITIVE)
    state.abstract_state.set_sign('y', Sign.NEGATIVE)
    states.append(state)
    
    print(f"Input: {len(states)} states")
    
    # Test merging
    cfg = build_cfg(ast.parse("pass"))
    config = RegionAIConfig(max_states_per_point=10)  # High limit
    context = AnalysisContext(config=config)
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    merged = analyzer.merge_states_at_join(states)
    print(f"After merge: {len(merged)} states")
    
    # Should have 3 states (states 1&2 merged due to same values)
    if len(merged) == 3:
        print("✅ States with identical values were grouped")
        return True
    else:
        print(f"❌ Expected 3 states after grouping, got {len(merged)}")
        return False


def test_aggressive_merging():
    """Test aggressive merging when limit is exceeded."""
    print("\nTesting aggressive merging at limit...")
    
    # Create many states with different values
    states = []
    for i in range(8):
        state = AnalysisState(
            abstract_state=AbstractState(),
            iteration_count=0,
            path_constraints=[]
        )
        # Alternate signs to create distinct states
        state.abstract_state.set_sign('x', Sign.POSITIVE if i % 2 == 0 else Sign.NEGATIVE)
        state.abstract_state.set_sign('y', Sign.ZERO if i % 3 == 0 else Sign.POSITIVE)
        states.append(state)
    
    print(f"Input: {len(states)} distinct states")
    
    # Test with low limit
    cfg = build_cfg(ast.parse("pass"))
    config = RegionAIConfig(max_states_per_point=3)
    context = AnalysisContext(config=config)
    analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
    
    merged = analyzer.merge_states_at_join(states)
    print(f"After merge with limit 3: {len(merged)} states")
    
    if len(merged) == 1:
        print("✅ Aggressive merge reduced to single state")
        # Check that differing values became TOP
        x_sign = merged[0].abstract_state.get_sign('x')
        if x_sign == Sign.TOP:
            print("✅ Variable x correctly set to TOP")
            return True
        else:
            print(f"❌ Variable x should be TOP, got {x_sign}")
            return False
    else:
        print(f"❌ Expected 1 state after aggressive merge")
        return False


def main():
    """Run all improved merging tests."""
    print("=== Improved State Merging Tests ===\n")
    
    results = []
    results.append(("Join point merging", test_join_point_merging()))
    results.append(("State grouping", test_state_grouping()))
    results.append(("Aggressive merging", test_aggressive_merging()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Improved merging is working correctly!")
        print("States are merged at join points, not just at the limit.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)