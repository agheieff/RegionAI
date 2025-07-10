#!/usr/bin/env python3
"""
Test script for interprocedural analysis.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.interprocedural_curriculum import InterproceduralCurriculumGenerator
from src.regionai.analysis import (
    build_call_graph, visualize_call_graph,
    analyze_interprocedural
)


def test_interprocedural_analysis():
    """Test whole-program interprocedural analysis."""
    print("=== Testing Interprocedural Analysis ===")
    print("Goal: Analyze entire programs across function boundaries\n")
    
    # Test 1: Simple call graph
    print("=== Test 1: Call Graph Construction ===")
    code1 = """def get_data():
    return 42

def process_data():
    data = get_data()
    result = transform(data)
    return result

def transform(x):
    return x * 2

def main():
    output = process_data()
    print(output)"""
    
    print("Code:")
    for line in code1.strip().split('\n'):
        print(f"  {line}")
    
    tree1 = ast.parse(code1)
    call_graph = build_call_graph(tree1)
    
    print("\n" + visualize_call_graph(call_graph))
    
    # Test 2: Null propagation across functions
    print("\n\n=== Test 2: Null Propagation ===")
    code2 = """def get_user_input():
    # Simulating function that returns None
    return None

def process_user():
    user = get_user_input()
    print(user.name)  # Null pointer exception!"""
    
    print("Code:")
    for line in code2.strip().split('\n'):
        print(f"  {line}")
    
    tree2 = ast.parse(code2)
    result2 = analyze_interprocedural(tree2)
    
    print("\nAnalysis Results:")
    if result2.errors:
        print("ERRORS:")
        for error in result2.errors:
            print(f"  ❌ {error}")
    else:
        print("  No errors found")
    
    print("\nFunction Summaries:")
    for func_name, summary in result2.function_summaries.items():
        print(f"  {func_name}:")
        print(f"    Returns: {summary.returns.nullability.name}")
    
    # Test 3: Conditional null return
    print("\n\n=== Test 3: Conditional Null Return ===")
    code3 = """def find_item(item_id):
    if item_id > 0:
        return {"name": "Item", "id": item_id}
    else:
        return None

def display_item(id):
    item = find_item(id)
    print(item["name"])  # Potential null access!"""
    
    print("Code:")
    for line in code3.strip().split('\n'):
        print(f"  {line}")
    
    tree3 = ast.parse(code3)
    result3 = analyze_interprocedural(tree3)
    
    print("\nAnalysis Results:")
    if result3.warnings:
        print("WARNINGS:")
        for warning in result3.warnings:
            print(f"  ⚠️  {warning}")
    
    # Test 4: Recursive function
    print("\n\n=== Test 4: Recursive Function Analysis ===")
    code4 = """def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

def compute():
    result = factorial(5)
    return result"""
    
    print("Code:")
    for line in code4.strip().split('\n'):
        print(f"  {line}")
    
    tree4 = ast.parse(code4)
    call_graph4 = build_call_graph(tree4)
    
    print("\nRecursive functions detected:")
    recursive = call_graph4.get_recursive_functions()
    for func in recursive:
        print(f"  ↻ {func}")
    
    # Test 5: Curriculum example
    print("\n\n=== Test 5: Curriculum Example ===")
    curriculum_gen = InterproceduralCurriculumGenerator()
    problems = curriculum_gen.generate_basic_interprocedural_curriculum()
    
    if problems:
        problem = problems[0]  # null_propagation_simple
        print(f"Problem: {problem.name}")
        print(f"Description: {problem.description}")
        
        code = ast.unparse(problem.input_data['code']).strip()
        print("\nCode:")
        for line in code.split('\n'):
            print(f"  {line}")
        
        print("\nExpected errors:", problem.output_data['errors'])
    
    print("\n\n=== Conceptual Understanding ===")
    print("Interprocedural analysis enables:")
    print("  1. Tracking data flow across function calls")
    print("  2. Detecting bugs that span multiple functions")
    print("  3. Understanding whole-program behavior")
    print("  4. Optimizing based on global information")
    
    print("\n=== The Power of Whole-Program Analysis ===")
    print("Intraprocedural: Analyzes one function at a time")
    print("Interprocedural: Analyzes entire call chains")
    print("This finds bugs that single-function analysis misses!")


def test_function_summaries():
    """Test function summary computation."""
    print("\n\n=== Test 6: Function Summaries ===")
    
    code = """def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b

def risky_divide(a, b):
    return a / b  # No check!

def get_null():
    return None

def get_positive():
    return 42"""
    
    print("Computing summaries for:")
    for line in code.strip().split('\n'):
        print(f"  {line}")
    
    tree = ast.parse(code)
    result = analyze_interprocedural(tree)
    
    print("\nFunction Summaries:")
    for func_name, summary in result.function_summaries.items():
        print(f"\n{func_name}():")
        print(f"  Returns: {summary.returns.nullability.name}")
        print(f"  Always returns: {summary.returns.always_returns}")
        if summary.preconditions:
            print(f"  Preconditions: {summary.preconditions}")
        if summary.side_effects.modifies_globals:
            print(f"  Modifies globals: {summary.side_effects.modifies_globals}")


if __name__ == "__main__":
    test_interprocedural_analysis()
    test_function_summaries()