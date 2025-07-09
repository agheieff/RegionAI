#!/usr/bin/env python3
"""
Test script for constant propagation and data flow analysis.
"""
import ast
import sys
sys.path.insert(0, '.')

from src.regionai.data.constant_propagation_curriculum import ConstantPropagationCurriculumGenerator


def apply_constant_propagation(tree: ast.AST) -> ast.AST:
    """Apply constant propagation with data flow analysis."""
    variable_state = {}
    
    class ConstantPropagator(ast.NodeTransformer):
        def visit_Module(self, node):
            # Process statements in order to track data flow
            new_body = []
            for stmt in node.body:
                new_stmt = self.visit(stmt)
                if new_stmt is not None:
                    new_body.append(new_stmt)
            node.body = new_body
            return node
        
        def visit_Assign(self, node):
            # First propagate in the value
            node.value = self.visit(node.value)
            
            # Then update our state tracking
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                if isinstance(node.value, ast.Constant):
                    # Track this constant value
                    variable_state[var_name] = node.value.value
                else:
                    # Variable assigned non-constant, mark as unknown
                    variable_state[var_name] = None
            
            return node
        
        def visit_Name(self, node):
            # Only propagate loads, not stores
            if isinstance(node.ctx, ast.Load):
                var_name = node.id
                if var_name in variable_state and variable_state[var_name] is not None:
                    # Replace with the known constant value
                    return ast.Constant(value=variable_state[var_name])
            return node
        
        def visit_BinOp(self, node):
            # Propagate in operands first
            node = self.generic_visit(node)
            
            # Then try to fold if both are constants
            if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                try:
                    if isinstance(node.op, ast.Add):
                        result = node.left.value + node.right.value
                    elif isinstance(node.op, ast.Sub):
                        result = node.left.value - node.right.value
                    elif isinstance(node.op, ast.Mult):
                        result = node.left.value * node.right.value
                    elif isinstance(node.op, ast.Div):
                        result = node.left.value / node.right.value
                    else:
                        return node
                    return ast.Constant(value=result)
                except:
                    return node
            
            return node
    
    return ConstantPropagator().visit(tree)


def apply_propagation_and_elimination(tree: ast.AST) -> ast.AST:
    """Apply constant propagation followed by dead code elimination."""
    # First propagate constants
    tree = apply_constant_propagation(tree)
    
    # Then fold any resulting constant expressions
    from src.regionai.discovery.ast_primitives import evaluate_node
    
    class ConstantFolder(ast.NodeTransformer):
        def visit_BinOp(self, node):
            node = self.generic_visit(node)
            return evaluate_node(node, [])
        
        def visit_Compare(self, node):
            node = self.generic_visit(node)
            return evaluate_node(node, [])
    
    tree = ConstantFolder().visit(tree)
    
    # Then eliminate dead code
    class DeadCodeEliminator(ast.NodeTransformer):
        def visit_If(self, node):
            node = self.generic_visit(node)
            
            if isinstance(node.test, ast.Constant):
                if node.test.value:
                    # True condition - keep only if body
                    # Return the body statements (will be flattened by visit_Module)
                    return node.body
                else:
                    # False condition - keep only else body
                    return node.orelse
            return node
        
        def visit_While(self, node):
            node = self.generic_visit(node)
            
            if isinstance(node.test, ast.Constant) and not node.test.value:
                return None  # Remove while False
            return node
        
        def visit_Module(self, node):
            new_body = []
            for item in node.body:
                result = self.visit(item)
                if result is not None:
                    if isinstance(result, list):
                        new_body.extend(result)
                    else:
                        new_body.append(result)
            node.body = new_body
            return node
    
    return DeadCodeEliminator().visit(tree)


def test_constant_propagation():
    """Test constant propagation discovery."""
    print("=== Testing Constant Propagation via Data Flow Analysis ===")
    print("Goal: Track variable values across statements and propagate constants")
    
    curriculum_gen = ConstantPropagationCurriculumGenerator()
    
    # Test 1: Simple Propagation
    print("\n=== Part 1: Simple Constant Propagation ===")
    simple_problems = curriculum_gen.generate_simple_propagation_curriculum()
    
    print(f"\nGenerated {len(simple_problems)} propagation problems:")
    for problem in simple_problems[:3]:  # Show first 3
        print(f"\n{problem.name}: {problem.description}")
        before_code = ast.unparse(problem.input_data).strip()
        after_code = ast.unparse(problem.output_data).strip()
        print("Before:")
        for line in before_code.split('\n'):
            print(f"  {line}")
        print("After:")
        for line in after_code.split('\n'):
            print(f"  {line}")
    
    # Test the transformation
    print("\n\nTesting constant propagation:")
    for problem in simple_problems:
        result = apply_constant_propagation(ast.parse(ast.unparse(problem.input_data)))
        expected = problem.output_data
        
        result_code = ast.unparse(result).strip()
        expected_code = ast.unparse(expected).strip()
        matches = result_code == expected_code
        
        print(f"  {problem.name}: {'✓' if matches else '✗'}")
        if not matches:
            print(f"    Expected: {expected_code}")
            print(f"    Got:      {result_code}")
    
    # Test 2: Propagation Enabling Elimination
    print("\n=== Part 2: Propagation Enabling Dead Code Elimination ===")
    elimination_problems = curriculum_gen.generate_propagation_enabling_elimination_curriculum()
    
    print(f"\nGenerated {len(elimination_problems)} combined optimization problems:")
    for problem in elimination_problems[:2]:  # Show first 2
        print(f"\n{problem.name}: {problem.description}")
        before_code = ast.unparse(problem.input_data).strip()
        print("Before:")
        for line in before_code.split('\n'):
            print(f"  {line}")
    
    print("\n\nTesting propagation + elimination:")
    for problem in elimination_problems:
        result = apply_propagation_and_elimination(ast.parse(ast.unparse(problem.input_data)))
        expected = problem.output_data
        
        result_code = ast.unparse(result).strip()
        expected_code = ast.unparse(expected).strip()
        matches = result_code == expected_code
        
        print(f"  {problem.name}: {'✓' if matches else '✗'}")
        if not matches:
            print(f"    Expected: {expected_code}")
            print(f"    Got:      {result_code}")
    
    print("\n=== Discovery Patterns ===")
    print("The system should discover:")
    print("\n1. State Tracking:")
    print("   FOR_EACH Assign node:")
    print("     IF value is Constant:")
    print("       UPDATE_VARIABLE_STATE(target, value)")
    print("     ELSE:")
    print("       UPDATE_VARIABLE_STATE(target, UNKNOWN)")
    
    print("\n2. Propagation:")
    print("   FOR_EACH Name(Load) node:")
    print("     state = GET_VARIABLE_STATE(node)")
    print("     IF state is Constant:")
    print("       REPLACE node WITH Constant(state)")
    
    print("\n=== Conceptual Understanding ===")
    print("RegionAI learns:")
    print("  - Variables carry values through program execution")
    print("  - These values can be tracked statically when constant")
    print("  - Propagation enables further optimizations")
    print("  - Data flow analysis is the foundation of program understanding")


if __name__ == "__main__":
    test_constant_propagation()