"""
Range abstract domain for bounds analysis.
"""
import ast
from typing import Optional, Tuple, Union, List, Any
from dataclasses import dataclass
import math


@dataclass
class Range:
    """
    Represents an interval [min, max].
    Special values: -inf, +inf for unbounded ranges.
    """
    min: Union[int, float]
    max: Union[int, float]
    
    def __post_init__(self):
        # Ensure min <= max
        if self.min > self.max:
            self.min, self.max = self.max, self.min
    
    def is_bottom(self) -> bool:
        """Check if this is the bottom element (empty range)."""
        return self.min > self.max
    
    def is_top(self) -> bool:
        """Check if this is the top element (unbounded)."""
        return self.min == float('-inf') and self.max == float('inf')
    
    def contains(self, value: Union[int, float]) -> bool:
        """Check if value is in range."""
        return self.min <= value <= self.max
    
    def __str__(self):
        if self.is_bottom():
            return "⊥"
        elif self.is_top():
            return "[-∞, +∞]"
        else:
            min_str = "-∞" if self.min == float('-inf') else str(self.min)
            max_str = "+∞" if self.max == float('inf') else str(self.max)
            return f"[{min_str}, {max_str}]"
    
    def __repr__(self):
        return self.__str__()


# Special range values
BOTTOM = Range(1, 0)  # Empty range
TOP = Range(float('-inf'), float('inf'))  # Full range


def range_from_constant(node: ast.AST) -> Range:
    """Extract range from a constant node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Range(node.value, node.value)
    return TOP


def range_join(r1: Range, r2: Range) -> Range:
    """Join two ranges (union)."""
    if r1.is_bottom():
        return r2
    if r2.is_bottom():
        return r1
    
    return Range(min(r1.min, r2.min), max(r1.max, r2.max))


def range_meet(r1: Range, r2: Range) -> Range:
    """Meet two ranges (intersection)."""
    if r1.is_bottom() or r2.is_bottom():
        return BOTTOM
    
    new_min = max(r1.min, r2.min)
    new_max = min(r1.max, r2.max)
    
    if new_min > new_max:
        return BOTTOM
    
    return Range(new_min, new_max)


def range_widen(old: Range, new: Range, iteration: int) -> Range:
    """
    Widening operator for ranges.
    If bounds keep growing, jump to infinity.
    """
    WIDENING_THRESHOLD = 3
    
    if old == new:
        return old
    
    if iteration >= WIDENING_THRESHOLD:
        # Aggressive widening
        widened_min = float('-inf') if new.min < old.min else old.min
        widened_max = float('inf') if new.max > old.max else old.max
        return Range(widened_min, widened_max)
    
    # Before threshold, allow some growth
    return range_join(old, new)


# --- Range Arithmetic ---

def range_add(r1: Range, r2: Range) -> Range:
    """Add two ranges: [a,b] + [c,d] = [a+c, b+d]."""
    if r1.is_bottom() or r2.is_bottom():
        return BOTTOM
    
    # Handle infinities carefully
    new_min = r1.min + r2.min if r1.min != float('-inf') and r2.min != float('-inf') else float('-inf')
    new_max = r1.max + r2.max if r1.max != float('inf') and r2.max != float('inf') else float('inf')
    
    return Range(new_min, new_max)


def range_subtract(r1: Range, r2: Range) -> Range:
    """Subtract ranges: [a,b] - [c,d] = [a-d, b-c]."""
    if r1.is_bottom() or r2.is_bottom():
        return BOTTOM
    
    # Subtraction reverses the bounds of r2
    new_min = r1.min - r2.max if r1.min != float('-inf') and r2.max != float('inf') else float('-inf')
    new_max = r1.max - r2.min if r1.max != float('inf') and r2.min != float('-inf') else float('inf')
    
    return Range(new_min, new_max)


def range_multiply(r1: Range, r2: Range) -> Range:
    """Multiply ranges - need to consider all corner cases."""
    if r1.is_bottom() or r2.is_bottom():
        return BOTTOM
    
    # Compute all possible products
    products = [
        r1.min * r2.min,
        r1.min * r2.max,
        r1.max * r2.min,
        r1.max * r2.max
    ]
    
    # Filter out infinity calculations that would be NaN
    valid_products = []
    for p in products:
        if not (math.isnan(p) or math.isinf(p)):
            valid_products.append(p)
    
    if not valid_products:
        return TOP
    
    return Range(min(valid_products), max(valid_products))


def range_divide(r1: Range, r2: Range) -> Range:
    """Division - must handle division by zero."""
    if r1.is_bottom() or r2.is_bottom():
        return BOTTOM
    
    # Check if divisor range contains zero
    if r2.contains(0):
        # Conservative: could divide by zero
        return TOP
    
    # Safe division
    quotients = []
    for a in [r1.min, r1.max]:
        for b in [r2.min, r2.max]:
            if b != 0:
                quotients.append(a / b)
    
    if not quotients:
        return TOP
    
    return Range(min(quotients), max(quotients))


# --- Comparison Operations ---

def range_less_than(r1: Range, r2: Range) -> Optional[bool]:
    """
    Check if r1 < r2.
    Returns True if definitely true, False if definitely false, None if unknown.
    """
    if r1.is_bottom() or r2.is_bottom():
        return None
    
    if r1.max < r2.min:
        return True
    elif r1.min >= r2.max:
        return False
    else:
        return None  # Ranges overlap


def range_less_equal(r1: Range, r2: Range) -> Optional[bool]:
    """Check if r1 <= r2."""
    if r1.is_bottom() or r2.is_bottom():
        return None
    
    if r1.max <= r2.min:
        return True
    elif r1.min > r2.max:
        return False
    else:
        return None


# --- Array Bounds Checking ---

def check_array_bounds(index_range: Range, array_size: int) -> str:
    """
    Check if array access is safe.
    Returns error message if bounds violation detected.
    """
    if index_range.is_bottom():
        return "Index has impossible value"
    
    # Check lower bound
    if index_range.min < 0:
        if index_range.max < 0:
            return "Array index is always negative"
        else:
            return "Array index might be negative"
    
    # Check upper bound
    if index_range.min >= array_size:
        return f"Array index always out of bounds (>= {array_size})"
    elif index_range.max >= array_size:
        return f"Array index might be out of bounds (>= {array_size})"
    
    # Safe access
    return ""


# --- Integration with Abstract State ---

class RangeState:
    """Tracks range information for variables."""
    def __init__(self):
        self.ranges = {}
    
    def get_range(self, var_name: str) -> Range:
        """Get range for a variable."""
        return self.ranges.get(var_name, TOP)
    
    def set_range(self, var_name: str, r: Range):
        """Set range for a variable."""
        self.ranges[var_name] = r
    
    def join(self, other: 'RangeState') -> 'RangeState':
        """Join two range states."""
        result = RangeState()
        
        all_vars = set(self.ranges.keys()) | set(other.ranges.keys())
        for var in all_vars:
            r1 = self.get_range(var)
            r2 = other.get_range(var)
            result.set_range(var, range_join(r1, r2))
        
        return result
    
    def widen(self, other: 'RangeState', iteration: int) -> 'RangeState':
        """Apply widening to range state."""
        result = RangeState()
        
        all_vars = set(self.ranges.keys()) | set(other.ranges.keys())
        for var in all_vars:
            old_range = self.get_range(var)
            new_range = other.get_range(var)
            result.set_range(var, range_widen(old_range, new_range, iteration))
        
        return result


def analyze_range_assignment(target_var: str, value_node: ast.AST, state: RangeState):
    """Analyze assignment for range information."""
    if isinstance(value_node, ast.Constant):
        r = range_from_constant(value_node)
        state.set_range(target_var, r)
    
    elif isinstance(value_node, ast.Name):
        # Propagate range
        source_range = state.get_range(value_node.id)
        state.set_range(target_var, source_range)
    
    elif isinstance(value_node, ast.BinOp):
        # Analyze binary operation
        left_range = get_node_range(value_node.left, state)
        right_range = get_node_range(value_node.right, state)
        
        if isinstance(value_node.op, ast.Add):
            result_range = range_add(left_range, right_range)
        elif isinstance(value_node.op, ast.Sub):
            result_range = range_subtract(left_range, right_range)
        elif isinstance(value_node.op, ast.Mult):
            result_range = range_multiply(left_range, right_range)
        elif isinstance(value_node.op, ast.Div):
            result_range = range_divide(left_range, right_range)
        else:
            result_range = TOP
        
        state.set_range(target_var, result_range)
    
    else:
        # Conservative
        state.set_range(target_var, TOP)


def get_node_range(node: ast.AST, state: RangeState) -> Range:
    """Get range of any node."""
    if isinstance(node, ast.Constant):
        return range_from_constant(node)
    elif isinstance(node, ast.Name):
        return state.get_range(node.id)
    else:
        return TOP