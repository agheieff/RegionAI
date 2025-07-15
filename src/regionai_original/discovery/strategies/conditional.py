"""
Conditional discovery strategy - discovers IF-THEN-ELSE patterns.
"""
from typing import List, Optional, Dict, Any, Set, Tuple
import torch
import uuid

from .base import DiscoveryStrategy
from ...data.problem import Problem
from ...core.region import RegionND
from ...core.transformation import (
    Transformation, TransformationSequence, AppliedTransformation,
    ConditionalTransformation
)


class ConditionalDiscovery(DiscoveryStrategy):
    """
    Discovery of conditional transformations (IF-THEN-ELSE patterns).
    From discover_conditional.py
    """
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
    
    def discover(self, problems: List[Problem]) -> Optional[RegionND]:
        """Discover conditional transformation patterns."""
        if not problems:
            return None
        
        # Extract parameter candidates
        param_candidates = self._extract_parameter_candidates(problems)
        
        # Try to discover condition patterns
        for key in param_candidates['keys']:
            for value_set in param_candidates['values'].get(key, []):
                condition = self._create_condition(key, value_set)
                
                # Split problems by condition
                if_problems, else_problems = self._split_by_condition(problems, condition)
                
                if if_problems and else_problems:
                    # Try to find transformations for each branch
                    if_transform = self._discover_branch_transform(if_problems)
                    else_transform = self._discover_branch_transform(else_problems)
                    
                    if if_transform and else_transform:
                        # Create conditional transformation
                        conditional = ConditionalTransformation(
                            condition=condition,
                            if_transform=if_transform,
                            else_transform=else_transform
                        )
                        
                        # Test on all problems
                        if self._test_conditional(conditional, problems):
                            concept_name = f"CONCEPT_CONDITIONAL_{uuid.uuid4().hex[:4].upper()}"
                            dims = 5  # Default for structured data
                            
                            seq = TransformationSequence([
                                AppliedTransformation(
                                    Transformation("CONDITIONAL", conditional),
                                    []
                                )
                            ])
                            
                            return self._create_concept_region(seq, concept_name, dims)
        
        return None
    
    def _extract_parameter_candidates(self, problems: List[Problem]) -> Dict[str, Set[Any]]:
        """Extract potential parameters from problem data."""
        candidates = {
            'keys': set(),
            'values': {},
            'multipliers': set()
        }
        
        for problem in problems:
            if isinstance(problem.input_data, list):
                for item in problem.input_data:
                    if isinstance(item, dict):
                        candidates['keys'].update(item.keys())
                        for key, value in item.items():
                            if key not in candidates['values']:
                                candidates['values'][key] = set()
                            candidates['values'][key].add(value)
        
        return candidates
    
    def _create_condition(self, key: str, value: Any):
        """Create a condition function."""
        return lambda x: isinstance(x, dict) and x.get(key) == value
    
    def _split_by_condition(self, problems: List[Problem], condition) -> Tuple[List[Problem], List[Problem]]:
        """Split problems based on condition evaluation."""
        if_problems = []
        else_problems = []
        
        for problem in problems:
            if isinstance(problem.input_data, list) and len(problem.input_data) > 0:
                # Check first item (simplified)
                if condition(problem.input_data[0]):
                    if_problems.append(problem)
                else:
                    else_problems.append(problem)
        
        return if_problems, else_problems
    
    def _discover_branch_transform(self, problems: List[Problem]) -> Optional[Any]:
        """Discover transformation for a condition branch."""
        if not problems:
            return None
        
        # Simplified: look for common multipliers
        multipliers = set()
        
        for problem in problems:
            if isinstance(problem.input_data, list) and isinstance(problem.output_data, list):
                for inp, out in zip(problem.input_data, problem.output_data):
                    if isinstance(inp, dict) and isinstance(out, dict):
                        if 'salary' in inp and 'salary' in out and inp['salary'] > 0:
                            ratio = out['salary'] / inp['salary']
                            multipliers.add(round(ratio, 3))
        
        if len(multipliers) == 1:
            mult = list(multipliers)[0]
            return lambda x: x['salary'] * mult if isinstance(x, dict) else x
        
        return None
    
    def _test_conditional(self, conditional: ConditionalTransformation, problems: List[Problem]) -> bool:
        """Test if conditional transformation solves all problems."""
        for problem in problems:
            try:
                result = conditional(problem.input_data)
                if isinstance(result, list) and isinstance(problem.output_data, list):
                    if not self._dict_list_equals(result, problem.output_data):
                        return False
                else:
                    return False
            except (TypeError, ValueError, AttributeError, KeyError, IndexError, Exception):
                # Transformation execution failed - this is expected for invalid transformations
                return False
        return True
    
    def _dict_list_equals(self, list1: List[Dict[str, Any]], list2: List[Dict[str, Any]]) -> bool:
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