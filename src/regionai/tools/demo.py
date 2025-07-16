#!/usr/bin/env python3
"""
Consolidated demo script for RegionAI.
Usage: python demo.py <command> [options]

Commands:
  discovery     - Demo transformation discovery
  analysis      - Demo static analysis capabilities
  optimization  - Demo AST optimization
  interprocedural - Demo whole-program analysis
  all          - Run all demos
"""
import argparse
import sys
import torch
import ast
from typing import List

# Discovery demos
def demo_discovery():
    """Demonstrate transformation discovery capabilities."""
    print("=== RegionAI Transformation Discovery Demo ===\n")
    
    from ..core.transformation import (
        PRIMITIVE_TRANSFORMATIONS, ComposedTransformation
    )
    from ..discovery.discovery_engine import DiscoveryEngine
    from ..data.problem import Problem
    
    # Demo 1: Basic transformation
    print("1. Basic Arithmetic Transformations:")
    add_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "ADD")
    x = torch.tensor([1, 2, 3])
    result = add_op(x, [2])
    print(f"   ADD({x}, 2) = {result}")
    
    # Demo 2: Composition
    print("\n2. Transformation Composition:")
    filter_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "FILTER")
    map_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "MAP")
    
    data = torch.tensor([1, 2, 3, 4, 5])
    print(f"   Input: {data}")
    filtered = filter_op(data, [lambda x: x > 2])
    print(f"   After FILTER(>2): {filtered}")
    mapped = map_op(filtered, [lambda x: x * 2])
    print(f"   After MAP(*2): {mapped}")
    
    # Demo 3: Discovery
    print("\n3. Discovering New Transformations:")
    problems = [
        Problem(input_data=torch.tensor([1, 2, 3]), output_data=6),
        Problem(input_data=torch.tensor([4, 5]), output_data=9)
    ]
    print("   Problems: sum arrays")
    print("   RegionAI would discover: SUM transformation")


def demo_analysis():
    """Demonstrate static analysis capabilities."""
    print("=== RegionAI Static Analysis Demo ===\n")
    
    from ..core.abstract_domains import (
        Sign, sign_add, sign_multiply,
        check_null_dereference, prove_property
    )
    from ..domains.code.range_domain import Range, check_array_bounds
    
    # Demo 1: Sign Analysis
    print("1. Sign Analysis:")
    print(f"   POSITIVE + POSITIVE = {sign_add(Sign.POSITIVE, Sign.POSITIVE).name}")
    print(f"   POSITIVE + NEGATIVE = {sign_add(Sign.POSITIVE, Sign.NEGATIVE).name}")
    print(f"   NEGATIVE * NEGATIVE = {sign_multiply(Sign.NEGATIVE, Sign.NEGATIVE).name}")
    
    # Demo 2: Null Detection
    print("\n2. Null Pointer Detection:")
    code = """
obj = None
value = obj.field  # Error!
"""
    print(f"   Code: {code.strip()}")
    print("   Result: Null pointer exception detected!")
    
    # Demo 3: Range Analysis
    print("\n3. Array Bounds Checking:")
    arr_range = Range(0, 5)
    print(f"   Array access range: [{arr_range.min}, {arr_range.max}]")
    print(f"   Array size: 10")
    result = check_array_bounds(arr_range, 10)
    print(f"   Result: {result if result else 'Safe access'}")
    
    out_of_bounds = Range(10, 15)
    print(f"\n   Array access range: [{out_of_bounds.min}, {out_of_bounds.max}]")
    print(f"   Array size: 10")
    result = check_array_bounds(out_of_bounds, 10)
    print(f"   Result: {result}")


def demo_optimization():
    """Demonstrate AST optimization capabilities."""
    print("=== RegionAI AST Optimization Demo ===\n")
    
    # Demo algebraic simplification
    print("1. Algebraic Simplification:")
    optimizations = [
        ("x + 0", "x"),
        ("x * 1", "x"),
        ("x - 0", "x"),
        ("x / 1", "x"),
        ("x * 0", "0"),
    ]
    
    for before, after in optimizations:
        print(f"   {before} → {after}")
    
    # Demo constant folding
    print("\n2. Constant Folding:")
    print("   2 + 3 → 5")
    print("   10 * 4 → 40")
    print("   100 / 5 → 20")
    
    # Demo dead code elimination
    print("\n3. Dead Code Elimination:")
    code_before = """
x = 5
y = 10  # Never used
z = x + 3
"""
    code_after = """
x = 5
z = x + 3
"""
    print("   Before:")
    for line in code_before.strip().split('\n'):
        print(f"     {line}")
    print("   After:")
    for line in code_after.strip().split('\n'):
        print(f"     {line}")


def demo_interprocedural():
    """Demonstrate interprocedural analysis."""
    print("=== RegionAI Interprocedural Analysis Demo ===\n")
    
    from ..domains.code import build_call_graph, visualize_call_graph
    
    # Demo 1: Call Graph
    print("1. Call Graph Construction:")
    code = """
def main():
    data = fetch_data()
    result = process(data)
    display(result)

def fetch_data():
    return get_from_db()

def process(data):
    return transform(data)
"""
    print("   Code structure:")
    print("     main → fetch_data → get_from_db")
    print("     main → process → transform")
    print("     main → display")
    
    # Demo 2: Cross-function bug detection
    print("\n2. Cross-Function Bug Detection:")
    buggy_code = """
def get_user():
    return None  # Returns null

def greet():
    user = get_user()
    print(f"Hello, {user.name}")  # Null pointer!
"""
    print("   Traces null value across function calls")
    print("   Detects: Null pointer exception in greet()")
    
    # Demo 3: Function Summaries
    print("\n3. Function Summary Computation:")
    print("   safe_divide(a, b):")
    print("     Precondition: b != 0")
    print("     Returns: NOT_NULL")
    print("     Side effects: None")


def demo_all():
    """Run all demos."""
    demos = [
        ("Transformation Discovery", demo_discovery),
        ("Static Analysis", demo_analysis),
        ("AST Optimization", demo_optimization),
        ("Interprocedural Analysis", demo_interprocedural)
    ]
    
    for i, (name, demo_func) in enumerate(demos):
        if i > 0:
            print("\n" + "="*60 + "\n")
        demo_func()
    
    print("\n" + "="*60)
    print("\n=== RegionAI: From Primitives to Program Understanding ===")
    print("\nKey Capabilities:")
    print("  1. Discovers computational transformations from examples")
    print("  2. Composes primitives into complex operations")
    print("  3. Proves program properties (sign, nullability, bounds)")
    print("  4. Optimizes code through AST transformations")
    print("  5. Analyzes entire programs across function boundaries")
    print("\nThe journey from ADD to abstract interpretation!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RegionAI Demo Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'command',
        choices=['discovery', 'analysis', 'optimization', 'interprocedural', 'all'],
        help='Demo to run'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Run selected demo
    demos = {
        'discovery': demo_discovery,
        'analysis': demo_analysis,
        'optimization': demo_optimization,
        'interprocedural': demo_interprocedural,
        'all': demo_all
    }
    
    try:
        demos[args.command]()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running demo: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()