"""
Pointer analysis for tracking aliasing and heap objects.

This module provides flow-insensitive, field-sensitive pointer analysis
using Andersen's algorithm with enhancements for Python's object model.
"""
import ast
from typing import Dict, Set, Optional, Tuple, Union
from dataclasses import dataclass

from tier1.config import RegionAIConfig, DEFAULT_CONFIG


class PointsToLocation:
    """Abstract location that a pointer can point to."""


@dataclass(frozen=True)
class HeapObject(PointsToLocation):
    """
    Represents an abstract heap object.
    
    Attributes:
        allocation_site: Line number or identifier where object was allocated
        type_name: Optional type name if known (e.g., 'list', 'dict', 'User')
    """
    allocation_site: Union[int, str]
    type_name: Optional[str] = None
    
    def __str__(self):
        if self.type_name:
            return f"Heap<{self.type_name}@{self.allocation_site}>"
        return f"Heap<@{self.allocation_site}>"


@dataclass(frozen=True)
class StackVariable(PointsToLocation):
    """Represents a stack variable (local or parameter)."""
    name: str
    function: Optional[str] = None
    
    def __str__(self):
        if self.function:
            return f"{self.function}::{self.name}"
        return self.name


@dataclass(frozen=True)
class FieldLocation(PointsToLocation):
    """
    Represents a field of an object.
    
    This enables field-sensitive analysis where obj.x and obj.y
    are tracked separately.
    """
    base: PointsToLocation
    field: str
    
    def __str__(self):
        return f"{self.base}.{self.field}"


@dataclass(frozen=True)
class GlobalVariable(PointsToLocation):
    """Represents a global variable."""
    name: str
    
    def __str__(self):
        return f"global::{self.name}"


class PointerAnalysis:
    """
    Andersen-style pointer analysis for Python.
    
    This analysis computes which abstract heap objects each variable
    may point to, enabling precise tracking of aliasing and mutations.
    """
    
    def __init__(self, config: Optional[RegionAIConfig] = None):
        """Initialize pointer analysis."""
        self.config = config or DEFAULT_CONFIG
        
        # Points-to sets: what locations each variable may point to
        self.points_to: Dict[PointsToLocation, Set[PointsToLocation]] = {}
        
        # Constraint edges for Andersen's algorithm
        # (source, target) means source ⊆ target (subset constraint)
        self.subset_constraints: Set[Tuple[PointsToLocation, PointsToLocation]] = set()
        
        # Track heap allocation sites
        self.heap_objects: Dict[Union[int, str], HeapObject] = {}
        
        # Current function being analyzed
        self.current_function: Optional[str] = None
        
        # Object type information from static analysis
        self.object_types: Dict[HeapObject, str] = {}
        
    def analyze_module(self, tree: ast.AST) -> Dict[PointsToLocation, Set[PointsToLocation]]:
        """
        Analyze an entire module and return points-to information.
        
        Args:
            tree: AST of the module to analyze
            
        Returns:
            Dictionary mapping each location to its points-to set
        """
        # First pass: collect all functions and global variables
        self._collect_globals(tree)
        
        # Second pass: analyze each function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.analyze_function(node)
        
        # Third pass: solve constraints using Andersen's algorithm
        self._solve_constraints()
        
        return self.points_to
    
    def analyze_function(self, func_node: ast.FunctionDef):
        """Analyze a single function."""
        old_function = self.current_function
        self.current_function = func_node.name
        
        # Create locations for parameters
        for arg in func_node.args.args:
            param_loc = StackVariable(arg.arg, self.current_function)
            # Parameters initially point to unknown (TOP)
            self._ensure_location(param_loc)
        
        # Analyze function body
        for stmt in func_node.body:
            self._analyze_statement(stmt)
        
        self.current_function = old_function
    
    def _analyze_statement(self, stmt: ast.AST):
        """Analyze a single statement."""
        if isinstance(stmt, ast.Assign):
            self._analyze_assignment(stmt)
        elif isinstance(stmt, ast.AugAssign):
            # x += y is like x = x + y
            self._analyze_augmented_assignment(stmt)
        elif isinstance(stmt, ast.If):
            # Analyze both branches
            for s in stmt.body:
                self._analyze_statement(s)
            for s in stmt.orelse:
                self._analyze_statement(s)
        elif isinstance(stmt, ast.While) or isinstance(stmt, ast.For):
            # Analyze loop body
            body_stmts = stmt.body if hasattr(stmt, 'body') else []
            for s in body_stmts:
                self._analyze_statement(s)
        elif isinstance(stmt, ast.Return):
            # Track return values if needed
            pass
        elif isinstance(stmt, ast.Expr):
            # Handle expression statements (e.g., method calls)
            if isinstance(stmt.value, ast.Call):
                self._analyze_call(stmt.value)
    
    def _analyze_assignment(self, assign: ast.Assign):
        """Analyze assignment statement."""
        # Get locations for RHS
        rhs_locs = self._get_locations(assign.value)
        
        # Create constraints for each target
        for target in assign.targets:
            target_locs = self._get_or_create_locations(target)
            
            # For direct heap object assignments, add to points-to set immediately
            for rhs_loc in rhs_locs:
                if isinstance(rhs_loc, HeapObject):
                    # Direct assignment of heap object
                    for target_loc in target_locs:
                        if target_loc not in self.points_to:
                            self.points_to[target_loc] = set()
                        self.points_to[target_loc].add(rhs_loc)
                else:
                    # Variable-to-variable assignment, add constraint
                    for target_loc in target_locs:
                        self._add_subset_constraint(rhs_loc, target_loc)
    
    def _analyze_augmented_assignment(self, aug_assign: ast.AugAssign):
        """Analyze augmented assignment (+=, -=, etc.)."""
        # For pointer analysis, treat x += y as x = x
        # (we're not tracking numeric values)
        self._get_or_create_locations(aug_assign.target)
        # No new constraints needed - target keeps pointing to same objects
    
    def _analyze_call(self, call: ast.Call):
        """Analyze function call."""
        # Handle object creation
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
            
            # Check for constructor calls
            if func_name[0].isupper() or func_name in ['list', 'dict', 'set', 'tuple']:
                # This is likely an object creation
                alloc_site = call.lineno if hasattr(call, 'lineno') else f"alloc_{id(call)}"
                heap_obj = HeapObject(alloc_site, func_name)
                self.heap_objects[alloc_site] = heap_obj
                return {heap_obj}
        
        # Handle method calls (e.g., obj.method())
        elif isinstance(call.func, ast.Attribute):
            self._get_locations(call.func.value)
            # Could track method calls for more precision
        
        return set()
    
    def _get_locations(self, expr: ast.AST) -> Set[PointsToLocation]:
        """Get locations that an expression may evaluate to."""
        if isinstance(expr, ast.Name):
            var_loc = StackVariable(expr.id, self.current_function)
            # For RHS of assignment, return the variable location itself
            # The points-to set will be populated by constraints
            return {var_loc}
        
        elif isinstance(expr, ast.Attribute):
            # obj.field
            base_locs = self._get_locations(expr.value)
            field_locs = set()
            for base_loc in base_locs:
                field_loc = FieldLocation(base_loc, expr.attr)
                field_locs.add(field_loc)
            return field_locs
        
        elif isinstance(expr, ast.Call):
            # Handle object creation
            return self._analyze_call(expr)
        
        elif isinstance(expr, ast.List) or isinstance(expr, ast.Dict):
            # List/dict literal creates new heap object
            alloc_site = expr.lineno if hasattr(expr, 'lineno') else f"alloc_{id(expr)}"
            type_name = 'list' if isinstance(expr, ast.List) else 'dict'
            heap_obj = HeapObject(alloc_site, type_name)
            self.heap_objects[alloc_site] = heap_obj
            return {heap_obj}
        
        # Conservative: unknown location
        return set()
    
    def _get_or_create_locations(self, target: ast.AST) -> Set[PointsToLocation]:
        """Get or create locations for assignment target."""
        if isinstance(target, ast.Name):
            var_loc = StackVariable(target.id, self.current_function)
            self._ensure_location(var_loc)
            return {var_loc}
        
        elif isinstance(target, ast.Attribute):
            # obj.field = ...
            base_locs = self._get_locations(target.value)
            field_locs = set()
            for base_loc in base_locs:
                field_loc = FieldLocation(base_loc, target.attr)
                self._ensure_location(field_loc)
                field_locs.add(field_loc)
            return field_locs
        
        elif isinstance(target, ast.Subscript):
            # For now, treat array[i] conservatively
            # Could enhance with array-sensitive analysis
            base_locs = self._get_locations(target.value)
            return base_locs
        
        return set()
    
    def _ensure_location(self, loc: PointsToLocation):
        """Ensure location exists in points-to map."""
        if loc not in self.points_to:
            self.points_to[loc] = set()
    
    def _add_subset_constraint(self, source: PointsToLocation, target: PointsToLocation):
        """Add constraint that source ⊆ target."""
        self._ensure_location(source)
        self._ensure_location(target)
        self.subset_constraints.add((source, target))
    
    def _collect_globals(self, tree: ast.AST):
        """Collect global variables."""
        # Simple collection of top-level assignments
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        global_loc = GlobalVariable(target.id)
                        self._ensure_location(global_loc)
    
    def _solve_constraints(self):
        """
        Solve subset constraints using Andersen's algorithm.
        
        This is a fixed-point computation that propagates points-to
        information according to the subset constraints.
        """
        changed = True
        iterations = 0
        max_iterations = 100  # Prevent infinite loops
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            # Process each constraint
            for source, target in self.subset_constraints:
                # Get current points-to sets
                source_pts = self.points_to.get(source, set())
                target_pts = self.points_to.get(target, set())
                
                # Check if we need to add anything to target
                to_add = source_pts - target_pts
                if to_add:
                    self.points_to[target] = target_pts | to_add
                    changed = True
                    
                    # Handle field constraints
                    # If target is a field and we added heap objects,
                    # we need to propagate to the field locations
                    if isinstance(target, FieldLocation):
                        for loc in to_add:
                            if isinstance(loc, HeapObject):
                                # Create field location for heap object
                                heap_field = FieldLocation(loc, target.field)
                                self._ensure_location(heap_field)
    
    def may_alias(self, loc1: PointsToLocation, loc2: PointsToLocation) -> bool:
        """
        Check if two locations may alias (point to same heap object).
        
        Args:
            loc1: First location
            loc2: Second location
            
        Returns:
            True if the locations may alias
        """
        pts1 = self.points_to.get(loc1, {loc1})
        pts2 = self.points_to.get(loc2, {loc2})
        
        # Check if they have any heap objects in common
        return bool(pts1 & pts2)
    
    def get_pointed_objects(self, var_name: str, 
                          function: Optional[str] = None) -> Set[HeapObject]:
        """
        Get heap objects that a variable may point to.
        
        Args:
            var_name: Variable name
            function: Function containing the variable (None for globals)
            
        Returns:
            Set of heap objects the variable may point to
        """
        if function:
            loc = StackVariable(var_name, function)
        else:
            loc = GlobalVariable(var_name)
        
        pts = self.points_to.get(loc, set())
        return {obj for obj in pts if isinstance(obj, HeapObject)}
    
    def get_field_objects(self, base_var: str, field: str,
                         function: Optional[str] = None) -> Set[HeapObject]:
        """
        Get heap objects that a field may point to.
        
        Args:
            base_var: Base variable name
            field: Field name
            function: Function containing the variable
            
        Returns:
            Set of heap objects the field may point to
        """
        base_objs = self.get_pointed_objects(base_var, function)
        result = set()
        
        for base_obj in base_objs:
            field_loc = FieldLocation(base_obj, field)
            pts = self.points_to.get(field_loc, set())
            result.update(obj for obj in pts if isinstance(obj, HeapObject))
        
        return result