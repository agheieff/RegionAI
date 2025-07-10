"""
Curriculum for teaching algebraic identities and optimization patterns.
"""
import ast
from typing import List
from .problem import Problem


class AlgebraicIdentitiesCurriculumGenerator:
    """
    Teaches the AI to discover algebraic identities and strength reduction optimizations.
    Patterns:
    1. Multiplicative identity: x * 1 → x and 1 * x → x
    2. Strength reduction: x * 2 → x << 1 (multiplication by power of 2 to bit shift)
    """
    
    def generate_multiplicative_identity_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning multiplicative identity.
        Pattern: x * 1 → x and 1 * x → x
        """
        print("Generating curriculum for multiplicative identity...")
        
        problems = []
        
        # Problem 1: Simple right-side one
        code1_before = "result = value * 1"
        code1_after = "result = value"
        problems.append(Problem(
            name="mult_identity_right",
            problem_type="transformation",
            input_data=ast.parse(code1_before).body[0],
            output_data=ast.parse(code1_after).body[0],
            description="Simplify multiplication by one on the right"
        ))
        
        # Problem 2: Left-side one
        code2_before = "result = 1 * value"
        code2_after = "result = value"
        problems.append(Problem(
            name="mult_identity_left",
            problem_type="transformation",
            input_data=ast.parse(code2_before).body[0],
            output_data=ast.parse(code2_after).body[0],
            description="Simplify multiplication by one on the left"
        ))
        
        # Problem 3: Nested expression
        code3_before = "result = (a * b) * 1"
        code3_after = "result = a * b"
        problems.append(Problem(
            name="mult_identity_nested",
            problem_type="transformation",
            input_data=ast.parse(code3_before).body[0],
            output_data=ast.parse(code3_after).body[0],
            description="Simplify nested multiplication by one"
        ))
        
        # Problem 4: Complex expression
        code4_before = "result = 1 * (x + y) * 1"
        code4_after = "result = x + y"
        problems.append(Problem(
            name="mult_identity_complex",
            problem_type="transformation",
            input_data=ast.parse(code4_before).body[0],
            output_data=ast.parse(code4_after).body[0],
            description="Simplify multiple multiplications by one"
        ))
        
        # Problem 5: Different variable names
        code5_before = "total = count * 1"
        code5_after = "total = count"
        problems.append(Problem(
            name="mult_identity_different_vars",
            problem_type="transformation",
            input_data=ast.parse(code5_before).body[0],
            output_data=ast.parse(code5_after).body[0],
            description="Generalize to different variable names"
        ))
        
        return problems
    
    def generate_strength_reduction_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning strength reduction.
        Pattern: x * 2^n → x << n (focusing on x * 2 → x << 1)
        """
        print("Generating curriculum for strength reduction...")
        
        problems = []
        
        # Problem 1: Simple multiplication by 2
        code1_before = "result = value * 2"
        code1_after = "result = value << 1"
        problems.append(Problem(
            name="strength_reduction_2",
            problem_type="transformation",
            input_data=ast.parse(code1_before).body[0],
            output_data=ast.parse(code1_after).body[0],
            description="Replace multiplication by 2 with left shift by 1"
        ))
        
        # Problem 2: Left-side 2
        code2_before = "result = 2 * value"
        code2_after = "result = value << 1"
        problems.append(Problem(
            name="strength_reduction_2_left",
            problem_type="transformation",
            input_data=ast.parse(code2_before).body[0],
            output_data=ast.parse(code2_after).body[0],
            description="Replace 2 * x with x << 1"
        ))
        
        # Problem 3: Complex expression
        code3_before = "result = (a + b) * 2"
        code3_after = "result = (a + b) << 1"
        problems.append(Problem(
            name="strength_reduction_complex",
            problem_type="transformation",
            input_data=ast.parse(code3_before).body[0],
            output_data=ast.parse(code3_after).body[0],
            description="Strength reduction on complex expression"
        ))
        
        # Problem 4: Multiplication by 4 (2^2)
        code4_before = "result = value * 4"
        code4_after = "result = value << 2"
        problems.append(Problem(
            name="strength_reduction_4",
            problem_type="transformation",
            input_data=ast.parse(code4_before).body[0],
            output_data=ast.parse(code4_after).body[0],
            description="Replace multiplication by 4 with left shift by 2"
        ))
        
        # Problem 5: Multiplication by 8 (2^3)
        code5_before = "result = value * 8"
        code5_after = "result = value << 3"
        problems.append(Problem(
            name="strength_reduction_8",
            problem_type="transformation",
            input_data=ast.parse(code5_before).body[0],
            output_data=ast.parse(code5_after).body[0],
            description="Replace multiplication by 8 with left shift by 3"
        ))
        
        return problems
    
    def generate_mixed_optimization_curriculum(self) -> List[Problem]:
        """
        Mixed problems combining different optimization patterns.
        """
        print("Generating curriculum for mixed optimizations...")
        
        problems = []
        
        # Problem 1: Both identity and strength reduction potential
        code1_before = "result = (x * 1) * 2"
        code1_after = "result = x << 1"
        problems.append(Problem(
            name="mixed_optimization_1",
            problem_type="transformation",
            input_data=ast.parse(code1_before).body[0],
            output_data=ast.parse(code1_after).body[0],
            description="Apply both multiplicative identity and strength reduction"
        ))
        
        # Problem 2: Multiple optimizations
        code2_before = "result = (a * 2) + (b * 1)"
        code2_after = "result = (a << 1) + b"
        problems.append(Problem(
            name="mixed_optimization_2",
            problem_type="transformation",
            input_data=ast.parse(code2_before).body[0],
            output_data=ast.parse(code2_after).body[0],
            description="Multiple optimizations in one expression"
        ))
        
        # Problem 3: Nested with all patterns
        code3_before = "result = ((x + 0) * 1) * 2"
        code3_after = "result = x << 1"
        problems.append(Problem(
            name="mixed_optimization_all",
            problem_type="transformation",
            input_data=ast.parse(code3_before).body[0],
            output_data=ast.parse(code3_after).body[0],
            description="Apply additive identity, multiplicative identity, and strength reduction"
        ))
        
        return problems