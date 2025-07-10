"""
Enhanced discovery module that handles structured data and parameterized transformations.
"""
from typing import List, Optional, Dict, Any, Set
import torch
import uuid
from collections import deque

from regionai.data.problem import Problem, ProblemDataType
from regionai.geometry.region import RegionND
from regionai.discovery.transformation import (
    PRIMITIVE_OPERATIONS, TransformationSequence, INVERSE_OPERATIONS,
    AppliedTransformation, Transformation
)


def extract_keys_from_data(data: List[Dict[str, Any]]) -> Set[str]:
    """Extract all unique keys from a list of dictionaries."""
    keys = set()
    for item in data:
        if isinstance(item, dict):
            keys.update(item.keys())
    return keys


def extract_values_for_key(data: List[Dict[str, Any]], key: str) -> Set[Any]:
    """Extract all unique values for a given key from a list of dictionaries."""
    values = set()
    for item in data:
        if isinstance(item, dict) and key in item:
            values.add(item[key])
    return values


def infer_data_type(data: ProblemDataType) -> str:
    """Infer the type of data for type checking."""
    if isinstance(data, torch.Tensor):
        if data.numel() == 1:
            return "scalar"
        else:
            return "vector"
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return "dict_list"
    elif isinstance(data, (int, float)):
        return "scalar"
    else:
        return "unknown"


def discover_concept_from_failures(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Enhanced discovery that handles structured data and parameterized transformations.
    """
    print("\n--- Phase 2: Analyzing failures to discover a new concept ---")
    
    if not failed_problems:
        print("    No failures provided. Nothing to learn.")
        return None
    
    problem_type = failed_problems[0].problem_type
    if not all(p.problem_type == problem_type for p in failed_problems) or problem_type != 'transformation':
        print("    Discovery requires a consistent set of 'transformation' problems.")
        return None
    
    print(f"    Searching for operations that solve all {len(failed_problems)} failures...")
    
    # Extract parameter candidates from the problem data
    param_candidates = {
        'keys': set(),
        'values': {}
    }
    
    for problem in failed_problems:
        if isinstance(problem.input_data, list):
            keys = extract_keys_from_data(problem.input_data)
            param_candidates['keys'].update(keys)
            
            for key in keys:
                if key not in param_candidates['values']:
                    param_candidates['values'][key] = set()
                values = extract_values_for_key(problem.input_data, key)
                param_candidates['values'][key].update(values)
    
    print(f"    Found parameter candidates - Keys: {param_candidates['keys']}")
    
    # Initialize search queue
    search_queue = deque()
    
    # Add all primitives to the queue with appropriate arguments
    for primitive in PRIMITIVE_OPERATIONS:
        if primitive.num_args == 0:
            # No arguments needed
            applied = AppliedTransformation(primitive, [])
            seq = TransformationSequence([applied])
            search_queue.append(seq)
            
        elif primitive.name == "MAP_GET":
            # Try each key as a parameter
            for key in param_candidates['keys']:
                applied = AppliedTransformation(primitive, [key])
                seq = TransformationSequence([applied])
                search_queue.append(seq)
                
        elif primitive.name == "FILTER_BY_VALUE":
            # Try each key-value combination
            for key in param_candidates['keys']:
                if key in param_candidates['values']:
                    for value in param_candidates['values'][key]:
                        applied = AppliedTransformation(primitive, [key, value])
                        seq = TransformationSequence([applied])
                        search_queue.append(seq)
                        
        elif primitive.name == "ADD_TENSOR":
            # Special marker for "use input"
            marker = torch.tensor([-999.0])
            applied = AppliedTransformation(primitive, [marker])
            seq = TransformationSequence([applied])
            search_queue.append(seq)
    
    MAX_SEARCH_DEPTH = 4  # Allow deeper search for structured data
    
    while search_queue:
        current_sequence = search_queue.popleft()
        
        if len(current_sequence) > MAX_SEARCH_DEPTH:
            continue
        
        # Test the current sequence against all problems
        is_consistent_solution = True
        
        for problem in failed_problems:
            try:
                result = current_sequence.apply(problem.input_data)
                
                # Handle different output types
                if isinstance(problem.output_data, torch.Tensor) and isinstance(result, torch.Tensor):
                    # Check dimensions match
                    if result.shape != problem.output_data.shape:
                        is_consistent_solution = False
                        break
                    if not torch.allclose(result, problem.output_data, rtol=1e-5):
                        is_consistent_solution = False
                        break
                elif result != problem.output_data:
                    is_consistent_solution = False
                    break
            except Exception:
                # If the sequence fails on any problem, it's not a solution
                is_consistent_solution = False
                break
        
        if is_consistent_solution:
            print(f"    >>> Solution Found! Sequence: {current_sequence} solves all failures.")
            
            # Create concept name
            if len(current_sequence) == 1:
                concept_name = f"CONCEPT_{current_sequence.transformations[0].name}_{uuid.uuid4().hex[:4].upper()}"
            else:
                concept_name = f"CONCEPT_STRUCTURED_{uuid.uuid4().hex[:4].upper()}"
            
            print(f"    Creating new concept '{concept_name}'...")
            
            # Create a simple region for now
            dims = 10  # Default dimensionality
            min_corner = torch.rand(dims) * 0.1
            max_corner = min_corner + 0.1
            
            new_concept = RegionND(
                min_corner=min_corner,
                max_corner=max_corner,
                region_type='transformation',
                transformation_function=current_sequence
            )
            new_concept.name = concept_name
            return new_concept
        
        # Expand the search by adding one more operation
        if len(current_sequence) < MAX_SEARCH_DEPTH:
            # Get the output type of the last operation
            last_transformation = current_sequence.transformations[-1]
            
            # Try to infer the output type from a sample execution
            try:
                sample_result = current_sequence.apply(failed_problems[0].input_data)
                last_output_type = infer_data_type(sample_result)
            except:
                # If we can't execute, use the declared type
                last_output_type = last_transformation.output_type
            
            for primitive in PRIMITIVE_OPERATIONS:
                # Type matching
                if primitive.input_type != last_output_type:
                    continue
                
                # Avoid inverse operations
                last_op_name = last_transformation.name
                if INVERSE_OPERATIONS.get(last_op_name) == primitive.name:
                    continue
                
                # Create new sequences with appropriate arguments
                if primitive.num_args == 0:
                    new_applied = AppliedTransformation(primitive, [])
                    new_applied_list = current_sequence.applied_transformations + [new_applied]
                    new_sequence = TransformationSequence(new_applied_list)
                    search_queue.append(new_sequence)
                    
                elif primitive.name == "MAP_GET":
                    for key in param_candidates['keys']:
                        new_applied = AppliedTransformation(primitive, [key])
                        new_applied_list = current_sequence.applied_transformations + [new_applied]
                        new_sequence = TransformationSequence(new_applied_list)
                        search_queue.append(new_sequence)
                        
                elif primitive.name == "FILTER_BY_VALUE":
                    for key in param_candidates['keys']:
                        if key in param_candidates['values']:
                            for value in param_candidates['values'][key]:
                                new_applied = AppliedTransformation(primitive, [key, value])
                                new_applied_list = current_sequence.applied_transformations + [new_applied]
                                new_sequence = TransformationSequence(new_applied_list)
                                search_queue.append(new_sequence)
    
    print("    --- Search failed. No solution found within the search depth. ---")
    return None