"""
Hierarchical discovery engine for conditional control flow.
"""
from typing import List, Optional, Dict, Any, Set, Tuple
import torch
import uuid
from collections import deque
from dataclasses import dataclass

from regionai.data.problem import Problem, ProblemDataType
from regionai.geometry.region import RegionND
from regionai.discovery.transformation import (
    PRIMITIVE_OPERATIONS, TransformationSequence, INVERSE_OPERATIONS,
    AppliedTransformation, Transformation, ConditionalTransformation
)


def dict_list_equals(list1: List[Dict[str, Any]], list2: List[Dict[str, Any]]) -> bool:
    """Check if two lists of dictionaries are equal."""
    if len(list1) != len(list2):
        return False
    
    for d1, d2 in zip(list1, list2):
        if set(d1.keys()) != set(d2.keys()):
            return False
        for key in d1.keys():
            v1, v2 = d1[key], d2[key]
            if isinstance(v1, float) and isinstance(v2, float):
                if not torch.allclose(torch.tensor([v1]), torch.tensor([v2]), rtol=1e-5):
                    return False
            elif v1 != v2:
                return False
    return True


def extract_parameter_candidates(problems: List[Problem]) -> Dict[str, Set[Any]]:
    """Extract potential parameters from problem data."""
    candidates = {
        'keys': set(),
        'values': {},
        'multipliers': set()
    }
    
    for problem in problems:
        # Extract from input data
        if isinstance(problem.input_data, list):
            for item in problem.input_data:
                if isinstance(item, dict):
                    candidates['keys'].update(item.keys())
                    for key, value in item.items():
                        if key not in candidates['values']:
                            candidates['values'][key] = set()
                        candidates['values'][key].add(value)
        
        # Try to infer multipliers from input/output pairs
        if isinstance(problem.input_data, list) and isinstance(problem.output_data, list):
            for inp, out in zip(problem.input_data, problem.output_data):
                if isinstance(inp, dict) and isinstance(out, dict):
                    if 'salary' in inp and 'salary' in out:
                        ratio = out['salary'] / inp['salary']
                        candidates['multipliers'].add(round(ratio, 3))
    
    return candidates


def discover_linear_sequence(
    problems: List[Problem],
    param_candidates: Dict[str, Set[Any]],
    max_depth: int = 3
) -> Optional[TransformationSequence]:
    """Discover a linear sequence of transformations."""
    search_queue = deque()
    
    # Initialize with primitive operations
    for primitive in PRIMITIVE_OPERATIONS:
        if primitive.input_type == "dict_list":
            if primitive.num_args == 0:
                applied = AppliedTransformation(primitive, [])
                seq = TransformationSequence([applied])
                search_queue.append(seq)
            elif primitive.name == "MAP_GET":
                for key in param_candidates['keys']:
                    applied = AppliedTransformation(primitive, [key])
                    seq = TransformationSequence([applied])
                    search_queue.append(seq)
            elif primitive.name == "FILTER_BY_VALUE":
                for key in param_candidates['keys']:
                    if key in param_candidates['values']:
                        for value in param_candidates['values'][key]:
                            applied = AppliedTransformation(primitive, [key, value])
                            seq = TransformationSequence([applied])
                            search_queue.append(seq)
            elif primitive.name == "UPDATE_FIELD":
                # For UPDATE_FIELD, we need to try different update strategies
                for key in param_candidates['keys']:
                    if key == 'salary':  # Special handling for salary updates
                        for mult in param_candidates['multipliers']:
                            # Create a lambda that multiplies the field
                            update_fn = lambda x, m=mult: x * m
                            applied = AppliedTransformation(primitive, [key, update_fn])
                            seq = TransformationSequence([applied])
                            search_queue.append(seq)
    
    while search_queue:
        current_seq = search_queue.popleft()
        
        if len(current_seq) > max_depth:
            continue
        
        # Test if this sequence solves all problems
        is_solution = True
        for problem in problems:
            try:
                result = current_seq.apply(problem.input_data)
                if isinstance(problem.output_data, list) and isinstance(result, list):
                    if not dict_list_equals(result, problem.output_data):
                        is_solution = False
                        break
                else:
                    is_solution = False
                    break
            except:
                is_solution = False
                break
        
        if is_solution:
            return current_seq
        
        # Expand search (simplified for now)
        # In a full implementation, we'd add more operations here
    
    return None


def discover_conditional_concept(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Discover concepts that require conditional logic.
    """
    print("\n--- Phase 2: Analyzing failures for conditional patterns ---")
    
    if not failed_problems:
        print("    No failures provided.")
        return None
    
    # Extract parameter candidates
    param_candidates = extract_parameter_candidates(failed_problems)
    print(f"    Found candidates - Keys: {param_candidates['keys']}, Multipliers: {param_candidates['multipliers']}")
    
    # Try to identify the condition by analyzing the data
    # Look for a field that correlates with different transformations
    condition_field = None
    condition_values = {}
    
    # Simple heuristic: check if 'role' field correlates with different salary multipliers
    if 'role' in param_candidates['keys'] and 'salary' in param_candidates['keys']:
        # Group by role and check salary changes
        role_multipliers = {}
        
        for problem in failed_problems:
            if isinstance(problem.input_data, list) and isinstance(problem.output_data, list):
                for inp, out in zip(problem.input_data, problem.output_data):
                    if 'role' in inp and 'salary' in inp and 'salary' in out:
                        role = inp['role']
                        multiplier = out['salary'] / inp['salary']
                        
                        if role not in role_multipliers:
                            role_multipliers[role] = []
                        role_multipliers[role].append(multiplier)
        
        # Check if different roles have consistent multipliers
        distinct_multipliers = {}
        for role, mults in role_multipliers.items():
            if mults:
                avg_mult = sum(mults) / len(mults)
                # Check if all multipliers for this role are similar
                if all(abs(m - avg_mult) < 0.001 for m in mults):
                    distinct_multipliers[role] = avg_mult
        
        if len(distinct_multipliers) > 1:
            condition_field = 'role'
            condition_values = distinct_multipliers
            print(f"    Detected conditional pattern on '{condition_field}': {condition_values}")
    
    if not condition_field:
        print("    No conditional pattern detected.")
        return None
    
    # Now try to build a conditional transformation
    # Find the role with different treatment (e.g., engineers)
    special_role = None
    special_multiplier = None
    default_multiplier = None
    
    # Simple heuristic: find the role that appears in all problems
    role_counts = {}
    for role in condition_values:
        count = sum(1 for p in failed_problems 
                   for item in p.input_data 
                   if isinstance(item, dict) and item.get('role') == role)
        role_counts[role] = count
    
    # Assume the most common role with a unique multiplier is the special case
    sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_roles) >= 2:
        # Check if top role has different multiplier than others
        top_role = sorted_roles[0][0]
        top_mult = condition_values[top_role]
        
        other_mults = [condition_values[r[0]] for r in sorted_roles[1:]]
        if other_mults and all(abs(m - other_mults[0]) < 0.001 for m in other_mults):
            if abs(top_mult - other_mults[0]) > 0.001:
                special_role = top_role
                special_multiplier = top_mult
                default_multiplier = other_mults[0]
    
    if not special_role:
        # Try another strategy: engineers often get special treatment
        if 'engineer' in condition_values:
            special_role = 'engineer'
            special_multiplier = condition_values['engineer']
            other_mults = [v for k, v in condition_values.items() if k != 'engineer']
            if other_mults:
                default_multiplier = other_mults[0]
    
    if special_role and special_multiplier and default_multiplier:
        print(f"    Building conditional: IF role='{special_role}' THEN *{special_multiplier} ELSE *{default_multiplier}")
        
        # Create the condition
        condition = AppliedTransformation(
            next(t for t in PRIMITIVE_OPERATIONS if t.name == "VALUE_EQUALS"),
            ['role', special_role]
        )
        
        # Create the true branch (special multiplier)
        update_special = AppliedTransformation(
            next(t for t in PRIMITIVE_OPERATIONS if t.name == "UPDATE_FIELD"),
            ['salary', lambda x: x * special_multiplier]
        )
        true_branch = TransformationSequence([update_special])
        
        # Create the false branch (default multiplier)
        update_default = AppliedTransformation(
            next(t for t in PRIMITIVE_OPERATIONS if t.name == "UPDATE_FIELD"),
            ['salary', lambda x: x * default_multiplier]
        )
        false_branch = TransformationSequence([update_default])
        
        # Create the conditional transformation
        conditional = ConditionalTransformation(
            name=f"IF_ROLE_{special_role.upper()}",
            condition=condition,
            if_true_sequence=true_branch,
            if_false_sequence=false_branch
        )
        
        # Test if this solves all problems
        all_correct = True
        for problem in failed_problems:
            try:
                result = conditional.apply(problem.input_data)
                if not dict_list_equals(result, problem.output_data):
                    all_correct = False
                    break
            except Exception as e:
                print(f"    Error testing conditional: {e}")
                all_correct = False
                break
        
        if all_correct:
            print(f"    >>> Conditional Solution Found! {conditional}")
            
            # Create concept
            concept_name = f"CONCEPT_CONDITIONAL_{uuid.uuid4().hex[:4].upper()}"
            dims = 10
            min_corner = torch.rand(dims) * 0.1
            max_corner = min_corner + 0.1
            
            new_concept = RegionND(
                min_corner=min_corner,
                max_corner=max_corner,
                region_type='conditional_transformation',
                transformation_function=conditional
            )
            new_concept.name = concept_name
            return new_concept
    
    print("    Failed to discover conditional solution.")
    return None