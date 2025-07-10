"""
Curriculum for teaching sound loop analysis via fixpoint computation.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class LoopAnalysisCurriculumGenerator:
    """
    Teaches the AI to analyze loops soundly using fixpoint iteration.
    """
    
    def generate_basic_loop_curriculum(self) -> List[Problem]:
        """
        Basic loop analysis problems requiring fixpoint computation.
        """
        print("Generating curriculum for basic loop analysis...")
        
        problems = []
        
        # Problem 1: Simple accumulator loop
        code1 = """sum = 0
i = 1
while i <= 10:
    sum = sum + i
    i = i + 1"""
        
        # After loop: sum is POSITIVE (accumulating positives), i is POSITIVE
        expected_properties1 = {
            'sum': 'POSITIVE',
            'i': 'POSITIVE'
        }
        
        problems.append(Problem(
            name="positive_accumulator",
            problem_type="loop_analysis",
            input_data={'code': ast.parse(code1)},
            output_data=expected_properties1,
            description="Prove loop maintains positive accumulator"
        ))
        
        # Problem 2: Loop that never executes
        code2 = """x = 5
y = 0
while False:
    x = -1
    y = y + 1
result = x + y"""
        
        # Loop never executes, so x=5, y=0
        expected_properties2 = {
            'x': 'POSITIVE',
            'y': 'ZERO',
            'result': 'POSITIVE'
        }
        
        problems.append(Problem(
            name="never_executing_loop",
            problem_type="loop_analysis",
            input_data={'code': ast.parse(code2)},
            output_data=expected_properties2,
            description="Recognize loop that never executes"
        ))
        
        # Problem 3: Loop with sign alternation (needs widening)
        code3 = """x = 1
while condition():
    x = -x"""
        
        # x alternates between positive and negative -> TOP after widening
        expected_properties3 = {
            'x': 'TOP'  # Could be any sign
        }
        
        problems.append(Problem(
            name="sign_alternation_loop",
            problem_type="loop_analysis",
            input_data={'code': ast.parse(code3)},
            output_data=expected_properties3,
            description="Handle sign alternation with widening"
        ))
        
        # Problem 4: Nested loops
        code4 = """sum = 0
i = 0
while i < 10:
    j = 0
    while j < 5:
        sum = sum + 1
        j = j + 1
    i = i + 1"""
        
        expected_properties4 = {
            'sum': 'POSITIVE',  # Or ZERO initially
            'i': 'POSITIVE',    # Or ZERO
            'j': 'POSITIVE'     # Or ZERO
        }
        
        problems.append(Problem(
            name="nested_loops",
            problem_type="loop_analysis",
            input_data={'code': ast.parse(code4)},
            output_data=expected_properties4,
            description="Analyze nested loop structure"
        ))
        
        return problems
    
    def generate_loop_invariant_curriculum(self) -> List[Problem]:
        """
        Problems requiring discovery of loop invariants.
        """
        print("Generating curriculum for loop invariants...")
        
        problems = []
        
        # Problem 1: Maintaining sign invariant
        code1 = """x = 10
while x > 0:
    x = x - 1
    y = x * x"""
        
        # Loop invariant: x >= 0, y >= 0
        expected_invariants1 = {
            'loop_invariant': {
                'x': 'NON_NEGATIVE',
                'y': 'NON_NEGATIVE'
            },
            'after_loop': {
                'x': 'ZERO',
                'y': 'ZERO'
            }
        }
        
        problems.append(Problem(
            name="decreasing_positive",
            problem_type="loop_invariant",
            input_data={'code': ast.parse(code1)},
            output_data=expected_invariants1,
            description="Discover x stays non-negative in loop"
        ))
        
        # Problem 2: Product invariant
        code2 = """product = 1
i = 1
while i <= n:
    if i > 0:
        product = product * i
    i = i + 1"""
        
        # Invariant: product is always positive (multiplying positives)
        expected_invariants2 = {
            'loop_invariant': {
                'product': 'POSITIVE',
                'i': 'POSITIVE'
            }
        }
        
        problems.append(Problem(
            name="factorial_invariant",
            problem_type="loop_invariant",
            input_data={'code': ast.parse(code2)},
            output_data=expected_invariants2,
            description="Prove factorial stays positive"
        ))
        
        return problems
    
    def generate_fixpoint_convergence_curriculum(self) -> List[Problem]:
        """
        Problems demonstrating fixpoint convergence and widening.
        """
        print("Generating curriculum for fixpoint convergence...")
        
        problems = []
        
        # Problem 1: Requires exactly 2 iterations to converge
        code1 = """x = 0
y = 0
if condition():
    x = 1
while x > 0:
    y = 1
    x = 0"""
        
        # First iteration: y could be 0
        # Second iteration: y could be 0 or 1 -> stabilizes
        convergence_trace1 = {
            'iterations': 2,
            'states': [
                {'y': 'ZERO'},
                {'y': 'TOP'}  # Could be ZERO or POSITIVE
            ]
        }
        
        problems.append(Problem(
            name="two_iteration_convergence",
            problem_type="fixpoint_trace",
            input_data={'code': ast.parse(code1)},
            output_data=convergence_trace1,
            description="Converges in exactly 2 iterations"
        ))
        
        # Problem 2: Requires widening to converge
        code2 = """i = 0
while i < 100:
    i = i + 1"""
        
        # Without widening: i ∈ {0}, {0,1}, {0,1,2}, ...
        # With widening: i -> [0, +∞) after threshold
        convergence_trace2 = {
            'requires_widening': True,
            'final_state': {
                'i': 'POSITIVE'  # Widened to any positive
            }
        }
        
        problems.append(Problem(
            name="counting_loop_widening",
            problem_type="fixpoint_trace",
            input_data={'code': ast.parse(code2)},
            output_data=convergence_trace2,
            description="Requires widening for termination"
        ))
        
        return problems
    
    def generate_loop_optimization_curriculum(self) -> List[Problem]:
        """
        Loop analysis enabling optimizations.
        """
        print("Generating curriculum for loop optimizations...")
        
        problems = []
        
        # Problem 1: Loop-invariant code motion
        code1 = """x = 10
y = 20
sum = 0
i = 0
while i < n:
    temp = x + y  # This is loop-invariant!
    sum = sum + temp
    i = i + 1"""
        
        # Analysis should detect that x and y don't change in loop
        invariant_analysis1 = {
            'loop_invariant_expressions': ['x + y'],
            'can_hoist': True
        }
        
        problems.append(Problem(
            name="loop_invariant_detection",
            problem_type="optimization_analysis",
            input_data={'code': ast.parse(code1)},
            output_data=invariant_analysis1,
            description="Detect loop-invariant computation"
        ))
        
        # Problem 2: Dead code in loop
        code2 = """sum = 0
i = 0
while i < 10:
    if False:
        sum = -1  # Dead code
    sum = sum + i
    i = i + 1"""
        
        # Analysis should prove the if-block is dead
        dead_code_analysis2 = {
            'dead_statements': ['sum = -1'],
            'final_sign': {
                'sum': 'POSITIVE'  # Never becomes negative
            }
        }
        
        problems.append(Problem(
            name="dead_code_in_loop",
            problem_type="optimization_analysis",
            input_data={'code': ast.parse(code2)},
            output_data=dead_code_analysis2,
            description="Detect dead code inside loop"
        ))
        
        return problems
    
    def generate_loop_analysis_curriculum(self) -> List[Problem]:
        """
        Complete curriculum for loop analysis.
        """
        all_problems = []
        all_problems.extend(self.generate_basic_loop_curriculum())
        all_problems.extend(self.generate_loop_invariant_curriculum())
        all_problems.extend(self.generate_fixpoint_convergence_curriculum())
        all_problems.extend(self.generate_loop_optimization_curriculum())
        return all_problems