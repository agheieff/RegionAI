"""
Abstract domains for program property analysis.
Now uses unified base class implementation.
"""
import ast
from typing import Any, List, Optional, Dict
import warnings

# Import everything from the new unified implementation
from .abstract_domain_base import (
    # Base class
    AbstractDomain,
    
    # Sign domain
    Sign, SignDomain,
    sign_add, sign_multiply,
    
    # Nullability domain
    Nullability,
    nullability_join,
    
    # Abstract state
    AbstractState,
)

# Additional legacy functions for compatibility

def sign_from_constant(node: ast.AST, args: List[Any]) -> Sign:
    """Extract sign from a constant node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return SignDomain.from_constant(node.value)
    return Sign.TOP


def sign_negate(sign: Sign) -> Sign:
    """Abstract negation for sign domain."""
    return SignDomain.negate(sign)


def nullability_from_constant(node: ast.AST, args: List[Any]) -> Nullability:
    """Extract nullability from a constant node."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return Nullability.DEFINITELY_NULL
        else:
            return Nullability.NOT_NULL
    elif isinstance(node, ast.Name) and node.id == "None":
        return Nullability.DEFINITELY_NULL
    return Nullability.NULLABLE


def nullability_meet(n1: Nullability, n2: Nullability) -> Nullability:
    """Meet operation for nullability."""
    return n1.meet(n2)


# Global state for backward compatibility
_abstract_state = AbstractState()


def reset_abstract_state():
    """Reset global abstract state."""
    global _abstract_state
    _abstract_state = AbstractState()


def update_sign_state(var: str, sign: Sign):
    """Update sign in global state."""
    _abstract_state.update_sign(var, sign)


def update_nullability_state(var: str, null: Nullability):
    """Update nullability in global state."""
    _abstract_state.update_nullability(var, null)


def get_sign_state(var: str) -> Optional[Sign]:
    """Get sign from global state."""
    return _abstract_state.get_sign(var)


def get_nullability_state(var: str) -> Optional[Nullability]:
    """Get nullability from global state."""
    return _abstract_state.get_nullability(var)


# Analysis functions

def analyze_sign(node: ast.AST) -> Optional[Sign]:
    """Analyze AST node to determine sign."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return SignDomain.from_constant(node.value)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner_sign = analyze_sign(node.operand)
        if inner_sign:
            return SignDomain.negate(inner_sign)
    elif isinstance(node, ast.BinOp):
        left_sign = analyze_sign(node.left)
        right_sign = analyze_sign(node.right)
        if left_sign and right_sign:
            if isinstance(node.op, ast.Add):
                return SignDomain.add(left_sign, right_sign)
            elif isinstance(node.op, ast.Mult):
                return SignDomain.multiply(left_sign, right_sign)
    elif isinstance(node, ast.Name):
        return get_sign_state(node.id)
    
    return None


def check_null_dereference(node: ast.AST) -> List[str]:
    """Check for potential null dereferences."""
    errors = []
    
    class NullChecker(ast.NodeVisitor):
        def visit_Attribute(self, node):
            # Check obj.attr access
            if isinstance(node.value, ast.Name):
                null_state = get_nullability_state(node.value.id)
                if null_state == Nullability.DEFINITELY_NULL:
                    errors.append(f"Null pointer exception: {node.value.id} is null")
                elif null_state == Nullability.NULLABLE:
                    errors.append(f"Potential null pointer: {node.value.id} may be null")
            self.generic_visit(node)
        
        def visit_Subscript(self, node):
            # Check obj[index] access
            if isinstance(node.value, ast.Name):
                null_state = get_nullability_state(node.value.id)
                if null_state == Nullability.DEFINITELY_NULL:
                    errors.append(f"Null pointer exception: {node.value.id} is null")
            self.generic_visit(node)
    
    NullChecker().visit(node)
    return errors


def prove_property(tree: ast.AST, initial_state: Dict[str, Sign]) -> Dict[str, bool]:
    """
    Prove sign properties about variables.
    Returns dict mapping variable names to whether property holds.
    """
    reset_abstract_state()
    
    # Set initial state
    for var, sign in initial_state.items():
        update_sign_state(var, sign)
    
    # Simple interpreter for sign analysis
    class SignProver(ast.NodeVisitor):
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                sign = analyze_sign(node.value)
                if sign:
                    update_sign_state(var_name, sign)
            self.generic_visit(node)
    
    SignProver().visit(tree)
    
    # Return which variables have definite signs
    result = {}
    for var in _abstract_state.sign_state:
        sign = _abstract_state.sign_state[var]
        result[var] = sign in [Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO]
    
    return result


# Re-export key items
__all__ = [
    'AbstractDomain',
    'Sign', 'SignDomain',
    'Nullability',
    'AbstractState',
    'sign_add', 'sign_multiply', 'sign_negate',
    'nullability_join', 'nullability_meet',
    'analyze_sign', 'check_null_dereference', 'prove_property',
    'reset_abstract_state',
    'update_sign_state', 'update_nullability_state',
]