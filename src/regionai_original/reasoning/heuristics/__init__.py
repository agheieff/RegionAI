"""
Modular heuristic implementations for the RegionAI reasoning engine.

This package contains heuristic functions organized by category:
- ast_heuristics: AST analysis and code structure heuristics
- pattern_heuristics: Pattern detection and relationship discovery
- security_heuristics: Security vulnerability detection
- quality_heuristics: Code quality analysis (documentation, complexity)
"""

# Import all heuristics to register them with the registry
from .ast_heuristics import *
from .pattern_heuristics import *
from .security_heuristics import *
from .quality_heuristics import *

# For backward compatibility, expose all heuristics at package level
__all__ = [
    # AST heuristics
    'method_call_implies_performs',
    'sequential_nodes_imply_precedes',
    
    # Pattern heuristics
    'co_occurrence_implies_related',
    
    # Security heuristics
    'check_insecure_ssl_config',
    
    # Quality heuristics
    'check_missing_docstrings',
    'analyze_function_complexity',
]