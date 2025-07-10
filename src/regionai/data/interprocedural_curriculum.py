"""
Curriculum for teaching interprocedural analysis.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class InterproceduralCurriculumGenerator:
    """
    Teaches the AI to analyze programs across function boundaries.
    """
    
    def generate_basic_interprocedural_curriculum(self) -> List[Problem]:
        """
        Basic problems requiring cross-function analysis.
        """
        print("Generating curriculum for basic interprocedural analysis...")
        
        problems = []
        
        # Problem 1: Simple null propagation
        code1 = """def get_user_input():
    # This function might return None
    return None

def process_user():
    user = get_user_input()
    print(user.name)  # Null pointer exception!"""
        
        expected_analysis1 = {
            'errors': ['Null pointer exception: user.name'],
            'function_summaries': {
                'get_user_input': {'returns': 'DEFINITELY_NULL'},
                'process_user': {'has_error': True}
            }
        }
        
        problems.append(Problem(
            name="null_propagation_simple",
            problem_type="interprocedural",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Detect null propagation across functions"
        ))
        
        # Problem 2: Conditional null return
        code2 = """def find_user(user_id):
    if user_id > 0:
        return {"name": "Alice", "id": user_id}
    else:
        return None

def display_user(uid):
    user = find_user(uid)
    print(user["name"])  # Potential null pointer!"""
        
        expected_analysis2 = {
            'warnings': ['Potential null pointer: user["name"]'],
            'function_summaries': {
                'find_user': {'returns': 'NULLABLE'},
                'display_user': {'has_warning': True}
            }
        }
        
        problems.append(Problem(
            name="conditional_null_return",
            problem_type="interprocedural",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Handle functions that may return null"
        ))
        
        # Problem 3: Safe with null check
        code3 = """def get_optional_value():
    # May return None
    return None

def safe_process():
    value = get_optional_value()
    if value is not None:
        print(value.data)  # Safe!
    else:
        print("No value available")"""
        
        expected_analysis3 = {
            'errors': [],
            'warnings': [],
            'function_summaries': {
                'get_optional_value': {'returns': 'NULLABLE'},
                'safe_process': {'safe': True}
            }
        }
        
        problems.append(Problem(
            name="safe_null_handling",
            problem_type="interprocedural",
            input_data={'code': ast.parse(code3)},
            output_data=expected_analysis3,
            description="Recognize safe null handling"
        ))
        
        return problems
    
    def generate_range_propagation_curriculum(self) -> List[Problem]:
        """
        Problems for range analysis across functions.
        """
        print("Generating curriculum for interprocedural range analysis...")
        
        problems = []
        
        # Problem 1: Array bounds across functions
        code1 = """def get_index():
    return 15  # Out of bounds!

def access_array():
    arr = [1, 2, 3, 4, 5]  # Size 5
    index = get_index()
    value = arr[index]  # Index out of bounds!"""
        
        expected_analysis1 = {
            'errors': ['Array index out of bounds: index=15, array_size=5'],
            'function_summaries': {
                'get_index': {'returns': 'Range[15, 15]'},
                'access_array': {'has_bounds_error': True}
            }
        }
        
        problems.append(Problem(
            name="bounds_check_interprocedural",
            problem_type="interprocedural_range",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Detect bounds errors across functions"
        ))
        
        # Problem 2: Safe bounded return
        code2 = """def get_safe_index(max_val):
    # Returns value in [0, max_val-1]
    return min(max_val - 1, 5)

def safe_access():
    arr = [0] * 10
    index = get_safe_index(10)
    value = arr[index]  # Safe!"""
        
        expected_analysis2 = {
            'errors': [],
            'function_summaries': {
                'get_safe_index': {'returns': 'Range[0, 9]'},
                'safe_access': {'safe': True}
            }
        }
        
        problems.append(Problem(
            name="safe_bounds_interprocedural",
            problem_type="interprocedural_range",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Verify safe bounds across functions"
        ))
        
        return problems
    
    def generate_context_sensitive_curriculum(self) -> List[Problem]:
        """
        Problems requiring context-sensitive analysis.
        """
        print("Generating curriculum for context-sensitive analysis...")
        
        problems = []
        
        # Problem 1: Different contexts, different results
        code1 = """def abs_value(x):
    if x < 0:
        return -x
    else:
        return x

def caller1():
    result = abs_value(-5)  # Returns 5 (POSITIVE)
    return result

def caller2():
    result = abs_value(10)  # Returns 10 (POSITIVE)
    return result"""
        
        expected_analysis1 = {
            'context_summaries': {
                'abs_value(-5)': {'returns': 'POSITIVE'},
                'abs_value(10)': {'returns': 'POSITIVE'}
            },
            'function_results': {
                'caller1': 'POSITIVE',
                'caller2': 'POSITIVE'
            }
        }
        
        problems.append(Problem(
            name="context_sensitive_abs",
            problem_type="context_sensitive",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Analyze function in different contexts"
        ))
        
        # Problem 2: Context affects safety
        code2 = """def divide(a, b):
    return a / b

def safe_caller():
    result = divide(10, 5)  # Safe: b=5 != 0
    return result

def unsafe_caller():
    result = divide(10, 0)  # Error: division by zero!
    return result"""
        
        expected_analysis2 = {
            'errors': ['Division by zero in unsafe_caller'],
            'context_summaries': {
                'divide(10, 5)': {'safe': True},
                'divide(10, 0)': {'error': 'division_by_zero'}
            }
        }
        
        problems.append(Problem(
            name="context_sensitive_division",
            problem_type="context_sensitive",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Context determines safety"
        ))
        
        return problems
    
    def generate_recursive_function_curriculum(self) -> List[Problem]:
        """
        Problems involving recursive functions.
        """
        print("Generating curriculum for recursive function analysis...")
        
        problems = []
        
        # Problem 1: Simple recursive factorial
        code1 = """def factorial(n):
    if n <= 0:
        return 1  # Base case: POSITIVE
    else:
        return n * factorial(n - 1)  # Recursive case

def compute():
    result = factorial(5)
    return result"""
        
        expected_analysis1 = {
            'function_summaries': {
                'factorial': {
                    'returns': 'POSITIVE',  # Always returns positive
                    'recursive': True
                }
            },
            'recursive_functions': ['factorial']
        }
        
        problems.append(Problem(
            name="recursive_factorial",
            problem_type="recursive",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Analyze recursive function"
        ))
        
        # Problem 2: Mutual recursion
        code2 = """def is_even(n):
    if n == 0:
        return True
    else:
        return is_odd(n - 1)

def is_odd(n):
    if n == 0:
        return False
    else:
        return is_even(n - 1)

def check():
    result = is_even(4)
    return result"""
        
        expected_analysis2 = {
            'recursive_functions': ['is_even', 'is_odd'],
            'mutual_recursion': True,
            'call_cycles': [['is_even', 'is_odd', 'is_even']]
        }
        
        problems.append(Problem(
            name="mutual_recursion",
            problem_type="recursive",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Handle mutual recursion"
        ))
        
        return problems
    
    def generate_whole_program_curriculum(self) -> List[Problem]:
        """
        Complex whole-program analysis problems.
        """
        print("Generating curriculum for whole-program analysis...")
        
        problems = []
        
        # Problem 1: Multi-function data flow
        code1 = """def validate_input(data):
    if data is None:
        return None
    if len(data) == 0:
        return None
    return data.strip()

def process_data(raw_data):
    validated = validate_input(raw_data)
    # validated could be None!
    tokens = validated.split()  # Potential null pointer
    return tokens

def main():
    result = process_data(None)
    return result"""
        
        expected_analysis1 = {
            'errors': ['Potential null pointer: validated.split()'],
            'data_flow': {
                'None → validate_input → None → process_data → ERROR'
            }
        }
        
        problems.append(Problem(
            name="multi_function_flow",
            problem_type="whole_program",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Track data through multiple functions"
        ))
        
        # Problem 2: Library-like code with multiple entry points
        code2 = """# Library functions
def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b

def unsafe_divide(a, b):
    return a / b  # No check!

# Client code
def calculation1():
    return safe_divide(10, 0)  # Returns 0

def calculation2():
    return unsafe_divide(10, 0)  # Division by zero!"""
        
        expected_analysis2 = {
            'errors': ['Division by zero in calculation2'],
            'entry_points': ['calculation1', 'calculation2'],
            'safe_functions': ['safe_divide', 'calculation1'],
            'unsafe_functions': ['unsafe_divide', 'calculation2']
        }
        
        problems.append(Problem(
            name="library_analysis",
            problem_type="whole_program",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Analyze library with multiple entry points"
        ))
        
        return problems
    
    def generate_interprocedural_curriculum(self) -> List[Problem]:
        """
        Complete curriculum for interprocedural analysis.
        """
        all_problems = []
        all_problems.extend(self.generate_basic_interprocedural_curriculum())
        all_problems.extend(self.generate_range_propagation_curriculum())
        all_problems.extend(self.generate_context_sensitive_curriculum())
        all_problems.extend(self.generate_recursive_function_curriculum())
        all_problems.extend(self.generate_whole_program_curriculum())
        return all_problems