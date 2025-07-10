"""
Curriculum for teaching constant folding and dead code elimination.
"""
import ast
from typing import List
from .problem import Problem


class ConstantFoldingCurriculumGenerator:
    """
    Teaches the AI to discover constant folding and dead code elimination.
    Patterns:
    1. Constant folding: Evaluate expressions with constant operands at compile time
    2. Dead code elimination: Remove unreachable or useless code
    """
    
    def generate_constant_folding_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning constant folding.
        Pattern: expressions with constant operands → evaluated result
        """
        print("Generating curriculum for constant folding...")
        
        problems = []
        
        # Problem 1: Simple arithmetic
        code1_before = "result = 2 + 3"
        code1_after = "result = 5"
        problems.append(Problem(
            name="constant_fold_add",
            problem_type="transformation",
            input_data=ast.parse(code1_before).body[0],
            output_data=ast.parse(code1_after).body[0],
            description="Fold simple addition"
        ))
        
        # Problem 2: Multiplication
        code2_before = "result = 10 * 4"
        code2_after = "result = 40"
        problems.append(Problem(
            name="constant_fold_mult",
            problem_type="transformation",
            input_data=ast.parse(code2_before).body[0],
            output_data=ast.parse(code2_after).body[0],
            description="Fold multiplication"
        ))
        
        # Problem 3: Complex expression
        code3_before = "result = (10 * 4) + 2"
        code3_after = "result = 42"
        problems.append(Problem(
            name="constant_fold_complex",
            problem_type="transformation",
            input_data=ast.parse(code3_before).body[0],
            output_data=ast.parse(code3_after).body[0],
            description="Fold complex expression"
        ))
        
        # Problem 4: Division
        code4_before = "result = 100 / 5"
        code4_after = "result = 20.0"
        problems.append(Problem(
            name="constant_fold_div",
            problem_type="transformation",
            input_data=ast.parse(code4_before).body[0],
            output_data=ast.parse(code4_after).body[0],
            description="Fold division"
        ))
        
        # Problem 5: Nested operations
        code5_before = "result = (2 + 3) * (4 + 1)"
        code5_after = "result = 25"
        problems.append(Problem(
            name="constant_fold_nested",
            problem_type="transformation",
            input_data=ast.parse(code5_before).body[0],
            output_data=ast.parse(code5_after).body[0],
            description="Fold nested constant expressions"
        ))
        
        # Problem 6: Boolean operations
        code6_before = "result = 5 > 3"
        code6_after = "result = True"
        problems.append(Problem(
            name="constant_fold_compare",
            problem_type="transformation",
            input_data=ast.parse(code6_before).body[0],
            output_data=ast.parse(code6_after).body[0],
            description="Fold comparison operations"
        ))
        
        # Problem 7: Unary operations
        code7_before = "result = -(-42)"
        code7_after = "result = 42"
        problems.append(Problem(
            name="constant_fold_unary",
            problem_type="transformation",
            input_data=ast.parse(code7_before).body[0],
            output_data=ast.parse(code7_after).body[0],
            description="Fold unary operations"
        ))
        
        return problems
    
    def generate_dead_code_elimination_curriculum(self) -> List[Problem]:
        """
        Generates problems for learning dead code elimination.
        Pattern: unreachable or useless code → removed
        """
        print("Generating curriculum for dead code elimination...")
        
        problems = []
        
        # Problem 1: If False block
        code1_before = """
if False:
    x = 1
    y = 2
result = 42"""
        code1_after = "result = 42"
        problems.append(Problem(
            name="dead_code_if_false",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Remove if False block"
        ))
        
        # Problem 2: If True with else
        code2_before = """
if True:
    result = 1
else:
    result = 2"""
        code2_after = "result = 1"
        problems.append(Problem(
            name="dead_code_if_true",
            problem_type="transformation",
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Remove unreachable else block"
        ))
        
        # Problem 3: While False
        code3_before = """
while False:
    x = x + 1
result = 0"""
        code3_after = "result = 0"
        problems.append(Problem(
            name="dead_code_while_false",
            problem_type="transformation",
            input_data=ast.parse(code3_before),
            output_data=ast.parse(code3_after),
            description="Remove while False loop"
        ))
        
        # Problem 4: Constant condition after folding
        code4_before = """
if 2 + 2 == 5:
    result = 'impossible'
else:
    result = 'correct'"""
        code4_after = "result = 'correct'"
        problems.append(Problem(
            name="dead_code_folded_condition",
            problem_type="transformation",
            input_data=ast.parse(code4_before),
            output_data=ast.parse(code4_after),
            description="Remove branch with folded false condition"
        ))
        
        # Problem 5: Dead assignment (overwritten)
        code5_before = """
y = 5
y = 10
result = y"""
        code5_after = """
y = 10
result = y"""
        problems.append(Problem(
            name="dead_code_assignment",
            problem_type="transformation",
            input_data=ast.parse(code5_before),
            output_data=ast.parse(code5_after),
            description="Remove overwritten assignment"
        ))
        
        return problems
    
    def generate_combined_optimization_curriculum(self) -> List[Problem]:
        """
        Problems requiring both constant folding and dead code elimination.
        """
        print("Generating curriculum for combined optimizations...")
        
        problems = []
        
        # Problem 1: Fold then eliminate
        code1_before = """
if 3 > 5:
    result = 100
else:
    result = 2 * 21"""
        code1_after = "result = 42"
        problems.append(Problem(
            name="combined_fold_eliminate",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Fold constants then eliminate dead code"
        ))
        
        # Problem 2: Complex folding and elimination
        code2_before = """
x = 10 + 20
if x == 30:
    y = x * 2
else:
    y = 0
result = y + 5"""
        code2_after = "result = 65"
        problems.append(Problem(
            name="combined_complex",
            problem_type="transformation", 
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Multiple folding and elimination steps"
        ))
        
        return problems