#!/usr/bin/env python3
"""
Test script for abstract sign analysis and property proving.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.abstract_sign_analysis_curriculum import AbstractSignAnalysisCurriculumGenerator
from src.regionai.discovery.abstract_domains import (
    Sign, prove_property, get_proof_explanation,
    reset_abstract_state, update_sign_state
)
import src.regionai.discovery.abstract_domains as abstract_domains
from typing import Dict, List, Any


def simulate_input_function(tree: ast.AST, input_type: str) -> ast.AST:
    """
    Replace input functions with abstract values.
    input_positive_integer() -> assumed POSITIVE
    input_negative_integer() -> assumed NEGATIVE
    input_integer() -> assumed TOP (any sign)
    """
    class InputReplacer(ast.NodeTransformer):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                if node.func.id == 'input_positive_integer':
                    # Create a marker that will be interpreted as POSITIVE
                    return ast.Constant(value='<POSITIVE>')
                elif node.func.id == 'input_negative_integer':
                    return ast.Constant(value='<NEGATIVE>')
                elif node.func.id == 'input_integer':
                    return ast.Constant(value='<ANY>')
            return self.generic_visit(node)
    
    return InputReplacer().visit(tree)


def enhanced_update_sign_state(node: ast.AST, args: List[Any]) -> ast.AST:
    """Enhanced version that handles input markers."""
    if isinstance(node, ast.Assign) and node.targets:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            
            # Check for input markers
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                if node.value.value == '<POSITIVE>':
                    abstract_domains._abstract_state.set_sign(var_name, Sign.POSITIVE)
                elif node.value.value == '<NEGATIVE>':
                    abstract_domains._abstract_state.set_sign(var_name, Sign.NEGATIVE)
                elif node.value.value == '<ANY>':
                    abstract_domains._abstract_state.set_sign(var_name, Sign.TOP)
            else:
                # Use regular update
                update_sign_state(node, args)
    
    return node


def prove_sign_properties(code: str, properties: Dict[str, str]) -> Dict[str, bool]:
    """
    Prove sign properties about variables in the given code.
    """
    # Parse and prepare code
    tree = ast.parse(code)
    tree = simulate_input_function(tree, 'sign')
    
    # Convert string properties to Sign enum
    sign_spec = {}
    for var, prop in properties.items():
        if prop == 'POSITIVE':
            sign_spec[var] = Sign.POSITIVE
        elif prop == 'NEGATIVE':
            sign_spec[var] = Sign.NEGATIVE
        elif prop == 'ZERO':
            sign_spec[var] = Sign.ZERO
        elif prop == 'NON_NEGATIVE':
            # For now, treat as needing to be POSITIVE or ZERO
            sign_spec[var] = Sign.POSITIVE  # Simplified
    
    # Reset state
    reset_abstract_state(tree, [])
    
    # Analyze with enhanced interpreter
    class ProofInterpreter(ast.NodeVisitor):
        def visit_Module(self, node):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    enhanced_update_sign_state(stmt, [])
                self.visit(stmt)
    
    interpreter = ProofInterpreter()
    interpreter.visit(tree)
    
    # Verify properties
    results = {}
    for var, expected_sign in sign_spec.items():
        actual = abstract_domains._abstract_state.get_sign(var)
        results[var] = (actual == expected_sign)
    
    return results


def test_abstract_proofs():
    """Test abstract sign analysis and property proving."""
    print("=== Testing Abstract Sign Analysis and Property Proving ===")
    print("Goal: Prove properties about programs for ALL possible inputs")
    
    curriculum_gen = AbstractSignAnalysisCurriculumGenerator()
    
    # Test 1: Basic Proofs
    print("\n=== Part 1: Basic Sign Property Proofs ===")
    basic_problems = curriculum_gen.generate_basic_proof_curriculum()
    
    for problem in basic_problems[:3]:
        print(f"\n{problem.name}: {problem.description}")
        
        code = problem.input_data['code']
        spec = problem.input_data['spec']
        
        print("Code:")
        code_str = ast.unparse(code).strip()
        for line in code_str.split('\n'):
            print(f"  {line}")
        
        print(f"Prove: {spec}")
        
        # Attempt proof
        results = prove_sign_properties(code_str, spec)
        
        print("Proof results:")
        for var, proven in results.items():
            status = "✓ PROVEN" if proven else "✗ CANNOT PROVE"
            explanation = get_proof_explanation(var)
            print(f"  {var}: {status} - {explanation}")
    
    # Test 2: Complex Proof
    print("\n\n=== Part 2: Complex Sign Reasoning ===")
    
    code = """x = input_integer()
if x < 0:
    abs_x = -x
else:
    abs_x = x
result = abs_x + 1"""
    
    spec = {'result': 'POSITIVE'}
    
    print("Code (computing absolute value):")
    for line in code.split('\n'):
        print(f"  {line}")
    
    print(f"\nProve: result is always POSITIVE")
    
    # This is complex - our simple analysis might not handle it yet
    results = prove_sign_properties(code, spec)
    print(f"Result: {'PROVEN' if results.get('result', False) else 'CANNOT PROVE (need path-sensitive analysis)'}")
    
    # Test 3: Security Property
    print("\n\n=== Part 3: Security-Relevant Proofs ===")
    
    code = """x = input_positive_integer()
y = 0
z = x / y"""
    
    print("Code (potential division by zero):")
    for line in code.split('\n'):
        print(f"  {line}")
    
    print("\nAnalyzing for safety...")
    tree = ast.parse(code)
    tree = simulate_input_function(tree, 'sign')
    reset_abstract_state(tree, [])
    
    # Analyze
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            enhanced_update_sign_state(stmt, [])
    
    # Check if division is safe
    y_sign = abstract_domains._abstract_state.get_sign('y')
    print(f"Variable y is: {y_sign.name}")
    print("Division by zero detected!" if y_sign == Sign.ZERO else "Division is safe")
    
    print("\n=== Conceptual Understanding ===")
    print("Abstract interpretation enables:")
    print("  1. Proving properties for ALL possible inputs")
    print("  2. Finding bugs without test cases")
    print("  3. Enabling aggressive optimizations")
    print("  4. Guaranteeing program safety")
    
    print("\n=== Discovery Pattern ===")
    print("The system learns to:")
    print("  1. Track abstract states through program flow")
    print("  2. Apply abstract transformers to operations")
    print("  3. Prove properties by forward analysis")
    print("  4. Recognize when properties cannot be proven")


if __name__ == "__main__":
    test_abstract_proofs()