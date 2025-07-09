"""
The ConceptDiscovery module, responsible for creating new concepts
from patterns of failure.
"""
from typing import List, Optional
import torch
import uuid
from collections import deque

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
    
    # --- Begin Compositional Algorithm Search ---
    print(f"    Searching for a sequence of operations that solves all {len(failed_problems)} failures...")
    
    # 1. Initialize the search queue. It will hold TransformationSequence objects.
    # Start with all sequences of length 1.
    search_queue = deque([TransformationSequence([p]) for p in PRIMITIVE_OPERATIONS])
    
    # Set a maximum search depth to prevent infinite loops.
    MAX_SEARCH_DEPTH = 2  # Start with a small depth
    
    while search_queue:
        current_sequence = search_queue.popleft()
        
        # Stop searching if sequences get too long.
        if len(current_sequence) > MAX_SEARCH_DEPTH:
            print("    --- Search failed. Reached maximum search depth. ---")
            return None
        
        # 2. Test the current sequence against all failed problems.
        is_consistent_solution = True
        for problem in failed_problems:
            result = current_sequence.apply(problem.input_data)
            if not torch.equal(result, problem.output_data):
                is_consistent_solution = False
                break
        
        # 3. If the sequence worked for ALL problems, we have found our algorithm!
        if is_consistent_solution:
            print(f"    >>> Compositional Solution Found! Sequence: {current_sequence} solves all failures.")
            
            # Create appropriate concept name based on composition
            if len(current_sequence) == 1:
                concept_name = f"CONCEPT_{current_sequence.transformations[0].name}_{uuid.uuid4().hex[:4].upper()}"
            else:
                concept_name = f"CONCEPT_COMPOSED_{uuid.uuid4().hex[:4].upper()}"
            
            print(f"    Creating new concept '{concept_name}'...")
            
            dims = failed_problems[0].input_data.dim()
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
        
        # 4. If this sequence didn't work, expand it by one step and add the new
        # longer sequences to the back of the queue.
        if len(current_sequence) < MAX_SEARCH_DEPTH:
            for primitive in PRIMITIVE_OPERATIONS:
                new_sequence = TransformationSequence(current_sequence.transformations + [primitive])
                search_queue.append(new_sequence)
    
    # If the while loop finishes, no solution was found.
    print("    --- Search failed. No solution found within the search depth. ---")
    return None