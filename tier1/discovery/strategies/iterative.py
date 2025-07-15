"""
Iterative discovery strategy - discovers FOR-EACH patterns with nested conditionals.
"""
from typing import List, Optional, Dict, Any, Set
import uuid

from .base import DiscoveryStrategy
from tier1.data.problem import Problem
from tier1.core.region import RegionND
from tier1.core.transformation import (
    Transformation, TransformationSequence, AppliedTransformation,
    ForEachTransformation
)


class IterativeDiscovery(DiscoveryStrategy):
    """
    Discovery of iterative patterns (FOR-EACH with nested conditionals).
    From discover_iterative.py
    """
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
    
    def discover(self, problems: List[Problem]) -> Optional[RegionND]:
        """Discover iterative transformation patterns."""
        if not problems:
            return None
        
        # Extract candidates
        param_candidates = self._extract_parameter_candidates(problems)
        
        # Try to infer item transformation
        for problem in problems:
            if not isinstance(problem.input_data, list) or not isinstance(problem.output_data, list):
                continue
            
            item_transform = self._infer_item_transformation(
                problem.input_data,
                problem.output_data,
                param_candidates
            )
            
            if item_transform:
                # Create FOR_EACH transformation
                for_each = ForEachTransformation(item_transform)
                
                # Test on all problems
                if self._test_for_each(for_each, problems):
                    concept_name = f"CONCEPT_ITERATIVE_{uuid.uuid4().hex[:4].upper()}"
                    dims = 5  # Default for structured data
                    
                    seq = TransformationSequence([
                        AppliedTransformation(
                            Transformation("FOR_EACH", for_each),
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
            'categories': {}
        }
        
        for problem in problems:
            if isinstance(problem.input_data, list):
                for item in problem.input_data:
                    if isinstance(item, dict):
                        candidates['keys'].update(item.keys())
                        
                        # Track category values
                        if 'category' in item:
                            cat = item['category']
                            if cat not in candidates['categories']:
                                candidates['categories'][cat] = []
                            candidates['categories'][cat].append(item)
        
        return candidates
    
    def _infer_item_transformation(self,
                                 input_items: List[Dict[str, Any]],
                                 output_items: List[Dict[str, Any]],
                                 param_candidates: Dict[str, Set[Any]]) -> Optional[Any]:
        """Infer transformation applied to each item."""
        if len(input_items) != len(output_items):
            return None
        
        # Analyze transformations
        category_rules = {}
        
        for inp, out in zip(input_items, output_items):
            if 'category' in inp and 'price' in inp and 'final_price' in out:
                category = inp['category']
                multiplier = out['final_price'] / inp['price']
                
                if category not in category_rules:
                    category_rules[category] = []
                category_rules[category].append(multiplier)
        
        # Check consistency
        final_rules = {}
        for cat, multipliers in category_rules.items():
            if all(abs(m - multipliers[0]) < 0.001 for m in multipliers):
                final_rules[cat] = multipliers[0]
        
        if final_rules:
            # Create conditional transformation
            def item_transform(item):
                if isinstance(item, dict) and 'category' in item and 'price' in item:
                    cat = item['category']
                    if cat in final_rules:
                        result = item.copy()
                        result['final_price'] = item['price'] * final_rules[cat]
                        return result
                return item
            
            return item_transform
        
        return None
    
    def _test_for_each(self, for_each: ForEachTransformation, problems: List[Problem]) -> bool:
        """Test if FOR_EACH transformation solves all problems."""
        for problem in problems:
            try:
                result = for_each(problem.input_data)
                if isinstance(result, list) and isinstance(problem.output_data, list):
                    if not self._list_equals(result, problem.output_data):
                        return False
                else:
                    return False
            except (TypeError, ValueError, AttributeError, KeyError, IndexError, Exception):
                # Transformation execution failed - this is expected for invalid transformations
                return False
        return True
    
    def _list_equals(self, list1: List[Any], list2: List[Any]) -> bool:
        """Compare two lists for equality."""
        if len(list1) != len(list2):
            return False
        
        for item1, item2 in zip(list1, list2):
            if isinstance(item1, dict) and isinstance(item2, dict):
                if not self._dict_equals(item1, item2):
                    return False
            elif item1 != item2:
                return False
        
        return True
    
    def _dict_equals(self, d1: Dict[str, Any], d2: Dict[str, Any]) -> bool:
        """Compare two dictionaries for equality."""
        if set(d1.keys()) != set(d2.keys()):
            return False
        
        for key in d1.keys():
            v1, v2 = d1[key], d2[key]
            if isinstance(v1, float) and isinstance(v2, float):
                if abs(v1 - v2) > 1e-5:
                    return False
            elif v1 != v2:
                return False
        
        return True