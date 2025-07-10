"""
Data module for problems and curricula.
"""

# Core problem class
from .problem import Problem, ProblemDataType

# New curriculum factory (recommended)
from .curriculum_factory import (
    CurriculumFactory,
    CurriculumConfig,
    CurriculumGenerator,
    create_curriculum,
    list_curricula,
    create_mixed_curriculum
)

# Backward compatibility imports
from .curriculum_wrappers import (
    SignAnalysisCurriculumGenerator,
    NullabilityCurriculumGenerator,
    RangeCurriculumGenerator,
    LoopAnalysisCurriculumGenerator,
    InterproceduralCurriculumGenerator,
    ASTCurriculumGenerator
)

__all__ = [
    # Problem classes
    "Problem",
    "ProblemDataType",
    
    # New factory interface
    "CurriculumFactory",
    "CurriculumConfig",
    "CurriculumGenerator",
    "create_curriculum",
    "list_curricula",
    "create_mixed_curriculum",
    
    # Legacy generators
    "SignAnalysisCurriculumGenerator",
    "NullabilityCurriculumGenerator",
    "RangeCurriculumGenerator",
    "LoopAnalysisCurriculumGenerator",
    "InterproceduralCurriculumGenerator",
    "ASTCurriculumGenerator"
]