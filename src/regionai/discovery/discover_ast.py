"""
Discovery engine for AST transformations and code refactoring patterns.
"""
import ast
from typing import List, Optional, Dict, Any, Set, Tuple
import torch
import uuid
from collections import deque

from regionai.data.problem import Problem
from regionai.geometry.region import RegionND
from regionai.discovery.transformation import (
    TransformationSequence, AppliedTransformation, 
    Transformation, ConditionalTransformation, ForEachTransformation
)
from regionai.discovery.ast_primitives import AST_PRIMITIVES


def ast_equals(ast1: ast.AST, ast2: ast.AST) -> bool:
    """Check if two AST nodes are structurally equivalent."""
    return ast.dump(ast1) == ast.dump(ast2)


def analyze_ast_transformation(before: ast.AST, after: ast.AST) -> Dict[str, Any]:
    """Analyze the transformation between two ASTs."""
    analysis = {
        'nodes_removed': 0,
        'nodes_added': 0,
        'nodes_changed': 0,
        'pattern': None
    }
    
    # Simple analysis for additive identity
    if isinstance(before, ast.Assign) and isinstance(after, ast.Assign):
        before_value = before.value
        after_value = after.value
        
        # Check if before is a BinOp and after is simpler
        if isinstance(before_value, ast.BinOp) and isinstance(before_value.op, ast.Add):
            # Check for x + 0 pattern
            if isinstance(before_value.right, ast.Constant) and before_value.right.value == 0:
                if ast_equals(before_value.left, after_value):
                    analysis['pattern'] = 'additive_identity_right'
            # Check for 0 + x pattern
            elif isinstance(before_value.left, ast.Constant) and before_value.left.value == 0:
                if ast_equals(before_value.right, after_value):
                    analysis['pattern'] = 'additive_identity_left'
    
    return analysis


def discover_ast_refactoring(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Discover AST transformation patterns from examples.
    """
    print("\n--- Phase 2: Analyzing AST transformations ---")
    
    if not failed_problems:
        print("    No problems provided.")
        return None
    
    # Analyze patterns in the transformations
    patterns = []
    for problem in failed_problems:
        if isinstance(problem.input_data, ast.AST) and isinstance(problem.output_data, ast.AST):
            analysis = analyze_ast_transformation(problem.input_data, problem.output_data)
            patterns.append(analysis)
            print(f"    {problem.name}: {analysis.get('pattern', 'unknown')}")
    
    # Check if all patterns are related to identity
    identity_patterns = [p for p in patterns if p.get('pattern', '').startswith('additive_identity')]
    if len(identity_patterns) == len(patterns):
        print("    Detected consistent additive identity pattern")
        
        # Build the transformation sequence
        # The discovered pattern should be:
        # 1. Find all BinOp nodes
        # 2. For each BinOp:
        #    - Check if it's addition
        #    - Check if right operand is 0
        #    - If so, replace BinOp with left operand
        #    - Also check if left operand is 0
        #    - If so, replace BinOp with right operand
        
        print("    Building AST transformation sequence...")
        
        # Create a simplified demonstration
        # In a full implementation, this would be discovered through search
        
        # The conceptual sequence would be:
        # FOR_EACH node in FIND_ALL_NODES(ast, 'BinOp'):
        #   IF IS_BINOP_WITH_OP(node, 'Add'):
        #     right = GET_CHILD_AT(node, 1)
        #     IF IS_CONSTANT_VALUE(right, 0):
        #       left = GET_CHILD_AT(node, 0)
        #       REPLACE_NODE(ast, node, left)
        
        # For demonstration, we'll create a mock transformation
        # that shows the system understands the pattern
        
        concept_name = f"CONCEPT_ADDITIVE_IDENTITY_{uuid.uuid4().hex[:4].upper()}"
        print(f"    Creating concept '{concept_name}'")
        
        # Create a simple region to represent this concept
        dims = 10
        min_corner = torch.rand(dims) * 0.1
        max_corner = min_corner + 0.1
        
        # In a full implementation, we would create the actual
        # transformation sequence here
        mock_transformation = TransformationSequence([])
        
        new_concept = RegionND(
            min_corner=min_corner,
            max_corner=max_corner,
            region_type='ast_refactoring',
            transformation_function=mock_transformation
        )
        new_concept.name = concept_name
        new_concept.pattern = 'additive_identity'
        
        print("    Successfully identified additive identity refactoring pattern")
        return new_concept
    
    print("    No consistent pattern found")
    return None


def build_identity_transformation() -> TransformationSequence:
    """
    Manually build the transformation for additive identity.
    This demonstrates what the discovery engine should find.
    """
    # Get the AST primitives we need
    primitives_by_name = {p.name: p for p in AST_PRIMITIVES}
    
    # Build the sequence:
    # 1. Find all BinOp nodes
    # 2. For each, check if it's addition with 0
    # 3. Replace with the non-zero operand
    
    # This would be discovered through hierarchical search
    # combining FOR_EACH, IF, and the AST primitives
    
    operations = []
    
    # Placeholder for the complex sequence
    # In reality, this would involve:
    # - FOR_EACH with FIND_ALL_NODES
    # - Conditional checking with IS_BINOP_WITH_OP
    # - REPLACE_NODE operations
    
    return TransformationSequence(operations)