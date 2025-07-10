"""
Curriculum for teaching constant propagation through data flow analysis.
"""
import ast
from typing import List
from .problem import Problem


class ConstantPropagationCurriculumGenerator:
    """
    Teaches the AI to track variable values across statements and propagate constants.
    This requires understanding data flow and maintaining program state.
    """
    
    def generate_simple_propagation_curriculum(self) -> List[Problem]:
        """
        Generates problems for basic constant propagation.
        Pattern: Track constant assignments and replace variable uses.
        """
        print("Generating curriculum for simple constant propagation...")
        
        problems = []
        
        # Problem 1: Basic propagation
        code1_before = """x = 10
y = x + 5"""
        code1_after = """x = 10
y = 15"""
        problems.append(Problem(
            name="simple_propagation",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Propagate x=10 then fold"
        ))
        
        # Problem 2: Multiple uses
        code2_before = """a = 42
b = a + 1
c = a * 2"""
        code2_after = """a = 42
b = 43
c = 84"""
        problems.append(Problem(
            name="multiple_uses",
            problem_type="transformation",
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Propagate constant to multiple uses"
        ))
        
        # Problem 3: Chain propagation
        code3_before = """x = 5
y = x
z = y + 10"""
        code3_after = """x = 5
y = 5
z = 15"""
        problems.append(Problem(
            name="chain_propagation",
            problem_type="transformation",
            input_data=ast.parse(code3_before),
            output_data=ast.parse(code3_after),
            description="Propagate through variable assignments"
        ))
        
        # Problem 4: Overwrite tracking
        code4_before = """x = 10
y = x + 1
x = 20
z = x + 1"""
        code4_after = """x = 10
y = 11
x = 20
z = 21"""
        problems.append(Problem(
            name="overwrite_tracking",
            problem_type="transformation",
            input_data=ast.parse(code4_before),
            output_data=ast.parse(code4_after),
            description="Track variable overwrites correctly"
        ))
        
        # Problem 5: Mixed constants and variables
        code5_before = """PI = 3.14159
radius = 10
area = PI * radius * radius"""
        code5_after = """PI = 3.14159
radius = 10
area = 314.159"""
        problems.append(Problem(
            name="mixed_propagation",
            problem_type="transformation",
            input_data=ast.parse(code5_before),
            output_data=ast.parse(code5_after),
            description="Propagate multiple constants in expression"
        ))
        
        return problems
    
    def generate_propagation_enabling_elimination_curriculum(self) -> List[Problem]:
        """
        Problems where propagation enables dead code elimination.
        """
        print("Generating curriculum for propagation enabling elimination...")
        
        problems = []
        
        # Problem 1: Propagate then eliminate
        code1_before = """debug_mode = False
if debug_mode:
    print('Debugging...')
result = 42"""
        code1_after = """debug_mode = False
result = 42"""
        problems.append(Problem(
            name="propagate_eliminate_if",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Propagate False then eliminate dead if"
        ))
        
        # Problem 2: Propagate condition
        code2_before = """MAX_SIZE = 100
size = 50
if size < MAX_SIZE:
    status = 'OK'
else:
    status = 'TOO_BIG'"""
        code2_after = """MAX_SIZE = 100
size = 50
status = 'OK'"""
        problems.append(Problem(
            name="propagate_condition",
            problem_type="transformation",
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Propagate constants in condition then eliminate"
        ))
        
        # Problem 3: Loop condition
        code3_before = """ENABLED = False
while ENABLED:
    process()
done = True"""
        code3_after = """ENABLED = False
done = True"""
        problems.append(Problem(
            name="propagate_loop_condition",
            problem_type="transformation",
            input_data=ast.parse(code3_before),
            output_data=ast.parse(code3_after),
            description="Propagate to loop condition"
        ))
        
        return problems
    
    def generate_complex_propagation_curriculum(self) -> List[Problem]:
        """
        Complex propagation scenarios requiring full data flow understanding.
        """
        print("Generating curriculum for complex propagation...")
        
        problems = []
        
        # Problem 1: Full program optimization
        code1_before = """BASE_PRICE = 100
TAX_RATE = 0.08
quantity = 5
subtotal = BASE_PRICE * quantity
tax = subtotal * TAX_RATE
total = subtotal + tax"""
        code1_after = """BASE_PRICE = 100
TAX_RATE = 0.08
quantity = 5
subtotal = 500
tax = 40.0
total = 540.0"""
        problems.append(Problem(
            name="full_program_propagation",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Propagate through entire calculation"
        ))
        
        # Problem 2: Conditional with propagation
        code2_before = """threshold = 10
value = 5
if value < threshold:
    doubled = value * 2
    result = doubled + threshold
else:
    result = value"""
        code2_after = """threshold = 10
value = 5
doubled = 10
result = 20"""
        problems.append(Problem(
            name="conditional_propagation",
            problem_type="transformation",
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Propagate and simplify conditional"
        ))
        
        return problems