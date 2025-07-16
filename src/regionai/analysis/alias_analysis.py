"""
Alias analysis operations for tracking pointer relationships in Python code.

Since Python doesn't have explicit pointers, we track:
1. Variable assignments (p = q)
2. Object creation (p = {}, p = [], p = MyClass())
3. Attribute/element access (p.x, p[0])
4. Function parameters and returns
"""
import ast
from typing import Set
from .context import AnalysisContext, AbstractLocation


def analyze_alias_assignment(node: ast.Assign, context: AnalysisContext):
    """
    Analyze assignment for alias relationships.
    
    Handles:
    - Simple assignment: p = q
    - Object creation: p = {}, p = [], p = MyClass()
    - Attribute access: p = q.x
    """
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return  # Only handle simple assignments for now
    
    target_var = node.targets[0].id
    
    # Case 1: Assignment from another variable (p = q)
    if isinstance(node.value, ast.Name):
        source_var = node.value.id
        # p now points to everything q points to
        source_pts = context.get_points_to(source_var)
        if source_pts:
            context.set_points_to(target_var, source_pts)
        else:
            # If q doesn't point to anything, it might be a primitive
            # For now, clear p's points-to set
            context.clear_points_to(target_var)
    
    # Case 2: Object creation
    elif isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
        # New heap object at this line
        if hasattr(node, 'lineno'):
            obj_type = node.value.__class__.__name__.lower()
            heap_loc = AbstractLocation.heap_object(node.lineno, obj_type)
            context.set_points_to(target_var, {heap_loc})
    
    # Case 3: Constructor call (p = MyClass())
    elif isinstance(node.value, ast.Call):
        if hasattr(node.value, 'lineno'):
            # Simple heuristic: treat any call as potential object creation
            heap_loc = AbstractLocation.heap_object(node.value.lineno, "object")
            context.set_points_to(target_var, {heap_loc})
    
    # Case 4: Attribute access (p = q.x)
    elif isinstance(node.value, ast.Attribute):
        if isinstance(node.value.value, ast.Name):
            base_var = node.value.value.id
            attr_name = node.value.attr
            
            # For now, create a derived location
            base_pts = context.get_points_to(base_var)
            if base_pts:
                # Create field locations for each base location
                field_locs = set()
                for base_loc in base_pts:
                    field_loc = AbstractLocation(
                        name=f"{base_loc.name}.{attr_name}",
                        loc_type=base_loc.loc_type,
                        allocation_site=base_loc.allocation_site
                    )
                    field_locs.add(field_loc)
                context.set_points_to(target_var, field_locs)
    
    # Case 5: None assignment
    elif isinstance(node.value, ast.Constant) and node.value.value is None:
        # Clear points-to set for None
        context.clear_points_to(target_var)


def analyze_aliasing_in_call(call_node: ast.Call, context: AnalysisContext, 
                           func_name: str, param_names: list):
    """
    Analyze aliasing effects of a function call.
    
    Maps actual arguments to formal parameters for alias analysis.
    """
    # Map arguments to parameters
    for i, arg in enumerate(call_node.args):
        if i < len(param_names) and isinstance(arg, ast.Name):
            arg_var = arg.id
            param_names[i]
            
            # Parameter aliases with argument
            arg_pts = context.get_points_to(arg_var)
            if arg_pts:
                # In the callee context, param points to same locations
                # This would be used by interprocedural analysis
                pass  # Placeholder for interprocedural extension


def check_aliasing_before_access(node: ast.Attribute, context: AnalysisContext) -> Set[str]:
    """
    Check for potential aliasing before an attribute access.
    
    Returns set of variables that may alias with the base object.
    """
    if not isinstance(node.value, ast.Name):
        return set()
    
    base_var = node.value.id
    base_pts = context.get_points_to(base_var)
    
    if not base_pts:
        return set()
    
    # Find all variables that may point to the same locations
    aliases = set()
    for var, pts in context.points_to_map.items():
        if var != base_var and pts & base_pts:  # Non-empty intersection
            aliases.add(var)
    
    return aliases


def analyze_mutation_effects(node: ast.Assign, context: AnalysisContext) -> Set[str]:
    """
    Analyze which variables may be affected by a mutation.
    
    For example, if we have:
    p = obj
    q = obj
    p.x = 5  # This affects both p and q
    
    Returns set of potentially affected variables.
    """
    # Check if this is an attribute assignment (p.x = value)
    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute):
        attr_node = node.targets[0]
        if isinstance(attr_node.value, ast.Name):
            mutated_var = attr_node.value.id
            
            # Find all aliases
            mutated_pts = context.get_points_to(mutated_var)
            if mutated_pts:
                affected = {mutated_var}
                for var, pts in context.points_to_map.items():
                    if var != mutated_var and pts & mutated_pts:
                        affected.add(var)
                return affected
    
    return set()


def merge_points_to_maps(map1: dict, map2: dict) -> dict:
    """
    Merge two points-to maps for join points in control flow.
    
    The result contains the union of points-to sets for each variable.
    """
    merged = {}
    
    # All variables from both maps
    all_vars = set(map1.keys()) | set(map2.keys())
    
    for var in all_vars:
        pts1 = map1.get(var, set())
        pts2 = map2.get(var, set())
        merged[var] = pts1 | pts2  # Union of points-to sets
    
    return merged


def analyze_statement_for_aliases(stmt: ast.AST, context: AnalysisContext):
    """
    Main entry point for alias analysis of a statement.
    
    Updates the context's points-to map based on the statement.
    """
    if isinstance(stmt, ast.Assign):
        analyze_alias_assignment(stmt, context)
        
        # Check for mutations that affect aliases
        affected = analyze_mutation_effects(stmt, context)
        if affected and len(affected) > 1:
            context.add_warning(
                f"Mutation may affect multiple aliases: {affected}"
            )
    
    elif isinstance(stmt, ast.AugAssign):
        # p += q is like p = p + q
        if isinstance(stmt.target, ast.Name):
            # For now, just preserve existing points-to info
            pass
    
    elif isinstance(stmt, ast.Delete):
        # del p - remove from points-to map
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                context.clear_points_to(target.id)


# Integration with existing analysis
def analyze_assignment_with_aliases(node: ast.Assign, context: AnalysisContext, 
                                  abstract_state=None):
    """
    Extended assignment analysis that includes alias tracking.
    
    This wraps the existing analyze_assignment and adds alias analysis.
    """
    # First, do the alias analysis
    analyze_statement_for_aliases(node, context)
    
    # Then do the regular abstract domain analysis
    from ..discovery.abstract_domains import analyze_assignment
    analyze_assignment(node, context, abstract_state)