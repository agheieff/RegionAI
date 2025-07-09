"""
Enhanced discovery module that handles parameterized transformations.
"""
from typing import List, Optional, Tuple
import torch
import uuid
from collections import deque

from regionai.data.problem import Problem
from regionai.geometry.region import RegionND
from regionai.discovery.transformation import (
    PRIMITIVE_OPERATIONS, TransformationSequence, INVERSE_OPERATIONS,
    AppliedTransformation, Transformation
)


def find_consistent_args(
    primitive: Transformation, 
    failed_problems: List[Problem]
) -> Optional[List[torch.Tensor]]:
    """
    Try to find arguments that make this primitive work for all problems.
    
    For now, we use a simple heuristic: try using problem data as arguments.
    """
    if primitive.num_args == 0:
        # No arguments needed, just test if it works
        return []
    
    if primitive.num_args == 1:
        # Try different argument sources
        arg_candidates = []
        
        # Strategy 1: Use the input data itself (for doubling, etc.)
        # Check if using input_data as arg works for all problems
        works_with_input = True
        for problem in failed_problems:
            try:
                result = primitive.operation(problem.input_data, [problem.input_data])
                if not torch.equal(result, problem.output_data):
                    works_with_input = False
                    break
            except:
                works_with_input = False
                break
        
        if works_with_input:
            # Return the first problem's input as the argument template
            # In practice, we'd use the actual input at runtime
            return [failed_problems[0].input_data]
        
        # Strategy 2: Try using a constant derived from the problems
        # (Future enhancement: try more sophisticated strategies)
        
    return None


def discover_concept_from_failures(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Enhanced discovery that handles parameterized transformations.
    """
    print("\n--- Phase 2: Analyzing failures to discover a new concept ---")
    
    if not failed_problems:
        print("    No failures provided. Nothing to learn.")
        return None
    
    problem_type = failed_problems[0].problem_type
    if not all(p.problem_type == problem_type for p in failed_problems) or problem_type != 'transformation':
        print("    Discovery requires a consistent set of 'transformation' problems.")
        return None
    
    print(f"    Searching for operations (with arguments) that solve all {len(failed_problems)} failures...")
    
    # Try single primitives first (including those with arguments)
    for primitive in PRIMITIVE_OPERATIONS:
        if primitive.num_args == 0:
            # Test no-arg primitive
            is_consistent = True
            for problem in failed_problems:
                result = primitive.operation(problem.input_data)
                if not torch.equal(result, problem.output_data):
                    is_consistent = False
                    break
            
            if is_consistent:
                print(f"    >>> Solution Found! The '{primitive.name}' operation solves all failures.")
                applied = AppliedTransformation(primitive, [])
                sequence = TransformationSequence([applied])
                
                concept_name = f"CONCEPT_{primitive.name}_{uuid.uuid4().hex[:4].upper()}"
                print(f"    Creating new concept '{concept_name}'...")
                
                dims = failed_problems[0].input_data.dim()
                min_corner = torch.rand(dims) * 0.1
                max_corner = min_corner + 0.1
                
                new_concept = RegionND(
                    min_corner=min_corner,
                    max_corner=max_corner,
                    region_type='transformation',
                    transformation_function=sequence
                )
                new_concept.name = concept_name
                return new_concept
        
        else:
            # Test primitive with arguments
            # For ADD_TENSOR, we'll try using the input itself as the argument
            if primitive.name == "ADD_TENSOR":
                is_consistent = True
                for problem in failed_problems:
                    # Test if x + x equals the output
                    result = primitive.operation(problem.input_data, [problem.input_data])
                    if not torch.equal(result, problem.output_data):
                        is_consistent = False
                        break
                
                if is_consistent:
                    print(f"    >>> Parameterized Solution Found! '{primitive.name}(input)' solves all failures.")
                    # Create a special applied transformation that uses input as argument
                    # Note: In practice, we'd need a way to represent "use input as arg"
                    applied = AppliedTransformation(primitive, [torch.tensor([0.0])])  # Placeholder
                    sequence = TransformationSequence([applied])
                    
                    concept_name = f"CONCEPT_{primitive.name}_INPUT_{uuid.uuid4().hex[:4].upper()}"
                    print(f"    Creating new concept '{concept_name}'...")
                    
                    dims = failed_problems[0].input_data.dim()
                    min_corner = torch.rand(dims) * 0.1
                    max_corner = min_corner + 0.1
                    
                    new_concept = RegionND(
                        min_corner=min_corner,
                        max_corner=max_corner,
                        region_type='transformation',
                        transformation_function=sequence
                    )
                    new_concept.name = concept_name
                    # Mark that this uses input as argument
                    new_concept.uses_input_as_arg = True
                    return new_concept
    
    print("    --- Search failed. No single operation could solve all problems. ---")
    # TODO: Extend to multi-step sequences with arguments
    return None