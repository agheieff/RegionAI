#!/usr/bin/env python3
"""
Test script for loop analysis with fixpoint computation.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.loop_analysis_curriculum import LoopAnalysisCurriculumGenerator
from src.regionai.analysis import build_cfg, analyze_with_fixpoint
from src.regionai.discovery.abstract_domains import Sign


def visualize_cfg(cfg):
    """Simple CFG visualization."""
    print("\nControl Flow Graph:")
    for block_id, block in sorted(cfg.blocks.items()):
        block_type = "LOOP" if block.is_loop_header else block.type.name
        print(f"  Block {block_id} ({block_type}):")
        
        if block.statements:
            for stmt in block.statements:
                code = ast.unparse(stmt).strip()
                print(f"    {code}")
        else:
            print("    (empty)")
            
        if block.successors:
            print(f"    → successors: {sorted(block.successors)}")
        if block.back_edge_sources:
            print(f"    ← back edges from: {sorted(block.back_edge_sources)}")
    print()


def test_loop_analysis():
    """Test loop analysis with fixpoint computation."""
    print("=== Testing Loop Analysis with Fixpoint Computation ===")
    print("Goal: Soundly analyze loops to prove properties\n")
    
    # Test 1: Simple accumulator loop
    print("=== Test 1: Positive Accumulator Loop ===")
    code1 = """sum = 0
i = 1
while i <= 10:
    sum = sum + i
    i = i + 1"""
    
    print("Code:")
    for line in code1.strip().split('\n'):
        print(f"  {line}")
    
    tree = ast.parse(code1)
    
    # Build and visualize CFG
    cfg = build_cfg(tree)
    visualize_cfg(cfg)
    
    # Analyze with fixpoint
    print("Fixpoint Analysis:")
    result = analyze_with_fixpoint(tree, initial_assumptions={})
    
    if result['final_state']:
        print("Final state:")
        for var, sign in result['final_state'].sign_state.items():
            print(f"  {var}: {sign.name}")
    
    # Show loop analysis
    if result['loops']:
        print("\nLoop Analysis:")
        for loop_id, loop_info in result['loops'].items():
            print(f"  Loop at block {loop_id}:")
            print(f"    Body blocks: {sorted(loop_info['body'])}")
            if loop_info['fixpoint_state']:
                print(f"    Fixpoint reached after {loop_info['fixpoint_state'].iteration_count} iterations")
    
    # Test 2: Loop that never executes
    print("\n\n=== Test 2: Never-Executing Loop ===")
    code2 = """x = 5
y = 0
while False:
    x = -1
    y = y + 1
result = x + y"""
    
    print("Code:")
    for line in code2.strip().split('\n'):
        print(f"  {line}")
    
    tree2 = ast.parse(code2)
    result2 = analyze_with_fixpoint(tree2)
    
    print("\nAnalysis shows loop never executes:")
    if result2['final_state']:
        for var, sign in result2['final_state'].sign_state.items():
            print(f"  {var}: {sign.name}")
    
    # Test 3: Loop requiring widening
    print("\n\n=== Test 3: Counting Loop (Widening Required) ===")
    code3 = """i = 0
while i < 100:
    i = i + 1"""
    
    print("Code:")
    for line in code3.strip().split('\n'):
        print(f"  {line}")
    
    tree3 = ast.parse(code3)
    
    # Track iterations
    print("\nAnalyzing with widening...")
    result3 = analyze_with_fixpoint(tree3)
    
    # Show how widening works
    print("Without widening: i ∈ {0}, {0,1}, {0,1,2}, ...")
    print("With widening: i → POSITIVE (any positive value)")
    
    if result3['final_state']:
        print("\nFinal state after widening:")
        for var, sign in result3['final_state'].sign_state.items():
            print(f"  {var}: {sign.name}")
    
    # Test 4: Curriculum problem
    print("\n\n=== Test 4: Curriculum Example ===")
    curriculum_gen = LoopAnalysisCurriculumGenerator()
    problems = curriculum_gen.generate_basic_loop_curriculum()
    
    if problems:
        problem = problems[0]  # positive_accumulator
        print(f"Problem: {problem.name}")
        print(f"Description: {problem.description}")
        
        code = ast.unparse(problem.input_data['code']).strip()
        print("\nCode:")
        for line in code.split('\n'):
            print(f"  {line}")
        
        # Analyze
        result = analyze_with_fixpoint(problem.input_data['code'])
        
        print("\nExpected properties:", problem.output_data)
        print("Analyzed properties:")
        if result['final_state']:
            for var, expected in problem.output_data.items():
                actual = result['final_state'].sign_state.get(var, Sign.TOP)
                match = "✓" if actual.name == expected else "✗"
                print(f"  {var}: {actual.name} {match}")
    
    print("\n\n=== Conceptual Understanding ===")
    print("Fixpoint analysis enables:")
    print("  1. Sound analysis of loops with unknown bounds")
    print("  2. Discovering loop invariants automatically")
    print("  3. Guaranteed termination via widening")
    print("  4. Foundation for all loop optimizations")
    
    print("\n=== The Power of Fixpoint ===")
    print("Without fixpoint: Can only analyze straight-line code")
    print("With fixpoint: Can analyze any program with loops")
    print("This completes the analytical engine!")


if __name__ == "__main__":
    test_loop_analysis()