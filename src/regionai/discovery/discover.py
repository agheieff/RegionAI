"""
The ConceptDiscovery module, responsible for creating new concepts
from patterns of failure.
"""
from typing import List, Optional
import torch
import uuid

from regionai.data.problem import Problem
from regionai.geometry.region import RegionND
from regionai.discovery.transformation import PRIMITIVE_OPERATIONS, TransformationSequence

def discover_concept_from_failures(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Analyzes a list of failed problems and attempts to derive a single
    new concept that can solve them by finding a general transformation.
    """
    print("\n--- Phase 2: Analyzing failures to discover a new concept ---")
    
    if not failed_problems:
        print("    No failures provided. Nothing to learn.")
        return None
    
    problem_type = failed_problems[0].problem_type
    if not all(p.problem_type == problem_type for p in failed_problems) or problem_type != 'transformation':
        print("    Discovery requires a consistent set of 'transformation' problems.")
        return None
    
    # --- Begin Algorithm Search ---
    print(f"    Searching for a primitive operation that solves all {len(failed_problems)} failures...")
    
    # 1. Brute-force search through all known primitive operations.
    # For now, we only search for a single-step algorithm.
    for primitive in PRIMITIVE_OPERATIONS:
        is_consistent_solution = True
        # 2. Test this primitive against EVERY failed problem.
        for problem in failed_problems:
            # Apply the operation
            result = primitive.operation(problem.input_data)
            
            # Check if the result matches the expected output
            if not torch.equal(result, problem.output_data):
                is_consistent_solution = False
                break  # This primitive is not the solution, try the next one.
        
        # 3. If the primitive worked for ALL problems, we have found our algorithm!
        if is_consistent_solution:
            print(f"    >>> Generalization Found! The '{primitive.name}' operation solves all failures.")
            
            # 4. Create a TransformationSequence representing this algorithm.
            successful_sequence = TransformationSequence([primitive])
            
            # 5. Create the new concept region with this algorithm.
            new_concept_name = f"CONCEPT_{primitive.name}_{uuid.uuid4().hex[:4].upper()}"
            print(f"    Creating new concept '{new_concept_name}'...")
            
            dims = failed_problems[0].input_data.dim()
            min_corner = torch.rand(dims) * 0.1
            max_corner = min_corner + 0.1
            
            new_concept = RegionND(
                min_corner=min_corner,
                max_corner=max_corner,
                region_type='transformation',
                # Store the entire sequence object, not just the function.
                transformation_function=successful_sequence
            )
            new_concept.name = new_concept_name  # Add name as an attribute
            return new_concept
    
    # If the loop finishes without finding a working primitive
    print("    --- Search failed. No single primitive operation could solve all problems. ---")
    return None