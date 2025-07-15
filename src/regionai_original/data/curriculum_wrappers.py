"""
Backward compatibility wrappers for old curriculum classes.
These maintain the old API while using the new factory internally.
"""
import warnings
from typing import List
from .problem import Problem
from .curriculum_factory import create_curriculum


class DeprecatedCurriculumMixin:
    """Mixin for deprecated curriculum generators."""
    
    def __init__(self):
        warnings.warn(
            f"{self.__class__.__name__} is deprecated. "
            f"Use CurriculumFactory.create('{self.curriculum_type}') instead.",
            DeprecationWarning,
            stacklevel=2
        )


class SignAnalysisCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('sign_analysis')"""
    curriculum_type = 'sign_analysis'
    
    def generate_basic_sign_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_sign_arithmetic_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')
    
    def generate_conditional_sign_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='advanced')


class NullabilityCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('nullability')"""
    curriculum_type = 'nullability'
    
    def generate_basic_nullability_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_safe_handling_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')


class RangeCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('range_analysis')"""
    curriculum_type = 'range_analysis'
    
    def generate_array_bounds_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_loop_bounds_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')


class LoopAnalysisCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('loop_analysis')"""
    curriculum_type = 'loop_analysis'
    
    def generate_simple_loop_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_nested_loop_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')


class InterproceduralCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('interprocedural')"""
    curriculum_type = 'interprocedural'
    
    def generate_basic_interprocedural_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_recursive_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')


class ASTCurriculumGenerator(DeprecatedCurriculumMixin):
    """Deprecated: Use CurriculumFactory.create('ast_optimization')"""
    curriculum_type = 'ast_optimization'
    
    def generate_ast_optimization_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='basic')
    
    def generate_constant_folding_curriculum(self) -> List[Problem]:
        return create_curriculum(self.curriculum_type, difficulty='intermediate')


# Re-export for convenience
__all__ = [
    'SignAnalysisCurriculumGenerator',
    'NullabilityCurriculumGenerator', 
    'RangeCurriculumGenerator',
    'LoopAnalysisCurriculumGenerator',
    'InterproceduralCurriculumGenerator',
    'ASTCurriculumGenerator'
]