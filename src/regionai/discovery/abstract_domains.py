"""
Abstract domains for program property analysis.
These enable reasoning about abstract properties rather than concrete values.
"""
import ast
from typing import Any, List, Optional, Union, Set
from enum import Enum, auto
from .transformation import Transformation


# --- Sign Domain ---

class Sign(Enum):
    """Abstract domain for sign analysis."""
    POSITIVE = auto()
    NEGATIVE = auto() 
    ZERO = auto()
    TOP = auto()  # Could be any sign (unknown)
    BOTTOM = auto()  # Impossible/error state


def sign_from_constant(node: ast.AST, args: List[Any]) -> Sign:
    """Extract sign from a constant node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if node.value > 0:
            return Sign.POSITIVE
        elif node.value < 0:
            return Sign.NEGATIVE
        else:
            return Sign.ZERO
    return Sign.TOP


def sign_add(left: Sign, right: Sign) -> Sign:
    """Abstract addition for sign domain."""
    if left == Sign.BOTTOM or right == Sign.BOTTOM:
        return Sign.BOTTOM
    
    if left == Sign.TOP or right == Sign.TOP:
        return Sign.TOP
    
    if left == Sign.ZERO:
        return right
    if right == Sign.ZERO:
        return left
    
    if left == Sign.POSITIVE and right == Sign.POSITIVE:
        return Sign.POSITIVE
    if left == Sign.NEGATIVE and right == Sign.NEGATIVE:
        return Sign.NEGATIVE
    
    # POSITIVE + NEGATIVE or NEGATIVE + POSITIVE -> could be any sign
    return Sign.TOP


def sign_multiply(left: Sign, right: Sign) -> Sign:
    """Abstract multiplication for sign domain."""
    if left == Sign.BOTTOM or right == Sign.BOTTOM:
        return Sign.BOTTOM
    
    if left == Sign.ZERO or right == Sign.ZERO:
        return Sign.ZERO
    
    if left == Sign.TOP or right == Sign.TOP:
        return Sign.TOP
    
    # Both are either POSITIVE or NEGATIVE
    if left == right:  # Same sign
        return Sign.POSITIVE
    else:  # Different signs
        return Sign.NEGATIVE


def sign_negate(sign: Sign) -> Sign:
    """Abstract negation for sign domain."""
    if sign == Sign.POSITIVE:
        return Sign.NEGATIVE
    elif sign == Sign.NEGATIVE:
        return Sign.POSITIVE
    else:  # ZERO, TOP, BOTTOM
        return sign


# --- Nullability Domain ---

class Nullability(Enum):
    """Abstract domain for null analysis."""
    NOT_NULL = auto()
    NULLABLE = auto()
    DEFINITELY_NULL = auto()
    BOTTOM = auto()  # Impossible state


def nullability_from_constant(node: ast.AST, args: List[Any]) -> Nullability:
    """Extract nullability from a constant node."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return Nullability.DEFINITELY_NULL
        else:
            return Nullability.NOT_NULL
    return Nullability.NULLABLE


def nullability_join(n1: Nullability, n2: Nullability) -> Nullability:
    """Join operation for nullability lattice."""
    if n1 == Nullability.BOTTOM:
        return n2
    if n2 == Nullability.BOTTOM:
        return n1
    
    if n1 == n2:
        return n1
    
    # If one is definitely null and the other is not null, result is nullable
    if (n1 == Nullability.DEFINITELY_NULL and n2 == Nullability.NOT_NULL) or \
       (n1 == Nullability.NOT_NULL and n2 == Nullability.DEFINITELY_NULL):
        return Nullability.NULLABLE
    
    # If either is nullable, result is nullable
    if n1 == Nullability.NULLABLE or n2 == Nullability.NULLABLE:
        return Nullability.NULLABLE
    
    return Nullability.NULLABLE


# --- Abstract State Management ---

class AbstractState:
    """Tracks abstract properties of variables."""
    def __init__(self):
        self.sign_state = {}
        self.nullability_state = {}
    
    def get_sign(self, var_name: str) -> Sign:
        """Get sign property of a variable."""
        return self.sign_state.get(var_name, Sign.TOP)
    
    def set_sign(self, var_name: str, sign: Sign):
        """Set sign property of a variable."""
        self.sign_state[var_name] = sign
    
    def get_nullability(self, var_name: str) -> Nullability:
        """Get nullability property of a variable."""
        return self.nullability_state.get(var_name, Nullability.NULLABLE)
    
    def set_nullability(self, var_name: str, null: Nullability):
        """Set nullability property of a variable."""
        self.nullability_state[var_name] = null
    
    def join(self, other: 'AbstractState') -> 'AbstractState':
        """Join two abstract states (for control flow merge)."""
        result = AbstractState()
        
        # Join sign states
        all_vars = set(self.sign_state.keys()) | set(other.sign_state.keys())
        for var in all_vars:
            s1 = self.get_sign(var)
            s2 = other.get_sign(var)
            # Simple join: if they differ, go to TOP
            if s1 == s2:
                result.set_sign(var, s1)
            else:
                result.set_sign(var, Sign.TOP)
        
        # Join nullability states
        all_vars = set(self.nullability_state.keys()) | set(other.nullability_state.keys())
        for var in all_vars:
            n1 = self.get_nullability(var)
            n2 = other.get_nullability(var)
            result.set_nullability(var, nullability_join(n1, n2))
        
        return result


# Global abstract state for analysis
_abstract_state = AbstractState()


def reset_abstract_state(root: ast.AST, args: List[Any]) -> ast.AST:
    """Reset the abstract state for fresh analysis."""
    global _abstract_state
    _abstract_state = AbstractState()
    return root


def get_sign_state(node: ast.AST, args: List[Any]) -> Sign:
    """Get sign property of a variable from a Name node."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        return _abstract_state.get_sign(node.id)
    return Sign.TOP


def update_sign_state(node: ast.AST, args: List[Any]) -> ast.AST:
    """Update sign state from an assignment."""
    if isinstance(node, ast.Assign) and node.targets:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            
            # Analyze the assigned value
            if isinstance(node.value, ast.Constant):
                sign = sign_from_constant(node.value, [])
                _abstract_state.set_sign(var_name, sign)
            elif isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.USub):
                # Handle negative constants like -3
                if isinstance(node.value.operand, ast.Constant):
                    operand_sign = sign_from_constant(node.value.operand, [])
                    sign = sign_negate(operand_sign)
                    _abstract_state.set_sign(var_name, sign)
                else:
                    _abstract_state.set_sign(var_name, Sign.TOP)
            elif isinstance(node.value, ast.Name):
                # Propagate sign from another variable
                source_sign = _abstract_state.get_sign(node.value.id)
                _abstract_state.set_sign(var_name, source_sign)
            elif isinstance(node.value, ast.BinOp):
                # Analyze binary operations
                sign = abstract_sign_binop(node.value, [])
                _abstract_state.set_sign(var_name, sign)
            else:
                # Complex expression - mark as TOP for now
                _abstract_state.set_sign(var_name, Sign.TOP)
    
    return node


def abstract_sign_binop(node: ast.AST, args: List[Any]) -> Sign:
    """Compute abstract sign of a binary operation."""
    if not isinstance(node, ast.BinOp):
        return Sign.TOP
    
    # Get signs of operands
    left_sign = Sign.TOP
    right_sign = Sign.TOP
    
    if isinstance(node.left, ast.Constant):
        left_sign = sign_from_constant(node.left, [])
    elif isinstance(node.left, ast.Name):
        left_sign = _abstract_state.get_sign(node.left.id)
    
    if isinstance(node.right, ast.Constant):
        right_sign = sign_from_constant(node.right, [])
    elif isinstance(node.right, ast.Name):
        right_sign = _abstract_state.get_sign(node.right.id)
    
    # Apply abstract operation
    if isinstance(node.op, ast.Add):
        return sign_add(left_sign, right_sign)
    elif isinstance(node.op, ast.Mult):
        return sign_multiply(left_sign, right_sign)
    elif isinstance(node.op, ast.Sub):
        # a - b is like a + (-b)
        return sign_add(left_sign, sign_negate(right_sign))
    
    return Sign.TOP


def is_definitely_positive(node: ast.AST, args: List[Any]) -> bool:
    """Check if expression is definitely positive."""
    if isinstance(node, ast.Constant):
        sign = sign_from_constant(node, [])
        return sign == Sign.POSITIVE
    elif isinstance(node, ast.Name):
        sign = _abstract_state.get_sign(node.id)
        return sign == Sign.POSITIVE
    elif isinstance(node, ast.BinOp):
        sign = abstract_sign_binop(node, [])
        return sign == Sign.POSITIVE
    return False


def is_definitely_negative(node: ast.AST, args: List[Any]) -> bool:
    """Check if expression is definitely negative."""
    if isinstance(node, ast.Constant):
        sign = sign_from_constant(node, [])
        return sign == Sign.NEGATIVE
    elif isinstance(node, ast.Name):
        sign = _abstract_state.get_sign(node.id)
        return sign == Sign.NEGATIVE
    elif isinstance(node, ast.BinOp):
        sign = abstract_sign_binop(node, [])
        return sign == Sign.NEGATIVE
    return False


def is_definitely_zero(node: ast.AST, args: List[Any]) -> bool:
    """Check if expression is definitely zero."""
    if isinstance(node, ast.Constant):
        sign = sign_from_constant(node, [])
        return sign == Sign.ZERO
    elif isinstance(node, ast.Name):
        sign = _abstract_state.get_sign(node.id)
        return sign == Sign.ZERO
    return False


# --- Create Transformation objects ---

ABSTRACT_DOMAIN_PRIMITIVES = [
    # Sign analysis
    Transformation(
        name="SIGN_FROM_CONSTANT",
        operation=lambda n, a: sign_from_constant(n, a),
        input_type="ast",
        output_type="sign",
        num_args=0
    ),
    Transformation(
        name="GET_SIGN_STATE",
        operation=lambda n, a: get_sign_state(n, a),
        input_type="ast",
        output_type="sign",
        num_args=0
    ),
    Transformation(
        name="UPDATE_SIGN_STATE",
        operation=update_sign_state,
        input_type="ast",
        output_type="ast",
        num_args=0
    ),
    Transformation(
        name="ABSTRACT_SIGN_BINOP",
        operation=lambda n, a: abstract_sign_binop(n, a),
        input_type="ast",
        output_type="sign",
        num_args=0
    ),
    Transformation(
        name="IS_DEFINITELY_POSITIVE",
        operation=is_definitely_positive,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    Transformation(
        name="IS_DEFINITELY_NEGATIVE",
        operation=is_definitely_negative,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    Transformation(
        name="IS_DEFINITELY_ZERO",
        operation=is_definitely_zero,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    
    # State management
    Transformation(
        name="RESET_ABSTRACT_STATE",
        operation=reset_abstract_state,
        input_type="ast",
        output_type="ast",
        num_args=0
    ),
    
    # Nullability analysis
    Transformation(
        name="NULLABILITY_FROM_CONSTANT",
        operation=lambda n, a: nullability_from_constant(n, a),
        input_type="ast",
        output_type="nullability",
        num_args=0
    ),
]