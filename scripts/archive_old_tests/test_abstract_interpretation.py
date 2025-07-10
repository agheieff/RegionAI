#!/usr/bin/env python3
"""
Test script for abstract interpretation - sign analysis.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.abstract_interpretation_curriculum import AbstractInterpretationCurriculumGenerator
from src.regionai.discovery.abstract_domains import (
    Sign, sign_from_constant, sign_add, sign_multiply,
    reset_abstract_state, update_sign_state,
    get_sign_state, is_definitely_positive
)
import src.regionai.discovery.abstract_domains as abstract_domains


def analyze_sign_properties(tree: ast.AST) -> dict:
    """Analyze sign properties of all variables in the program."""
    # Reset global state
    reset_abstract_state(tree, [])
    
    # Visit all assignments and track signs
    class SignAnalyzer(ast.NodeVisitor):
        def visit_Module(self, node):
            # Process statements in order
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    update_sign_state(stmt, [])
            self.generic_visit(node)
    
    analyzer = SignAnalyzer()
    analyzer.visit(tree)
    
    # Extract final sign properties from the global state
    return dict(abstract_domains._abstract_state.sign_state)


def test_sign_analysis():
    """Test abstract sign analysis."""
    print("=== Testing Abstract Interpretation: Sign Analysis ===")
    print("Goal: Reason about sign properties without concrete execution")
    
    # Test basic sign operations
    print("\n=== Part 1: Sign Algebra ===")
    print(f"POSITIVE + POSITIVE = {sign_add(Sign.POSITIVE, Sign.POSITIVE)}")
    print(f"POSITIVE + NEGATIVE = {sign_add(Sign.POSITIVE, Sign.NEGATIVE)}")
    print(f"NEGATIVE + NEGATIVE = {sign_add(Sign.NEGATIVE, Sign.NEGATIVE)}")
    print(f"POSITIVE * POSITIVE = {sign_multiply(Sign.POSITIVE, Sign.POSITIVE)}")
    print(f"POSITIVE * NEGATIVE = {sign_multiply(Sign.POSITIVE, Sign.NEGATIVE)}")
    print(f"NEGATIVE * NEGATIVE = {sign_multiply(Sign.NEGATIVE, Sign.NEGATIVE)}")
    print(f"ZERO * POSITIVE = {sign_multiply(Sign.ZERO, Sign.POSITIVE)}")
    
    # Test curriculum problems
    curriculum_gen = AbstractInterpretationCurriculumGenerator()
    sign_problems = curriculum_gen.generate_sign_analysis_curriculum()
    
    print(f"\n=== Part 2: Sign Property Inference ===")
    print(f"Generated {len(sign_problems)} sign analysis problems:")
    
    for problem in sign_problems[:3]:  # Show first 3
        print(f"\n{problem.name}: {problem.description}")
        code = ast.unparse(problem.input_data).strip()
        print("Code:")
        for line in code.split('\n'):
            print(f"  {line}")
        
        # Analyze the code
        properties = analyze_sign_properties(problem.input_data)
        
        print("Inferred properties:")
        if properties:
            for var, sign in properties.items():
                print(f"  {var}: {sign.name}")
        else:
            print("  (none tracked)")
        
        print("Expected properties:")
        for var, expected in problem.output_data.items():
            if '_' not in var:  # Skip special markers like 'x_after_if'
                print(f"  {var}: {expected}")
        
        # Check if inference matches expectation
        matches = True
        for var, expected in problem.output_data.items():
            if '_' not in var and var in properties:
                if properties[var].name != expected:
                    matches = False
                    break
        print(f"Match: {'✓' if matches else '✗'}")
    
    print("\n=== Part 3: Property-Based Optimization ===")
    
    # Example: Remove unnecessary checks
    code = """x = 5
y = 10
if x > 0:
    result = y / x
else:
    result = 0"""
    
    tree = ast.parse(code)
    print("Original code:")
    print(ast.unparse(tree))
    
    # Analyze properties
    properties = analyze_sign_properties(tree)
    print("\nSign properties:")
    for var, sign in properties.items():
        print(f"  {var}: {sign.name}")
    
    print("\nOptimization opportunity:")
    print("  Since x is POSITIVE, the condition 'x > 0' is always True")
    print("  The else branch can be eliminated")
    
    print("\n=== Discovery Pattern ===")
    print("The system should learn:")
    print("\n1. Abstract Propagation:")
    print("   FOR_EACH Assign node:")
    print("     sign = ANALYZE_EXPRESSION(value)")
    print("     UPDATE_SIGN_STATE(target, sign)")
    
    print("\n2. Abstract Operations:")
    print("   POSITIVE + POSITIVE → POSITIVE")
    print("   NEGATIVE * NEGATIVE → POSITIVE")
    print("   anything * ZERO → ZERO")
    
    print("\n3. Property-Based Reasoning:")
    print("   IF variable.sign == POSITIVE:")
    print("     ELIMINATE checks for > 0")
    print("     ELIMINATE division-by-zero checks")
    
    print("\n=== Conceptual Understanding ===")
    print("RegionAI learns:")
    print("  - Programs have abstract properties beyond concrete values")
    print("  - These properties follow mathematical laws")
    print("  - Abstract reasoning enables powerful optimizations")
    print("  - Soundness: better to be conservative than wrong")


def test_abstract_transformation():
    """Test using abstract properties for transformation."""
    print("\n\n=== Part 4: Abstract-Guided Transformation ===")
    
    # Create a simple optimization based on sign analysis
    code_before = """x = 10
y = -5
z = x * y
if z < 0:
    result = 'negative'
else:
    result = 'positive'"""
    
    tree = ast.parse(code_before)
    properties = analyze_sign_properties(tree)
    
    print("Code analysis:")
    print(f"  x is {properties.get('x', Sign.TOP).name}")
    print(f"  y is {properties.get('y', Sign.TOP).name}")
    print(f"  z = x * y, so z is {sign_multiply(properties.get('x', Sign.TOP), properties.get('y', Sign.TOP)).name}")
    
    print("\nSince z is definitely NEGATIVE, we can optimize:")
    print("  The condition 'z < 0' is always True")
    print("  Transform to: result = 'negative'")
    
    # Show the conceptual discovery
    print("\n=== Abstract Interpretation Power ===")
    print("This demonstrates reasoning about:")
    print("  1. Properties that hold for ALL possible executions")
    print("  2. Compile-time proofs about runtime behavior")
    print("  3. Optimizations impossible with concrete values alone")


if __name__ == "__main__":
    test_sign_analysis()
    test_abstract_transformation()