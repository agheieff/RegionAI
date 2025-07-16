"""Discovery module for concept learning."""

# New unified interface
from .discovery import DiscoveryEngine, discover_transformations

# Core transformation classes
from ..core.transformation import (
    Transformation,
    TransformationSequence,
    ConditionalTransformation,
    ForEachTransformation,
    PRIMITIVE_OPERATIONS,
    STRUCTURED_DATA_PRIMITIVES,
    ARITHMETIC_PRIMITIVES,
    CONTROL_PRIMITIVES
)

# Create aliases for backward compatibility
PRIMITIVE_TRANSFORMATIONS = PRIMITIVE_OPERATIONS

# Import AST primitives
from .ast_primitives import AST_PRIMITIVES

# Abstract domains
from ..core.abstract_domains import (
    Sign, Nullability,
    sign_add, sign_multiply,
    check_null_dereference,
    prove_property
)

from ..domains.code.range_domain import Range, check_array_bounds

__all__ = [
    # Main interface
    "DiscoveryEngine",
    "discover_transformations",
    
    # Transformations
    "Transformation",
    "TransformationSequence",
    "ConditionalTransformation",
    "ForEachTransformation",
    "PRIMITIVE_OPERATIONS",
    "PRIMITIVE_TRANSFORMATIONS",
    "STRUCTURED_DATA_PRIMITIVES",
    "ARITHMETIC_PRIMITIVES",
    "CONTROL_PRIMITIVES",
    "AST_PRIMITIVES",
    
    # Abstract domains
    "Sign", "Nullability", "Range",
    "sign_add", "sign_multiply",
    "check_null_dereference",
    "check_array_bounds",
    "prove_property"
]