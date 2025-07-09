"""
The ConceptDiscovery module, responsible for creating new concepts
from patterns of failure.
"""
from typing import List, Optional
import torch
import uuid

from regionai.data.problem import Problem
from regionai.geometry.region import RegionND

def discover_concept_from_failures(failed_problems: List[Problem]) -> Optional[RegionND]:
    """
    Analyzes a list of failed problems and attempts to derive a single
    new concept that can solve them.
    
    This first version will implement a simple 'rote memorization' for transformations.
    """
    print("\n--- Phase 2: Analyzing failures to discover a new concept ---")
    
    if not failed_problems:
        print("    No failures provided. Nothing to learn.")
        return None
    
    # 1. Verify all problems are of the same type
    problem_type = failed_problems[0].problem_type
    if not all(p.problem_type == problem_type for p in failed_problems):
        print("    Failures are of mixed types. Cannot generalize yet.")
        return None
    
    if problem_type != 'transformation':
        print(f"    Discovery for problem type '{problem_type}' is not yet implemented.")
        return None
    
    # 2. Create the transformation function via a lookup table (rote memorization)
    # Tensors are not hashable, so we convert them to tuples to use as dict keys.
    lookup_table = {
        tuple(p.input_data.flatten().tolist()): p.output_data
        for p in failed_problems
    }
    print(f"    Built a lookup table with {len(lookup_table)} examples.")
    
    def transformation_function(x: torch.Tensor) -> Optional[torch.Tensor]:
        key = tuple(x.flatten().tolist())
        return lookup_table.get(key)
    
    # 3. Create the new RegionND for this concept
    new_concept_name = f"TRANSFORM_{uuid.uuid4().hex[:6].upper()}"
    print(f"    Generalizing failures into a new concept named '{new_concept_name}'.")
    
    # For now, place the new concept in a default, random part of the space.
    # The geometric location of transformation concepts is a problem for a later day.
    dims = failed_problems[0].input_data.shape[0]
    min_corner = torch.rand(dims) * 0.1
    max_corner = min_corner + 0.1  # Create a small box
    
    new_concept = RegionND(
        min_corner=min_corner,
        max_corner=max_corner,
        region_type='transformation',
        transformation_function=transformation_function
    )
    new_concept.name = new_concept_name  # Add name as an attribute
    
    return new_concept