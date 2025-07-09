"""
Curriculum for teaching AST transformations and code refactoring.
"""
import ast
from typing import List
from .problem import Problem


class ASTRefactoringCurriculumGenerator:
    """
    Teaches the AI to discover and apply code refactoring patterns.
    Starting with the fundamental concept: identity elements.
    """
    
    def generate_additive_identity_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning additive identity simplification.
        Pattern: x + 0 → x and 0 + x → x
        """
        print("Generating curriculum for additive identity refactoring...")
        
        problems = []
        
        # Problem 1: Simple right-side zero
        code1_before = "result = value + 0"
        code1_after = "result = value"
        ast1_before = ast.parse(code1_before).body[0]
        ast1_after = ast.parse(code1_after).body[0]
        
        problems.append(Problem(
            name="additive_identity_right",
            problem_type="transformation",
            input_data=ast1_before,
            output_data=ast1_after,
            description="Simplify addition with zero on the right"
        ))
        
        # Problem 2: Left-side zero
        code2_before = "result = 0 + value"
        code2_after = "result = value"
        ast2_before = ast.parse(code2_before).body[0]
        ast2_after = ast.parse(code2_after).body[0]
        
        problems.append(Problem(
            name="additive_identity_left",
            problem_type="transformation",
            input_data=ast2_before,
            output_data=ast2_after,
            description="Simplify addition with zero on the left"
        ))
        
        # Problem 3: Nested expression
        code3_before = "result = (x + y) + 0"
        code3_after = "result = x + y"
        ast3_before = ast.parse(code3_before).body[0]
        ast3_after = ast.parse(code3_after).body[0]
        
        problems.append(Problem(
            name="additive_identity_nested",
            problem_type="transformation",
            input_data=ast3_before,
            output_data=ast3_after,
            description="Simplify nested addition with zero"
        ))
        
        # Problem 4: Multiple occurrences
        code4_before = "result = a + 0 + b + 0"
        code4_after = "result = a + b"
        ast4_before = ast.parse(code4_before).body[0]
        ast4_after = ast.parse(code4_after).body[0]
        
        problems.append(Problem(
            name="additive_identity_multiple",
            problem_type="transformation",
            input_data=ast4_before,
            output_data=ast4_after,
            description="Simplify multiple additions with zero"
        ))
        
        # Problem 5: Different variable names
        code5_before = "total = count + 0"
        code5_after = "total = count"
        ast5_before = ast.parse(code5_before).body[0]
        ast5_after = ast.parse(code5_after).body[0]
        
        problems.append(Problem(
            name="additive_identity_different_vars",
            problem_type="transformation",
            input_data=ast5_before,
            output_data=ast5_after,
            description="Generalize to different variable names"
        ))
        
        return problems
    
    def generate_multiplicative_identity_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning multiplicative identity.
        Pattern: x * 1 → x and 1 * x → x
        """
        print("Generating curriculum for multiplicative identity refactoring...")
        
        problems = []
        
        # Problem 1: Simple right-side one
        code1_before = "result = value * 1"
        code1_after = "result = value"
        ast1_before = ast.parse(code1_before).body[0]
        ast1_after = ast.parse(code1_after).body[0]
        
        problems.append(Problem(
            name="multiplicative_identity_right",
            problem_type="transformation",
            input_data=ast1_before,
            output_data=ast1_after,
            description="Simplify multiplication with one on the right"
        ))
        
        # Problem 2: Left-side one
        code2_before = "result = 1 * value"
        code2_after = "result = value"
        ast2_before = ast.parse(code2_before).body[0]
        ast2_after = ast.parse(code2_after).body[0]
        
        problems.append(Problem(
            name="multiplicative_identity_left",
            problem_type="transformation",
            input_data=ast2_before,
            output_data=ast2_after,
            description="Simplify multiplication with one on the left"
        ))
        
        return problems
    
    def generate_mixed_identity_curriculum(self) -> List[Problem]:
        """
        Mixed problems to test generalization of identity concept.
        """
        print("Generating curriculum for mixed identity refactoring...")
        
        problems = []
        
        # Problem 1: Both additive and multiplicative
        code1_before = "result = (x + 0) * 1"
        code1_after = "result = x"
        ast1_before = ast.parse(code1_before).body[0]
        ast1_after = ast.parse(code1_after).body[0]
        
        problems.append(Problem(
            name="mixed_identity",
            problem_type="transformation",
            input_data=ast1_before,
            output_data=ast1_after,
            description="Simplify both additive and multiplicative identities"
        ))
        
        # Problem 2: Complex nested case
        code2_before = "result = ((a + 0) * 1) + (b * 1)"
        code2_after = "result = a + b"
        ast2_before = ast.parse(code2_before).body[0]
        ast2_after = ast.parse(code2_after).body[0]
        
        problems.append(Problem(
            name="complex_nested_identity",
            problem_type="transformation",
            input_data=ast2_before,
            output_data=ast2_after,
            description="Simplify complex nested identity operations"
        ))
        
        return problems