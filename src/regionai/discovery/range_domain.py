"""
Range abstract domain for bounds analysis.
Now uses unified base class implementation.
"""
import ast
from typing import Union, List, Any

# Import from unified implementation
from .abstract_domain_base import (
    Range as RangeBase,
    RangeDomain,
    AbstractState
)

# Re-export the base Range class
Range = RangeBase

# Special range values for compatibility
BOTTOM = Range.bottom()
TOP = Range.top()

# Legacy functions for backward compatibility

def range_from_constant(node: ast.AST) -> Range:
    """Extract range from a constant node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return RangeDomain.from_constant(node.value)
    return TOP


def range_join(r1: Range, r2: Range) -> Range:
    """Join two ranges (union)."""
    return r1.join(r2)


def range_meet(r1: Range, r2: Range) -> Range:
    """Meet two ranges (intersection)."""
    return r1.meet(r2)


def range_widen(old: Range, new: Range, iteration: int) -> Range:
    """Widening operator for ranges."""
    return old.widen(new, iteration)


def range_add(r1: Range, r2: Range) -> Range:
    """Add two ranges."""
    return RangeDomain.add(r1, r2)


def range_multiply(r1: Range, r2: Range) -> Range:
    """Multiply two ranges."""
    return RangeDomain.multiply(r1, r2)


def range_negate(r: Range) -> Range:
    """Negate a range."""
    return RangeDomain.negate(r)


def check_array_bounds(index_range: Range, array_size: int) -> str:
    """
    Check if array access is safe given index range.
    Returns error message if unsafe, empty string if safe.
    """
    if index_range.is_bottom():
        return ""  # Unreachable code
    
    # Check for negative indices
    if index_range.min < 0:
        return f"Array index may be negative: {index_range}"
    
    # Check for out of bounds
    if index_range.max >= array_size:
        return f"Array index out of bounds: {index_range} >= {array_size}"
    
    return ""  # Safe


def analyze_range(node: ast.AST, state: AbstractState = None) -> Range:
    """Analyze AST node to determine range."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return RangeDomain.from_constant(node.value)
    
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner_range = analyze_range(node.operand, state)
        return RangeDomain.negate(inner_range)
    
    elif isinstance(node, ast.BinOp):
        left_range = analyze_range(node.left, state)
        right_range = analyze_range(node.right, state)
        
        if isinstance(node.op, ast.Add):
            return RangeDomain.add(left_range, right_range)
        elif isinstance(node.op, ast.Mult):
            return RangeDomain.multiply(left_range, right_range)
    
    elif isinstance(node, ast.Name) and state:
        return state.get_range(node.id) or TOP
    
    return TOP


# Re-export everything
__all__ = [
    'Range',
    'BOTTOM', 'TOP',
    'range_from_constant',
    'range_join', 'range_meet', 'range_widen',
    'range_add', 'range_multiply', 'range_negate',
    'check_array_bounds',
    'analyze_range'
]