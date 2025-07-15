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


# Note: Global state has been removed. Use AnalysisContext for all state management.


# Analysis functions

def analyze_sign(node: ast.AST, context=None) -> Optional[Sign]:
    """
    Analyze AST node to determine sign.
    
    Args:
        node: AST node to analyze
        context: Optional AnalysisContext. If not provided, uses global state (deprecated).
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return SignDomain.from_constant(node.value)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner_sign = analyze_sign(node.operand, context)
        if inner_sign:
            return SignDomain.negate(inner_sign)
    elif isinstance(node, ast.BinOp):
        left_sign = analyze_sign(node.left, context)
        right_sign = analyze_sign(node.right, context)
        if left_sign and right_sign:
            if isinstance(node.op, ast.Add):
                return SignDomain.add(left_sign, right_sign)
            elif isinstance(node.op, ast.Mult):
                return SignDomain.multiply(left_sign, right_sign)
    elif isinstance(node, ast.Name):
        if context:
            return context.abstract_state.get_sign(node.id)
        else:
            # Fallback to global state (deprecated)
            return get_sign_state(node.id)
    
    return None


def check_null_dereference(node: ast.AST, context=None) -> List[str]:
    """
    Check for potential null dereferences.
    
    Args:
        node: AST node to check
        context: Optional AnalysisContext. If not provided, uses global state (deprecated).
    """
    errors = []
    
    class NullChecker(ast.NodeVisitor):
        def __init__(self, context):
            self.context = context
            
        def visit_Attribute(self, node):
            # Check obj.attr access
            if isinstance(node.value, ast.Name):
                if self.context:
                    null_state = self.context.abstract_state.get_nullability(node.value.id)
                else:
                    null_state = get_nullability_state(node.value.id)
                
                    
                if null_state == Nullability.DEFINITELY_NULL:
                    errors.append(f"Null pointer exception: {node.value.id} is null")
                elif null_state == Nullability.NULLABLE:
                    errors.append(f"Potential null pointer: {node.value.id} may be null")
            self.generic_visit(node)
        
        def visit_Subscript(self, node):
            # Check obj[index] access
            if isinstance(node.value, ast.Name):
                if self.context:
                    null_state = self.context.abstract_state.get_nullability(node.value.id)
                else:
                    null_state = get_nullability_state(node.value.id)
                    
                if null_state == Nullability.DEFINITELY_NULL:
                    errors.append(f"Null pointer exception: {node.value.id} is null")
            self.generic_visit(node)
    
    NullChecker(context).visit(node)
    return errors


def prove_property(tree: ast.AST, initial_state: Dict[str, Sign], context=None) -> Dict[str, bool]:
    """
    Prove sign properties about variables.
    Returns dict mapping variable names to whether property holds.
    
    Args:
        tree: AST to analyze
        initial_state: Initial sign values for variables
        context: Optional AnalysisContext. If not provided, uses global state (deprecated).
    """
    # Use provided context or create a new one
    if context is None:
        # Create temporary context for backward compatibility
        from ..analysis.context import AnalysisContext
        context = AnalysisContext()
        warnings.warn(
            "prove_property() without context is deprecated. Pass an AnalysisContext.",
            DeprecationWarning,
            stacklevel=2
        )
    
    # Reset context state
    context.reset()
    
    # Set initial state
    for var, sign in initial_state.items():
        context.abstract_state.update_sign(var, sign)
    
    # Simple interpreter for sign analysis
    class SignProver(ast.NodeVisitor):
        def __init__(self, ctx):
            self.context = ctx
            
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                sign = analyze_sign(node.value, self.context)
                if sign:
                    self.context.abstract_state.update_sign(var_name, sign)
            self.generic_visit(node)
    
    SignProver(context).visit(tree)
    
    # Return which variables have definite signs
    result = {}
    for var in context.abstract_state.sign_state:
        sign = context.abstract_state.sign_state[var]
        result[var] = sign in [Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO]
    
    return result


# New context-aware analysis functions (preferred)
def analyze_assignment(node: ast.Assign, context, abstract_state=None):
    """
    Analyze an assignment statement and update the abstract state.
    
    Args:
        node: Assignment AST node
        context: AnalysisContext for configuration and error reporting
        abstract_state: Optional AbstractState to update (uses context.abstract_state if not provided)
    """
    # Use provided abstract_state or fall back to context's
    state = abstract_state if abstract_state is not None else context.abstract_state
    
    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        var_name = node.targets[0].id
        
        # Create a temporary wrapper for analyze_sign if using external state
        if abstract_state is not None:
            class TempContext:
                def __init__(self, state, ctx):
                    self.abstract_state = state
                    self.config = ctx.config
            temp_ctx = TempContext(state, context)
            sign = analyze_sign(node.value, temp_ctx)
        else:
            # Use original context
            sign = analyze_sign(node.value, context)
            
        if sign:
            state.update_sign(var_name, sign)
        
        # Analyze nullability
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            state.update_nullability(var_name, Nullability.DEFINITELY_NULL)
        elif isinstance(node.value, ast.Name) and node.value.id == "None":
            state.update_nullability(var_name, Nullability.DEFINITELY_NULL)
        else:
            # For now, assume non-null for other values
            state.update_nullability(var_name, Nullability.NOT_NULL)


# Re-export key items
__all__ = [
    'AbstractDomain',
    'Sign', 'SignDomain',
    'Nullability',
    'AbstractState',
    'sign_add', 'sign_multiply', 'sign_negate',
    'nullability_join', 'nullability_meet',
    'analyze_sign', 'check_null_dereference', 'prove_property',
    'analyze_assignment'  # Context-aware function
]
