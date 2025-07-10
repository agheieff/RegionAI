"""
Curriculum for teaching range analysis and bounds checking.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class RangeAnalysisCurriculumGenerator:
    """
    Teaches the AI to track numeric ranges and detect bounds violations.
    """
    
    def generate_basic_range_curriculum(self) -> List[Problem]:
        """
        Basic range tracking problems.
        """
        print("Generating curriculum for basic range analysis...")
        
        problems = []
        
        # Problem 1: Simple constant ranges
        code1 = """x = 5
y = 10
z = x + y"""
        
        expected_ranges1 = {
            'x': '[5, 5]',
            'y': '[10, 10]',
            'z': '[15, 15]'
        }
        
        problems.append(Problem(
            name="constant_ranges",
            problem_type="range_analysis",
            input_data={'code': ast.parse(code1)},
            output_data=expected_ranges1,
            description="Track exact constant values as ranges"
        ))
        
        # Problem 2: Range arithmetic
        code2 = """a = 10
b = 20
c = b - a
d = a * 2"""
        
        expected_ranges2 = {
            'a': '[10, 10]',
            'b': '[20, 20]', 
            'c': '[10, 10]',
            'd': '[20, 20]'
        }
        
        problems.append(Problem(
            name="range_arithmetic",
            problem_type="range_analysis",
            input_data={'code': ast.parse(code2)},
            output_data=expected_ranges2,
            description="Compute ranges through arithmetic"
        ))
        
        # Problem 3: Bounded input
        code3 = """# x is in range [0, 100]
x = input_bounded(0, 100)
y = x + 50
z = x * 2"""
        
        expected_ranges3 = {
            'x': '[0, 100]',
            'y': '[50, 150]',
            'z': '[0, 200]'
        }
        
        problems.append(Problem(
            name="bounded_input",
            problem_type="range_analysis",
            input_data={'code': ast.parse(code3)},
            output_data=expected_ranges3,
            description="Propagate ranges from bounded inputs"
        ))
        
        return problems
    
    def generate_array_bounds_curriculum(self) -> List[Problem]:
        """
        Problems for array bounds checking.
        """
        print("Generating curriculum for array bounds checking...")
        
        problems = []
        
        # Problem 1: Safe array access
        code1 = """arr = create_array(10)  # Size 10
index = 5
value = arr[index]"""
        
        expected_analysis1 = {
            'array_size': 10,
            'index_range': '[5, 5]',
            'bounds_check': 'SAFE'
        }
        
        problems.append(Problem(
            name="safe_array_access",
            problem_type="bounds_check",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Verify safe array access"
        ))
        
        # Problem 2: Out of bounds error
        code2 = """arr = create_array(5)
index = 10
value = arr[index]"""
        
        expected_analysis2 = {
            'array_size': 5,
            'index_range': '[10, 10]',
            'bounds_check': 'ERROR',
            'message': 'Array index always out of bounds (>= 5)'
        }
        
        problems.append(Problem(
            name="definite_out_of_bounds",
            problem_type="bounds_check",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Detect definite bounds violation"
        ))
        
        # Problem 3: Potential out of bounds
        code3 = """arr = create_array(10)
index = input_bounded(0, 15)
value = arr[index]"""
        
        expected_analysis3 = {
            'array_size': 10,
            'index_range': '[0, 15]',
            'bounds_check': 'WARNING',
            'message': 'Array index might be out of bounds (>= 10)'
        }
        
        problems.append(Problem(
            name="potential_out_of_bounds",
            problem_type="bounds_check",
            input_data={'code': ast.parse(code3)},
            output_data=expected_analysis3,
            description="Warn about potential bounds violation"
        ))
        
        # Problem 4: Negative index
        code4 = """arr = create_array(10)
i = -1
value = arr[i]"""
        
        expected_analysis4 = {
            'array_size': 10,
            'index_range': '[-1, -1]',
            'bounds_check': 'ERROR',
            'message': 'Array index is always negative'
        }
        
        problems.append(Problem(
            name="negative_index",
            problem_type="bounds_check",
            input_data={'code': ast.parse(code4)},
            output_data=expected_analysis4,
            description="Detect negative array index"
        ))
        
        return problems
    
    def generate_loop_range_curriculum(self) -> List[Problem]:
        """
        Range analysis in loops with widening.
        """
        print("Generating curriculum for loop range analysis...")
        
        problems = []
        
        # Problem 1: Simple counting loop
        code1 = """i = 0
while i < 10:
    i = i + 1"""
        
        expected_analysis1 = {
            'loop_header_range': {
                'i': '[0, 10]'  # After widening and refinement
            },
            'loop_exit_range': {
                'i': '[10, 10]'
            }
        }
        
        problems.append(Problem(
            name="counting_loop",
            problem_type="loop_range",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Analyze counting loop with widening"
        ))
        
        # Problem 2: Loop with array access
        code2 = """arr = create_array(10)
i = 0
while i < 10:
    value = arr[i]
    i = i + 1"""
        
        expected_analysis2 = {
            'loop_invariant': {
                'i': '[0, 9]'  # Inside loop
            },
            'bounds_check': 'SAFE',
            'reason': 'Loop guard ensures i < 10'
        }
        
        problems.append(Problem(
            name="loop_array_safe",
            problem_type="loop_range",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Prove array access safe in loop"
        ))
        
        # Problem 3: Loop with potential overflow
        code3 = """i = 0
while i < n:
    i = i + 1"""
        
        expected_analysis3 = {
            'requires_widening': True,
            'widened_range': {
                'i': '[0, +∞]'
            },
            'overflow_risk': True
        }
        
        problems.append(Problem(
            name="unbounded_loop",
            problem_type="loop_range",
            input_data={'code': ast.parse(code3)},
            output_data=expected_analysis3,
            description="Widen to infinity for unknown bound"
        ))
        
        return problems
    
    def generate_conditional_range_curriculum(self) -> List[Problem]:
        """
        Range refinement through conditionals.
        """
        print("Generating curriculum for conditional range analysis...")
        
        problems = []
        
        # Problem 1: Range refinement from condition
        code1 = """x = input_bounded(-100, 100)
if x > 0:
    y = x + 10  # x is in [1, 100] here
else:
    y = -x      # x is in [-100, 0] here"""
        
        expected_analysis1 = {
            'then_branch': {
                'x': '[1, 100]',
                'y': '[11, 110]'
            },
            'else_branch': {
                'x': '[-100, 0]',
                'y': '[0, 100]'
            },
            'after_if': {
                'y': '[0, 110]'  # Join of both branches
            }
        }
        
        problems.append(Problem(
            name="conditional_refinement",
            problem_type="conditional_range",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Refine ranges based on conditions"
        ))
        
        # Problem 2: Nested conditions
        code2 = """x = input_bounded(0, 100)
if x < 50:
    if x > 10:
        y = x  # x is in [11, 49]
    else:
        y = 0
else:
    y = 100"""
        
        expected_analysis2 = {
            'inner_then': {
                'x': '[11, 49]',
                'y': '[11, 49]'
            }
        }
        
        problems.append(Problem(
            name="nested_conditions",
            problem_type="conditional_range",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Handle nested conditional refinement"
        ))
        
        return problems
    
    def generate_overflow_detection_curriculum(self) -> List[Problem]:
        """
        Integer overflow detection.
        """
        print("Generating curriculum for overflow detection...")
        
        problems = []
        
        # Problem 1: Safe addition
        code1 = """# Assuming 32-bit integers: [-2^31, 2^31-1]
x = 1000
y = 2000
z = x + y"""
        
        expected_analysis1 = {
            'operation': 'x + y',
            'result_range': '[3000, 3000]',
            'overflow': False
        }
        
        problems.append(Problem(
            name="safe_addition",
            problem_type="overflow_check",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="No overflow in small addition"
        ))
        
        # Problem 2: Potential overflow
        code2 = """# MAX_INT = 2147483647
x = 2000000000
y = 2000000000
z = x + y"""
        
        expected_analysis2 = {
            'operation': 'x + y',
            'mathematical_result': 4000000000,
            'overflow': True,
            'warning': 'Integer overflow: result exceeds MAX_INT'
        }
        
        problems.append(Problem(
            name="integer_overflow",
            problem_type="overflow_check",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Detect integer overflow"
        ))
        
        return problems
    
    def generate_range_analysis_curriculum(self) -> List[Problem]:
        """
        Complete curriculum for range analysis.
        """
        all_problems = []
        all_problems.extend(self.generate_basic_range_curriculum())
        all_problems.extend(self.generate_array_bounds_curriculum())
        all_problems.extend(self.generate_loop_range_curriculum())
        all_problems.extend(self.generate_conditional_range_curriculum())
        all_problems.extend(self.generate_overflow_detection_curriculum())
        return all_problems