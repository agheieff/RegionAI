"""
Curriculum for teaching null safety analysis.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class NullabilityAnalysisCurriculumGenerator:
    """
    Teaches the AI to track null values and detect null pointer exceptions.
    """
    
    def generate_basic_nullability_curriculum(self) -> List[Problem]:
        """
        Basic null tracking problems.
        """
        print("Generating curriculum for basic nullability analysis...")
        
        problems = []
        
        # Problem 1: Simple null assignment and check
        code1 = """x = None
y = 42
z = y"""
        
        expected_nullability1 = {
            'x': 'DEFINITELY_NULL',
            'y': 'NOT_NULL',
            'z': 'NOT_NULL'
        }
        
        problems.append(Problem(
            name="basic_null_tracking",
            problem_type="nullability_analysis",
            input_data={'code': ast.parse(code1)},
            output_data=expected_nullability1,
            description="Track null and non-null values"
        ))
        
        # Problem 2: Null propagation
        code2 = """a = None
b = a
c = b"""
        
        expected_nullability2 = {
            'a': 'DEFINITELY_NULL',
            'b': 'DEFINITELY_NULL',
            'c': 'DEFINITELY_NULL'
        }
        
        problems.append(Problem(
            name="null_propagation",
            problem_type="nullability_analysis",
            input_data={'code': ast.parse(code2)},
            output_data=expected_nullability2,
            description="Propagate null through assignments"
        ))
        
        # Problem 3: Function calls produce nullable
        code3 = """x = get_user()
y = process_data()
z = 123"""
        
        expected_nullability3 = {
            'x': 'NULLABLE',  # Function might return null
            'y': 'NULLABLE',
            'z': 'NOT_NULL'
        }
        
        problems.append(Problem(
            name="function_call_nullable",
            problem_type="nullability_analysis",
            input_data={'code': ast.parse(code3)},
            output_data=expected_nullability3,
            description="Functions may return null"
        ))
        
        return problems
    
    def generate_null_dereference_detection_curriculum(self) -> List[Problem]:
        """
        Problems for detecting null pointer exceptions.
        """
        print("Generating curriculum for null dereference detection...")
        
        problems = []
        
        # Problem 1: Definite null pointer exception
        code1 = """obj = None
value = obj.field"""
        
        expected_errors1 = {
            'errors': ['Null pointer exception: accessing attribute on null object'],
            'line': 2
        }
        
        problems.append(Problem(
            name="definite_null_pointer",
            problem_type="null_safety",
            input_data={'code': ast.parse(code1)},
            output_data=expected_errors1,
            description="Detect definite null pointer exception"
        ))
        
        # Problem 2: Potential null pointer
        code2 = """obj = get_object()
value = obj.field"""
        
        expected_errors2 = {
            'warnings': ['Potential null pointer: object might be null'],
            'line': 2
        }
        
        problems.append(Problem(
            name="potential_null_pointer",
            problem_type="null_safety",
            input_data={'code': ast.parse(code2)},
            output_data=expected_errors2,
            description="Warn about potential null pointer"
        ))
        
        # Problem 3: Safe after null check
        code3 = """obj = get_object()
if obj is not None:
    value = obj.field
else:
    value = None"""
        
        expected_errors3 = {
            'errors': [],
            'warnings': []
        }
        
        problems.append(Problem(
            name="safe_after_check",
            problem_type="null_safety",
            input_data={'code': ast.parse(code3)},
            output_data=expected_errors3,
            description="No error after null check"
        ))
        
        # Problem 4: Array indexing null
        code4 = """arr = None
value = arr[0]"""
        
        expected_errors4 = {
            'errors': ['Null pointer exception: indexing null object'],
            'line': 2
        }
        
        problems.append(Problem(
            name="null_array_index",
            problem_type="null_safety",
            input_data={'code': ast.parse(code4)},
            output_data=expected_errors4,
            description="Detect null array indexing"
        ))
        
        return problems
    
    def generate_null_safety_in_loops_curriculum(self) -> List[Problem]:
        """
        Null analysis in loops with fixpoint.
        """
        print("Generating curriculum for null safety in loops...")
        
        problems = []
        
        # Problem 1: Loop that may set to null
        code1 = """obj = create_object()
i = 0
while i < 10:
    if i == 5:
        obj = None
    i = i + 1
value = obj.field"""
        
        expected_analysis1 = {
            'loop_exit_nullability': {
                'obj': 'NULLABLE'  # Could be null after loop
            },
            'errors': ['Potential null pointer: object might be null']
        }
        
        problems.append(Problem(
            name="loop_nullable",
            problem_type="loop_null_analysis",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Track nullability through loops"
        ))
        
        # Problem 2: Loop invariant non-null
        code2 = """items = get_non_empty_list()
for item in items:
    value = item.process()"""
        
        expected_analysis2 = {
            'loop_invariant': {
                'item': 'NOT_NULL'  # List iteration produces non-null
            },
            'errors': []
        }
        
        problems.append(Problem(
            name="loop_invariant_non_null",
            problem_type="loop_null_analysis",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Loop iteration maintains non-null"
        ))
        
        return problems
    
    def generate_interprocedural_null_curriculum(self) -> List[Problem]:
        """
        Null analysis across function boundaries.
        """
        print("Generating curriculum for interprocedural null analysis...")
        
        problems = []
        
        # Problem 1: Function guaranteed to return non-null
        code1 = """def get_default():
    return "default"

value = get_default()
length = len(value)"""
        
        expected_analysis1 = {
            'function_contracts': {
                'get_default': 'NOT_NULL'
            },
            'errors': []
        }
        
        problems.append(Problem(
            name="non_null_return",
            problem_type="interprocedural_null",
            input_data={'code': ast.parse(code1)},
            output_data=expected_analysis1,
            description="Function returns non-null"
        ))
        
        # Problem 2: Function may return null
        code2 = """def find_user(id):
    if id in database:
        return database[id]
    return None

user = find_user(123)
name = user.name"""
        
        expected_analysis2 = {
            'function_contracts': {
                'find_user': 'NULLABLE'
            },
            'errors': ['Potential null pointer: object might be null']
        }
        
        problems.append(Problem(
            name="nullable_return",
            problem_type="interprocedural_null",
            input_data={'code': ast.parse(code2)},
            output_data=expected_analysis2,
            description="Function may return null"
        ))
        
        return problems
    
    def generate_nullability_optimization_curriculum(self) -> List[Problem]:
        """
        Null analysis enabling optimizations.
        """
        print("Generating curriculum for null-based optimizations...")
        
        problems = []
        
        # Problem 1: Remove redundant null check
        code1 = """x = "hello"
if x is not None:
    y = x.upper()
else:
    y = "" """
        
        optimized1 = """x = "hello"
y = x.upper()"""
        
        problems.append(Problem(
            name="redundant_null_check",
            problem_type="null_optimization",
            input_data={'code': ast.parse(code1), 'nullability': {'x': 'NOT_NULL'}},
            output_data={'optimized': ast.parse(optimized1)},
            description="Remove redundant null check"
        ))
        
        # Problem 2: Hoist null check out of loop
        code2 = """obj = get_stable_object()
i = 0
while i < 100:
    if obj is not None:
        obj.update(i)
    i = i + 1"""
        
        optimized2 = """obj = get_stable_object()
if obj is not None:
    i = 0
    while i < 100:
        obj.update(i)
        i = i + 1"""
        
        problems.append(Problem(
            name="hoist_null_check",
            problem_type="null_optimization",
            input_data={'code': ast.parse(code2)},
            output_data={'optimized': ast.parse(optimized2)},
            description="Hoist invariant null check"
        ))
        
        return problems
    
    def generate_nullability_curriculum(self) -> List[Problem]:
        """
        Complete curriculum for nullability analysis.
        """
        all_problems = []
        all_problems.extend(self.generate_basic_nullability_curriculum())
        all_problems.extend(self.generate_null_dereference_detection_curriculum())
        all_problems.extend(self.generate_null_safety_in_loops_curriculum())
        all_problems.extend(self.generate_interprocedural_null_curriculum())
        all_problems.extend(self.generate_nullability_optimization_curriculum())
        return all_problems