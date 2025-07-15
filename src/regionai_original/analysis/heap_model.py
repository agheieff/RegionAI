"""
Heap modeling for tracking object mutations and heap state.

This module provides abstract heap modeling to track how objects
are created, mutated, and accessed throughout program execution.
"""
import ast
from typing import Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass, field

from .pointer_analysis import HeapObject
from ..core.abstract_domains import AbstractState, Sign, Nullability


class HeapValue:
    """Abstract value that can be stored in the heap."""


@dataclass
class PrimitiveValue(HeapValue):
    """Represents a primitive value (int, str, bool, etc.)."""
    type_name: str
    abstract_value: Any  # Could be Sign, Range, or concrete value
    
    def __str__(self):
        return f"{self.type_name}({self.abstract_value})"


@dataclass
class ReferenceValue(HeapValue):
    """Represents a reference to another heap object."""
    target: HeapObject
    
    def __str__(self):
        return f"ref({self.target})"


@dataclass
class NullValue(HeapValue):
    """Represents a null/None value."""
    def __str__(self):
        return "null"


@dataclass
class HeapState:
    """
    Abstract heap state tracking object contents.
    
    This models the heap as a mapping from heap objects and their fields
    to abstract values. Supports field-sensitive analysis.
    """
    # Map from (HeapObject, field_name) to abstract value
    heap: Dict[Tuple[HeapObject, Optional[str]], HeapValue] = field(default_factory=dict)
    
    # Track object types
    object_types: Dict[HeapObject, str] = field(default_factory=dict)
    
    # Track which objects are definitely initialized
    initialized_objects: Set[HeapObject] = field(default_factory=set)
    
    def copy(self) -> 'HeapState':
        """Create a deep copy of the heap state."""
        new_heap = HeapState()
        new_heap.heap = self.heap.copy()
        new_heap.object_types = self.object_types.copy()
        new_heap.initialized_objects = self.initialized_objects.copy()
        return new_heap
    
    def get_field(self, obj: HeapObject, field: Optional[str] = None) -> Optional[HeapValue]:
        """Get the value of an object's field."""
        return self.heap.get((obj, field))
    
    def set_field(self, obj: HeapObject, field: Optional[str], value: HeapValue):
        """Set the value of an object's field."""
        self.heap[(obj, field)] = value
        self.initialized_objects.add(obj)
    
    def merge(self, other: 'HeapState') -> 'HeapState':
        """Merge two heap states (for join points)."""
        merged = HeapState()
        
        # Merge heap contents
        all_keys = set(self.heap.keys()) | set(other.heap.keys())
        for key in all_keys:
            val1 = self.heap.get(key)
            val2 = other.heap.get(key)
            
            if val1 is None:
                merged.heap[key] = val2
            elif val2 is None:
                merged.heap[key] = val1
            elif val1 == val2:
                merged.heap[key] = val1
            else:
                # Need to merge different values
                merged.heap[key] = self._merge_values(val1, val2)
        
        # Merge type information
        merged.object_types = self.object_types.copy()
        merged.object_types.update(other.object_types)
        
        # Intersection of initialized objects (conservative)
        merged.initialized_objects = self.initialized_objects & other.initialized_objects
        
        return merged
    
    def _merge_values(self, val1: HeapValue, val2: HeapValue) -> HeapValue:
        """Merge two heap values."""
        # Simple merge strategy - could be enhanced
        if isinstance(val1, NullValue) or isinstance(val2, NullValue):
            # If either is null, result could be null
            return NullValue()
        elif isinstance(val1, PrimitiveValue) and isinstance(val2, PrimitiveValue):
            if val1.type_name == val2.type_name:
                # Same type - merge abstract values
                # For now, just go to TOP
                return PrimitiveValue(val1.type_name, "TOP")
        # Conservative: return first value
        return val1


class HeapAnalyzer:
    """
    Analyzer for tracking heap state and mutations.
    
    Works in conjunction with pointer analysis to provide
    precise tracking of object mutations.
    """
    
    def __init__(self, pointer_analysis):
        """
        Initialize heap analyzer.
        
        Args:
            pointer_analysis: Pointer analysis results to use
        """
        self.pointer_analysis = pointer_analysis
        self.heap_states: Dict[Any, HeapState] = {}  # Map from program point to heap state
        
    def analyze_statement_with_heap(self, stmt: ast.AST, 
                                   abstract_state: AbstractState,
                                   heap_state: HeapState,
                                   current_function: Optional[str] = None) -> HeapState:
        """
        Analyze a statement and update heap state.
        
        Args:
            stmt: Statement to analyze
            abstract_state: Current abstract state for local variables
            heap_state: Current heap state
            current_function: Current function name
            
        Returns:
            Updated heap state
        """
        new_heap = heap_state.copy()
        
        if isinstance(stmt, ast.Assign):
            self._analyze_heap_assignment(stmt, abstract_state, new_heap, current_function)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            self._analyze_heap_call(stmt.value, abstract_state, new_heap, current_function)
        
        return new_heap
    
    def _analyze_heap_assignment(self, assign: ast.Assign,
                                abstract_state: AbstractState,
                                heap_state: HeapState,
                                current_function: Optional[str]):
        """Analyze assignment for heap effects."""
        # Check if we're assigning to a field
        for target in assign.targets:
            if isinstance(target, ast.Attribute):
                # obj.field = value
                base_var = self._get_var_name(target.value)
                if base_var:
                    # Get objects that base may point to
                    from .pointer_analysis import StackVariable
                    StackVariable(base_var, current_function)
                    pointed_objs = self.pointer_analysis.get_pointed_objects(
                        base_var, current_function
                    )
                    
                    # Get value being assigned
                    heap_value = self._evaluate_to_heap_value(
                        assign.value, abstract_state, current_function
                    )
                    
                    # Update heap state for each possible object
                    for obj in pointed_objs:
                        heap_state.set_field(obj, target.attr, heap_value)
    
    def _analyze_heap_call(self, call: ast.Call,
                          abstract_state: AbstractState,
                          heap_state: HeapState,
                          current_function: Optional[str]):
        """Analyze method call for heap effects."""
        if isinstance(call.func, ast.Attribute):
            # obj.method() call
            base_var = self._get_var_name(call.func.value)
            if base_var:
                method_name = call.func.attr
                
                # Special handling for known mutating methods
                if method_name in ['append', 'extend', 'insert', 'remove', 'pop']:
                    # List mutations
                    pointed_objs = self.pointer_analysis.get_pointed_objects(
                        base_var, current_function
                    )
                    for obj in pointed_objs:
                        # Mark object as mutated
                        heap_state.set_field(obj, '__mutated__', 
                                           PrimitiveValue('bool', True))
                
                elif method_name in ['update', 'setdefault', 'pop']:
                    # Dict mutations
                    pointed_objs = self.pointer_analysis.get_pointed_objects(
                        base_var, current_function
                    )
                    for obj in pointed_objs:
                        heap_state.set_field(obj, '__mutated__',
                                           PrimitiveValue('bool', True))
    
    def _evaluate_to_heap_value(self, expr: ast.AST,
                               abstract_state: AbstractState,
                               current_function: Optional[str]) -> HeapValue:
        """Evaluate expression to abstract heap value."""
        if isinstance(expr, ast.Constant):
            # Literal value
            if expr.value is None:
                return NullValue()
            elif isinstance(expr.value, (int, float)):
                return PrimitiveValue('int', expr.value)
            elif isinstance(expr.value, str):
                return PrimitiveValue('str', expr.value)
            elif isinstance(expr.value, bool):
                return PrimitiveValue('bool', expr.value)
        
        elif isinstance(expr, ast.Name):
            # Variable reference
            var_name = expr.id
            
            # Check if it points to heap objects
            pointed_objs = self.pointer_analysis.get_pointed_objects(
                var_name, current_function
            )
            if pointed_objs:
                # For simplicity, take first object
                # In practice, would need to handle multiple possibilities
                return ReferenceValue(next(iter(pointed_objs)))
            
            # Check abstract state
            sign = abstract_state.get_sign(var_name)
            if sign == Sign.ZERO:
                return PrimitiveValue('int', 0)
            else:
                return PrimitiveValue('int', sign)
        
        elif isinstance(expr, ast.Call):
            # Constructor call - check pointer analysis
            pass
            # This is simplified - would need proper handling
            locations = self.pointer_analysis._analyze_call(expr)
            if locations:
                for loc in locations:
                    if isinstance(loc, HeapObject):
                        return ReferenceValue(loc)
        
        # Default: unknown value
        return PrimitiveValue('unknown', 'TOP')
    
    def _get_var_name(self, expr: ast.AST) -> Optional[str]:
        """Extract variable name from expression."""
        if isinstance(expr, ast.Name):
            return expr.id
        return None
    
    def check_null_field_access(self, expr: ast.Attribute,
                               abstract_state: AbstractState,
                               heap_state: HeapState,
                               current_function: Optional[str]) -> bool:
        """
        Check if field access may dereference null.
        
        Args:
            expr: Attribute access expression (obj.field)
            abstract_state: Current abstract state
            heap_state: Current heap state
            current_function: Current function
            
        Returns:
            True if access is definitely safe, False if it may be null
        """
        base_var = self._get_var_name(expr.value)
        if not base_var:
            return False  # Conservative
        
        # Check nullability in abstract state
        null_state = abstract_state.get_nullability(base_var)
        if null_state == Nullability.NULL:
            return False  # Definitely null!
        
        # Check heap state
        pointed_objs = self.pointer_analysis.get_pointed_objects(
            base_var, current_function
        )
        
        if not pointed_objs:
            # No heap objects - check abstract state
            return null_state == Nullability.NOT_NULL
        
        # Check if all pointed objects are initialized
        all_initialized = all(
            obj in heap_state.initialized_objects
            for obj in pointed_objs
        )
        
        return all_initialized
    
    def get_field_value(self, var_name: str, field_name: str,
                       heap_state: HeapState,
                       current_function: Optional[str]) -> Set[HeapValue]:
        """
        Get possible values of a field access.
        
        Args:
            var_name: Base variable name
            field_name: Field name
            heap_state: Current heap state
            current_function: Current function
            
        Returns:
            Set of possible heap values
        """
        pointed_objs = self.pointer_analysis.get_pointed_objects(
            var_name, current_function
        )
        
        values = set()
        for obj in pointed_objs:
            val = heap_state.get_field(obj, field_name)
            if val:
                values.add(val)
            else:
                # Field not initialized - could be anything
                values.add(PrimitiveValue('unknown', 'TOP'))
        
        return values