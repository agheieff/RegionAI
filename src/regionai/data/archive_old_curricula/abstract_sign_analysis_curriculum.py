"""
Curriculum for teaching abstract sign analysis and property proving.
"""
import ast
from typing import List, Dict, Any
from .problem import Problem


class AbstractSignAnalysisCurriculumGenerator:
    """
    Teaches the AI to prove sign properties of programs without execution.
    """
    
    def generate_basic_proof_curriculum(self) -> List[Problem]:
        """
        Problems requiring basic sign property proofs.
        """
        print("Generating curriculum for basic sign proofs...")
        
        problems = []
        
        # Problem 1: Simple negative proof
        code1 = """x = input_positive_integer()
y = x * -1
z = y + -5"""
        
        proof_spec1 = {
            'z': 'NEGATIVE'  # Prove z is always negative
        }
        
        problems.append(Problem(
            name="prove_negative_simple",
            problem_type="property_proof",
            input_data={'code': ast.parse(code1), 'spec': proof_spec1},
            output_data={'z': True},  # Proof should succeed
            description="Prove z is always negative"
        ))
        
        # Problem 2: Positive product proof
        code2 = """a = input_positive_integer()
b = input_positive_integer()
c = a * b"""
        
        proof_spec2 = {
            'c': 'POSITIVE'  # Prove c is always positive
        }
        
        problems.append(Problem(
            name="prove_positive_product",
            problem_type="property_proof",
            input_data={'code': ast.parse(code2), 'spec': proof_spec2},
            output_data={'c': True},
            description="Prove product of positives is positive"
        ))
        
        # Problem 3: Sign preservation through operations
        code3 = """x = input_negative_integer()
y = x * -2
z = y + 10
w = z * 3"""
        
        proof_spec3 = {
            'y': 'POSITIVE',  # neg * neg = pos
            'z': 'POSITIVE',  # pos + pos = pos
            'w': 'POSITIVE'   # pos * pos = pos
        }
        
        problems.append(Problem(
            name="prove_sign_chain",
            problem_type="property_proof",
            input_data={'code': ast.parse(code3), 'spec': proof_spec3},
            output_data={'y': True, 'z': True, 'w': True},
            description="Prove signs through operation chain"
        ))
        
        # Problem 4: Conditional sign analysis
        code4 = """x = input_integer()
if x > 0:
    y = x * 2
else:
    y = -1"""
        
        # Cannot prove y is always positive or negative
        proof_spec4 = {
            'y': 'POSITIVE'
        }
        
        problems.append(Problem(
            name="unprovable_conditional",
            problem_type="property_proof",
            input_data={'code': ast.parse(code4), 'spec': proof_spec4},
            output_data={'y': False},  # Cannot be proven
            description="Recognize unprovable properties"
        ))
        
        return problems
    
    def generate_complex_proof_curriculum(self) -> List[Problem]:
        """
        Problems requiring complex sign reasoning.
        """
        print("Generating curriculum for complex sign proofs...")
        
        problems = []
        
        # Problem 1: Absolute value reasoning
        code1 = """x = input_integer()
if x < 0:
    abs_x = -x
else:
    abs_x = x
result = abs_x + 1"""
        
        proof_spec1 = {
            'result': 'POSITIVE'  # Always positive (abs + positive)
        }
        
        problems.append(Problem(
            name="prove_abs_positive",
            problem_type="property_proof",
            input_data={'code': ast.parse(code1), 'spec': proof_spec1},
            output_data={'result': True},
            description="Prove absolute value + 1 is positive"
        ))
        
        # Problem 2: Loop invariant
        code2 = """sum = 0
i = 1
while i <= 10:
    sum = sum + i
    i = i + 1"""
        
        proof_spec2 = {
            'sum': 'POSITIVE',  # Sum of positives
            'i': 'POSITIVE'     # Loop counter
        }
        
        problems.append(Problem(
            name="prove_loop_invariant",
            problem_type="property_proof",
            input_data={'code': ast.parse(code2), 'spec': proof_spec2},
            output_data={'sum': True, 'i': True},
            description="Prove loop maintains positive invariants"
        ))
        
        # Problem 3: Error detection
        code3 = """x = input_positive_integer()
y = 0
z = x / y"""  # Division by zero!
        
        proof_spec3 = {
            'z': 'BOTTOM'  # Should detect error
        }
        
        problems.append(Problem(
            name="detect_division_error",
            problem_type="property_proof",
            input_data={'code': ast.parse(code3), 'spec': proof_spec3},
            output_data={'z': True},
            description="Detect division by zero error"
        ))
        
        return problems
    
    def generate_security_proof_curriculum(self) -> List[Problem]:
        """
        Problems proving security-relevant properties.
        """
        print("Generating curriculum for security proofs...")
        
        problems = []
        
        # Problem 1: Array bounds safety
        code1 = """array_size = 10
index = input_positive_integer()
if index < array_size:
    safe_index = index
else:
    safe_index = 0"""
        
        # Prove safe_index is always valid (non-negative)
        proof_spec1 = {
            'safe_index': 'NON_NEGATIVE'  # >= 0
        }
        
        problems.append(Problem(
            name="prove_bounds_safety",
            problem_type="property_proof",
            input_data={'code': ast.parse(code1), 'spec': proof_spec1},
            output_data={'safe_index': True},
            description="Prove array access is safe"
        ))
        
        # Problem 2: Integer overflow detection
        code2 = """x = input_large_positive()  # Near MAX_INT
y = input_large_positive()
z = x + y"""  # Might overflow!
        
        # Cannot prove z is positive (might wrap to negative)
        proof_spec2 = {
            'z': 'POSITIVE'
        }
        
        problems.append(Problem(
            name="detect_overflow_risk",
            problem_type="property_proof",
            input_data={'code': ast.parse(code2), 'spec': proof_spec2},
            output_data={'z': False},  # Cannot prove due to overflow
            description="Recognize integer overflow risk"
        ))
        
        return problems
    
    def generate_optimization_enabling_proofs(self) -> List[Problem]:
        """
        Proofs that enable optimizations.
        """
        print("Generating curriculum for optimization-enabling proofs...")
        
        problems = []
        
        # Problem 1: Division safety optimization
        code1 = """x = 10
y = 5
if y != 0:
    result = x / y
else:
    result = 0"""
        
        # Can prove y != 0, so check can be removed
        proof_spec1 = {
            'y': 'POSITIVE'  # Implies != 0
        }
        
        optimization1 = """x = 10
y = 5
result = x / y"""
        
        problems.append(Problem(
            name="prove_division_safe",
            problem_type="proof_enables_optimization",
            input_data={'code': ast.parse(code1), 'spec': proof_spec1},
            output_data={'proof': {'y': True}, 'optimized': ast.parse(optimization1)},
            description="Prove division check unnecessary"
        ))
        
        # Problem 2: Sign check elimination
        code2 = """x = abs(input_integer())
y = x + 10
if y > 0:
    z = 100
else:
    z = 0"""
        
        proof_spec2 = {
            'y': 'POSITIVE'  # abs() + positive = positive
        }
        
        optimization2 = """x = abs(input_integer())
y = x + 10
z = 100"""
        
        problems.append(Problem(
            name="prove_sign_check_redundant",
            problem_type="proof_enables_optimization",
            input_data={'code': ast.parse(code2), 'spec': proof_spec2},
            output_data={'proof': {'y': True}, 'optimized': ast.parse(optimization2)},
            description="Prove sign check is redundant"
        ))
        
        return problems
    
    def generate_abstract_sign_curriculum(self) -> List[Problem]:
        """
        Complete curriculum for abstract sign analysis.
        """
        all_problems = []
        all_problems.extend(self.generate_basic_proof_curriculum())
        all_problems.extend(self.generate_complex_proof_curriculum())
        all_problems.extend(self.generate_security_proof_curriculum())
        all_problems.extend(self.generate_optimization_enabling_proofs())
        return all_problems