"""
Unified abstract domain framework with base class and implementations.
Consolidates Sign, Nullability, and Range domains with shared infrastructure.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Union, TypeVar, Generic
from enum import Enum
from dataclasses import dataclass

T = TypeVar('T')


class AbstractDomain(ABC, Generic[T]):
    """
    Base class for all abstract domains.
    Provides common interface for lattice operations.
    """
    
    @abstractmethod
    def join(self, other: T) -> T:
        """Least upper bound (⊔) - union/over-approximation."""
    
    @abstractmethod
    def meet(self, other: T) -> T:
        """Greatest lower bound (⊓) - intersection/under-approximation."""
    
    @abstractmethod
    def widen(self, other: T, iteration: int = 0) -> T:
        """Widening operator for ensuring termination."""
    
    @abstractmethod
    def is_bottom(self) -> bool:
        """Check if this is the bottom element (⊥)."""
    
    @abstractmethod
    def is_top(self) -> bool:
        """Check if this is the top element (⊤)."""
    
    def narrow(self, other: T) -> T:
        """Narrowing operator (optional, defaults to meet)."""
        return self.meet(other)
    
    @abstractmethod
    def __le__(self, other: T) -> bool:
        """Partial order: self ⊑ other."""


# --- Sign Domain ---

class Sign(Enum):
    """Abstract domain for sign analysis."""
    BOTTOM = 0    # ⊥ - Impossible
    NEGATIVE = 1  # -
    ZERO = 2      # 0
    POSITIVE = 3  # +
    TOP = 4       # ⊤ - Unknown
    
    def join(self, other: 'Sign') -> 'Sign':
        """Join operation for sign lattice."""
        if self == Sign.BOTTOM:
            return other
        if other == Sign.BOTTOM:
            return self
        if self == other:
            return self
        # Different signs join to TOP
        return Sign.TOP
    
    def meet(self, other: 'Sign') -> 'Sign':
        """Meet operation for sign lattice."""
        if self == Sign.TOP:
            return other
        if other == Sign.TOP:
            return self
        if self == other:
            return self
        # Different signs meet to BOTTOM
        return Sign.BOTTOM
    
    def widen(self, other: 'Sign', iteration: int = 0) -> 'Sign':
        """Widening for sign domain (same as join for finite domains)."""
        return self.join(other)
    
    def is_bottom(self) -> bool:
        return self == Sign.BOTTOM
    
    def is_top(self) -> bool:
        return self == Sign.TOP
    
    def __le__(self, other: 'Sign') -> bool:
        """Lattice ordering: BOTTOM ≤ NEGATIVE/ZERO/POSITIVE ≤ TOP."""
        if self == Sign.BOTTOM or other == Sign.TOP:
            return True
        if self == Sign.TOP or other == Sign.BOTTOM:
            return False
        return self == other


class SignDomain:
    """Operations for sign abstract domain."""
    
    @staticmethod
    def from_constant(value: Union[int, float]) -> Sign:
        """Create sign from concrete value."""
        if value > 0:
            return Sign.POSITIVE
        elif value < 0:
            return Sign.NEGATIVE
        else:
            return Sign.ZERO
    
    @staticmethod
    def add(left: Sign, right: Sign) -> Sign:
        """Abstract addition."""
        if left.is_bottom() or right.is_bottom():
            return Sign.BOTTOM
        if left.is_top() or right.is_top():
            return Sign.TOP
        
        if left == Sign.ZERO:
            return right
        if right == Sign.ZERO:
            return left
        
        if left == right:  # Same sign
            return left
        
        # Different signs -> could be any
        return Sign.TOP
    
    @staticmethod
    def multiply(left: Sign, right: Sign) -> Sign:
        """Abstract multiplication."""
        if left.is_bottom() or right.is_bottom():
            return Sign.BOTTOM
        if left == Sign.ZERO or right == Sign.ZERO:
            return Sign.ZERO
        if left.is_top() or right.is_top():
            return Sign.TOP
        
        # Both non-zero: same sign -> positive, different -> negative
        if left == right:
            return Sign.POSITIVE
        else:
            return Sign.NEGATIVE
    
    @staticmethod
    def negate(sign: Sign) -> Sign:
        """Abstract negation."""
        if sign == Sign.POSITIVE:
            return Sign.NEGATIVE
        elif sign == Sign.NEGATIVE:
            return Sign.POSITIVE
        else:
            return sign


# --- Nullability Domain ---

class Nullability(Enum):
    """Abstract domain for null analysis."""
    BOTTOM = 0          # ⊥ - Impossible
    NOT_NULL = 1        # Definitely not null
    DEFINITELY_NULL = 2 # Definitely null
    NULLABLE = 3        # May or may not be null (TOP)
    
    def join(self, other: 'Nullability') -> 'Nullability':
        """Join operation for nullability lattice."""
        if self == Nullability.BOTTOM:
            return other
        if other == Nullability.BOTTOM:
            return self
        if self == other:
            return self
        # Different values join to NULLABLE
        return Nullability.NULLABLE
    
    def meet(self, other: 'Nullability') -> 'Nullability':
        """Meet operation for nullability lattice."""
        if self == Nullability.NULLABLE:
            return other
        if other == Nullability.NULLABLE:
            return self
        if self == other:
            return self
        # Different values meet to BOTTOM
        return Nullability.BOTTOM
    
    def widen(self, other: 'Nullability', iteration: int = 0) -> 'Nullability':
        """Widening (same as join for finite domains)."""
        return self.join(other)
    
    def is_bottom(self) -> bool:
        return self == Nullability.BOTTOM
    
    def is_top(self) -> bool:
        return self == Nullability.NULLABLE
    
    def __le__(self, other: 'Nullability') -> bool:
        """Lattice ordering."""
        if self == Nullability.BOTTOM or other == Nullability.NULLABLE:
            return True
        if self == Nullability.NULLABLE or other == Nullability.BOTTOM:
            return False
        return self == other


# --- Range Domain ---

@dataclass
class Range(AbstractDomain['Range']):
    """
    Interval abstract domain [min, max].
    Supports infinite bounds for unbounded ranges.
    """
    min: Union[int, float]
    max: Union[int, float]
    
    def __post_init__(self):
        # Normalize invalid ranges to bottom
        if self.min > self.max:
            self.min = 1
            self.max = 0
    
    def join(self, other: 'Range') -> 'Range':
        """Union of ranges."""
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        return Range(min(self.min, other.min), max(self.max, other.max))
    
    def meet(self, other: 'Range') -> 'Range':
        """Intersection of ranges."""
        if self.is_bottom() or other.is_bottom():
            return Range.bottom()
        
        new_min = max(self.min, other.min)
        new_max = min(self.max, other.max)
        
        if new_min > new_max:
            return Range.bottom()
        
        return Range(new_min, new_max)
    
    def widen(self, other: 'Range', iteration: int = 0, threshold: int = 3) -> 'Range':
        """
        Widening with threshold.
        
        Args:
            other: Range to widen with
            iteration: Current iteration count
            threshold: Widening threshold (typically from config)
        """
        if self == other:
            return self
        
        if iteration >= threshold:
            # Jump to infinity if bounds keep growing
            new_min = float('-inf') if other.min < self.min else self.min
            new_max = float('inf') if other.max > self.max else self.max
            return Range(new_min, new_max)
        
        return self.join(other)
    
    def is_bottom(self) -> bool:
        """Check if empty range."""
        return self.min > self.max
    
    def is_top(self) -> bool:
        """Check if unbounded."""
        return self.min == float('-inf') and self.max == float('inf')
    
    def __le__(self, other: 'Range') -> bool:
        """Check if self is contained in other."""
        if self.is_bottom():
            return True
        if other.is_bottom():
            return False
        return self.min >= other.min and self.max <= other.max
    
    def contains(self, value: Union[int, float]) -> bool:
        """Check if value is in range."""
        return self.min <= value <= self.max
    
    @classmethod
    def bottom(cls) -> 'Range':
        """Bottom element (empty range)."""
        return cls(1, 0)
    
    @classmethod
    def top(cls) -> 'Range':
        """Top element (infinite range)."""
        return cls(float('-inf'), float('inf'))
    
    def __str__(self):
        if self.is_bottom():
            return "⊥"
        elif self.is_top():
            return "[-∞, +∞]"
        else:
            min_str = "-∞" if self.min == float('-inf') else str(self.min)
            max_str = "+∞" if self.max == float('inf') else str(self.max)
            return f"[{min_str}, {max_str}]"


class RangeDomain:
    """Operations for range abstract domain."""
    
    @staticmethod
    def from_constant(value: Union[int, float]) -> Range:
        """Create singleton range."""
        return Range(value, value)
    
    @staticmethod
    def add(r1: Range, r2: Range) -> Range:
        """Abstract addition of ranges."""
        if r1.is_bottom() or r2.is_bottom():
            return Range.bottom()
        return Range(r1.min + r2.min, r1.max + r2.max)
    
    @staticmethod
    def multiply(r1: Range, r2: Range) -> Range:
        """Abstract multiplication of ranges."""
        if r1.is_bottom() or r2.is_bottom():
            return Range.bottom()
        
        # All possible products
        products = [
            r1.min * r2.min, r1.min * r2.max,
            r1.max * r2.min, r1.max * r2.max
        ]
        
        return Range(min(products), max(products))
    
    @staticmethod
    def negate(r: Range) -> Range:
        """Abstract negation."""
        if r.is_bottom():
            return Range.bottom()
        return Range(-r.max, -r.min)


# --- Unified Abstract State ---

@dataclass
class AbstractState:
    """
    Combined abstract state tracking multiple domains.
    Maps variables to their abstract values.
    """
    sign_state: Dict[str, Sign]
    null_state: Dict[str, Nullability]
    range_state: Dict[str, Range]
    
    def __init__(self):
        self.sign_state = {}
        self.null_state = {}
        self.range_state = {}
    
    def get_sign(self, var: str) -> Optional[Sign]:
        """Get sign of variable."""
        return self.sign_state.get(var)
    
    def get_nullability(self, var: str) -> Optional[Nullability]:
        """Get nullability of variable."""
        return self.null_state.get(var)
    
    def get_range(self, var: str) -> Optional[Range]:
        """Get range of variable."""
        return self.range_state.get(var)
    
    def update_sign(self, var: str, sign: Sign):
        """Update sign of variable."""
        self.sign_state[var] = sign
    
    def set_sign(self, var: str, sign: Sign):
        """Alias for update_sign for compatibility."""
        self.update_sign(var, sign)
    
    def update_nullability(self, var: str, null: Nullability):
        """Update nullability of variable."""
        self.null_state[var] = null
    
    def set_nullability(self, var: str, null: Nullability):
        """Alias for update_nullability for compatibility."""
        self.update_nullability(var, null)
    
    def update_range(self, var: str, range: Range):
        """Update range of variable."""
        self.range_state[var] = range
    
    def set_range(self, var: str, range: Range):
        """Alias for update_range for compatibility."""
        self.update_range(var, range)
    
    def join(self, other: 'AbstractState') -> 'AbstractState':
        """Join two abstract states."""
        result = AbstractState()
        
        # Join signs
        all_vars = set(self.sign_state.keys()) | set(other.sign_state.keys())
        for var in all_vars:
            s1 = self.sign_state.get(var, Sign.TOP)
            s2 = other.sign_state.get(var, Sign.TOP)
            result.sign_state[var] = s1.join(s2)
        
        # Join nullability
        all_vars = set(self.null_state.keys()) | set(other.null_state.keys())
        for var in all_vars:
            n1 = self.null_state.get(var, Nullability.NULLABLE)
            n2 = other.null_state.get(var, Nullability.NULLABLE)
            result.null_state[var] = n1.join(n2)
        
        # Join ranges
        all_vars = set(self.range_state.keys()) | set(other.range_state.keys())
        for var in all_vars:
            r1 = self.range_state.get(var, Range.top())
            r2 = other.range_state.get(var, Range.top())
            result.range_state[var] = r1.join(r2)
        
        return result


# --- Convenience functions for backward compatibility ---

def sign_add(left: Sign, right: Sign) -> Sign:
    """Legacy function."""
    return SignDomain.add(left, right)

def sign_multiply(left: Sign, right: Sign) -> Sign:
    """Legacy function."""
    return SignDomain.multiply(left, right)

def nullability_join(n1: Nullability, n2: Nullability) -> Nullability:
    """Legacy function."""
    return n1.join(n2)

def range_join(r1: Range, r2: Range) -> Range:
    """Legacy function."""
    return r1.join(r2)

def range_widen(old: Range, new: Range, iteration: int) -> Range:
    """Legacy function."""
    return old.widen(new, iteration)