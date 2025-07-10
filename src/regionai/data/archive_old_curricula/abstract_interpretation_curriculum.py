"""
Curriculum for teaching abstract interpretation and program property analysis.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class AbstractInterpretationCurriculumGenerator:
    """
    Teaches the AI to reason about abstract properties of programs
    without knowing concrete values.
    """
    
    def generate_sign_analysis_curriculum(self) -> List[Problem]:
        """
        Problems for discovering sign properties (positive, negative, zero).
        """
        print("Generating curriculum for sign analysis...")
        
        problems = []
        
        # Problem 1: Basic sign propagation
        code1 = """x = 5
y = -3
z = x + y"""
        properties1 = {
            'x': 'POSITIVE',
            'y': 'NEGATIVE', 
            'z': 'POSITIVE'  # 5 + (-3) = 2, which is positive
        }
        problems.append(Problem(
            name="basic_sign_propagation",
            problem_type="property_inference",
            input_data=ast.parse(code1),
            output_data=properties1,
            description="Infer sign properties through operations"
        ))
        
        # Problem 2: Sign multiplication
        code2 = """a = 10
b = -2
c = a * b
d = b * b"""
        properties2 = {
            'a': 'POSITIVE',
            'b': 'NEGATIVE',
            'c': 'NEGATIVE',  # pos * neg = neg
            'd': 'POSITIVE'   # neg * neg = pos
        }
        problems.append(Problem(
            name="sign_multiplication",
            problem_type="property_inference",
            input_data=ast.parse(code2),
            output_data=properties2,
            description="Track signs through multiplication"
        ))
        
        # Problem 3: Zero handling
        code3 = """x = 0
y = 5
z = x * y
w = x + y"""
        properties3 = {
            'x': 'ZERO',
            'y': 'POSITIVE',
            'z': 'ZERO',      # 0 * anything = 0
            'w': 'POSITIVE'   # 0 + pos = pos
        }
        problems.append(Problem(
            name="zero_properties",
            problem_type="property_inference",
            input_data=ast.parse(code3),
            output_data=properties3,
            description="Understand zero's special properties"
        ))
        
        # Problem 4: Unknown propagation
        code4 = """x = input()  # Unknown value
y = 5
z = x + y"""
        properties4 = {
            'x': 'TOP',       # Unknown
            'y': 'POSITIVE',
            'z': 'TOP'        # pos + unknown = unknown
        }
        problems.append(Problem(
            name="unknown_propagation",
            problem_type="property_inference",
            input_data=ast.parse(code4),
            output_data=properties4,
            description="Handle unknown values conservatively"
        ))
        
        # Problem 5: Chain of operations
        code5 = """a = 3
b = -2
c = a * b
d = c + a
e = d * b"""
        properties5 = {
            'a': 'POSITIVE',   # 3
            'b': 'NEGATIVE',   # -2
            'c': 'NEGATIVE',   # 3 * -2 = -6
            'd': 'NEGATIVE',   # -6 + 3 = -3
            'e': 'POSITIVE'    # -3 * -2 = 6
        }
        problems.append(Problem(
            name="operation_chain",
            problem_type="property_inference",
            input_data=ast.parse(code5),
            output_data=properties5,
            description="Track signs through operation chains"
        ))
        
        return problems
    
    def generate_nullability_analysis_curriculum(self) -> List[Problem]:
        """
        Problems for discovering null safety properties.
        """
        print("Generating curriculum for nullability analysis...")
        
        problems = []
        
        # Problem 1: Basic null tracking
        code1 = """x = None
y = 42
z = y"""
        properties1 = {
            'x': 'DEFINITELY_NULL',
            'y': 'NOT_NULL',
            'z': 'NOT_NULL'
        }
        problems.append(Problem(
            name="basic_null_tracking",
            problem_type="property_inference",
            input_data=ast.parse(code1),
            output_data=properties1,
            description="Track null and non-null values"
        ))
        
        # Problem 2: Conditional nullability
        code2 = """x = None
if condition:
    x = 42
# After if: x could be null or not"""
        properties2 = {
            'x_before_if': 'DEFINITELY_NULL',
            'x_in_if': 'NOT_NULL',
            'x_after_if': 'NULLABLE'
        }
        problems.append(Problem(
            name="conditional_nullability",
            problem_type="property_inference",
            input_data=ast.parse(code2),
            output_data=properties2,
            description="Track nullability through control flow"
        ))
        
        return problems
    
    def generate_range_analysis_curriculum(self) -> List[Problem]:
        """
        Problems for discovering value range properties.
        """
        print("Generating curriculum for range analysis...")
        
        problems = []
        
        # Problem 1: Basic range tracking
        code1 = """x = 5
y = 10
z = x + y"""
        properties1 = {
            'x': 'Range(5, 5)',
            'y': 'Range(10, 10)',
            'z': 'Range(15, 15)'
        }
        problems.append(Problem(
            name="basic_range",
            problem_type="property_inference",
            input_data=ast.parse(code1),
            output_data=properties1,
            description="Track exact value ranges"
        ))
        
        # Problem 2: Loop bounds
        code2 = """i = 0
while i < 10:
    i = i + 1"""
        properties2 = {
            'i_initial': 'Range(0, 0)',
            'i_in_loop': 'Range(0, 9)',
            'i_after_loop': 'Range(10, 10)'
        }
        problems.append(Problem(
            name="loop_bounds",
            problem_type="property_inference",
            input_data=ast.parse(code2),
            output_data=properties2,
            description="Infer loop variable bounds"
        ))
        
        return problems
    
    def generate_property_based_optimization_curriculum(self) -> List[Problem]:
        """
        Problems where abstract properties enable optimizations.
        """
        print("Generating curriculum for property-based optimization...")
        
        problems = []
        
        # Problem 1: Division by zero elimination
        code1_before = """x = 5
y = 10
if x != 0:
    z = y / x
else:
    z = 0"""
        code1_after = """x = 5
y = 10
z = y / x"""  # x is definitely positive, so != 0
        
        problems.append(Problem(
            name="division_safety",
            problem_type="transformation",
            input_data=ast.parse(code1_before),
            output_data=ast.parse(code1_after),
            description="Remove unnecessary null/zero checks"
        ))
        
        # Problem 2: Sign-based optimization
        code2_before = """x = -5
if x < 0:
    y = -x
else:
    y = x"""
        code2_after = """x = -5
y = -x"""  # x is definitely negative
        
        problems.append(Problem(
            name="sign_based_simplification",
            problem_type="transformation",
            input_data=ast.parse(code2_before),
            output_data=ast.parse(code2_after),
            description="Simplify based on sign properties"
        ))
        
        # Problem 3: Array bounds elimination
        code3_before = """size = 10
index = 5
if 0 <= index < size:
    value = array[index]
else:
    value = None"""
        code3_after = """size = 10
index = 5
value = array[index]"""  # index is in range
        
        problems.append(Problem(
            name="bounds_check_elimination",
            problem_type="transformation",
            input_data=ast.parse(code3_before),
            output_data=ast.parse(code3_after),
            description="Remove redundant bounds checks"
        ))
        
        return problems
    
    def generate_abstract_interpretation_curriculum(self) -> List[Problem]:
        """
        Complete curriculum combining all abstract domains.
        """
        all_problems = []
        all_problems.extend(self.generate_sign_analysis_curriculum())
        all_problems.extend(self.generate_nullability_analysis_curriculum())
        all_problems.extend(self.generate_range_analysis_curriculum())
        all_problems.extend(self.generate_property_based_optimization_curriculum())
        return all_problems