"""
Sequential discovery strategy - finds linear sequences of transformations.
"""
from typing import List, Optional
from collections import deque
import torch
import uuid

from .base import DiscoveryStrategy
from tier1.data.problem import Problem
from tier1.core.region import RegionND
from tier1.core.transformation import (
    TransformationSequence, AppliedTransformation,
    PRIMITIVE_OPERATIONS
)


class SequentialDiscovery(DiscoveryStrategy):
    """
    Basic sequential discovery - finds linear sequences of transformations.
    Original implementation from discover.py
    """
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
    
    def discover(self, problems: List[Problem]) -> Optional[RegionND]:
        """Discover sequential compositions of primitive operations."""
        if not problems:
            return None
        
        # Validate all problems are transformation type
        problem_type = problems[0].problem_type
        if not all(p.problem_type == problem_type for p in problems) or problem_type != 'transformation':
            return None
        
        # BFS for transformation sequences
        search_queue = deque()
        
        # Initialize with single primitives
        for primitive in PRIMITIVE_OPERATIONS:
            if primitive.num_args == 0:
                applied = AppliedTransformation(primitive, [])
                seq = TransformationSequence([applied])
                search_queue.append(seq)
            elif primitive.num_args == 1 and primitive.name == "ADD_TENSOR":
                # Special case for doubling
                from tier1.transformation import UseInputAsArgument
                marker = UseInputAsArgument()
                applied = AppliedTransformation(primitive, [marker])
                seq = TransformationSequence([applied])
                search_queue.append(seq)
        
        while search_queue:
            current_sequence = search_queue.popleft()
            
            if len(current_sequence) > self.max_depth:
                return None
            
            # Test against all problems
            if self._test_sequence(current_sequence, problems):
                # Found solution!
                concept_name = self._generate_concept_name(current_sequence)
                dims = problems[0].input_data.dim()
                return self._create_concept_region(current_sequence, concept_name, dims)
            
            # Expand search
            self._expand_search(current_sequence, search_queue)
        
        return None
    
    def _test_sequence(self, sequence: TransformationSequence, problems: List[Problem]) -> bool:
        """Test if sequence solves all problems."""
        for problem in problems:
            result = sequence.apply(problem.input_data)
            if not torch.equal(result, problem.output_data):
                return False
        return True
    
    def _expand_search(self, sequence: TransformationSequence, queue: deque):
        """Add expanded sequences to search queue."""
        for primitive in PRIMITIVE_OPERATIONS:
            if primitive.input_type not in ["tensor", "vector"]:
                continue
                
            if primitive.num_args == 0:
                new_applied = AppliedTransformation(primitive, [])
                new_seq = TransformationSequence(sequence.applied_transformations + [new_applied])
                queue.append(new_seq)
            
            # Handle operations needing arguments
            if primitive.name in ["MULTIPLY", "ADD", "POWER", "DIVIDE"]:
                for arg in [1, 2, 3, 4, 5, 10]:
                    new_applied = AppliedTransformation(primitive, [arg])
                    new_seq = TransformationSequence(sequence.applied_transformations + [new_applied])
                    queue.append(new_seq)
    
    def _generate_concept_name(self, sequence: TransformationSequence) -> str:
        """Generate descriptive name for discovered concept."""
        if len(sequence.applied_transformations) == 1:
            return f"CONCEPT_{sequence.applied_transformations[0].transformation.name}_{uuid.uuid4().hex[:4].upper()}"
        else:
            return f"CONCEPT_COMPOSED_{uuid.uuid4().hex[:4].upper()}"