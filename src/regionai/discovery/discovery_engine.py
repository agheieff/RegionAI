"""
Unified discovery engine with strategy pattern for different discovery approaches.
"""
from typing import List, Optional, Dict, Any, Set, Tuple, Protocol
from abc import ABC, abstractmethod
import torch
import uuid
from collections import deque
from dataclasses import dataclass

from ..data.problem import Problem
from ..geometry.region import RegionND
from .transformation import (
    Transformation, TransformationSequence, AppliedTransformation,
    ConditionalTransformation, ForEachTransformation,
    PRIMITIVE_OPERATIONS, INVERSE_OPERATIONS
)


class DiscoveryStrategy(ABC):
    """Abstract base class for discovery strategies."""
    
    @abstractmethod
    def discover(self, problems: List[Problem]) -> Optional[RegionND]:
        """
        Discover a new concept/transformation from failed problems.
        
        Args:
            problems: List of problems that failed with existing transformations
            
        Returns:
            A new RegionND representing the discovered concept, or None
        """
        pass
    
    def _create_concept_region(self, 
                             transformation: TransformationSequence,
                             concept_name: str,
                             dims: int) -> RegionND:
        """Helper to create a region for a discovered concept."""
        min_corner = torch.rand(dims) * 0.1
        max_corner = min_corner + 0.1
        
        region = RegionND(
            min_corner=min_corner,
            max_corner=max_corner,
            region_type='transformation',
            transformation_function=transformation
        )
        region.name = concept_name
        return region


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
                marker = torch.tensor([-999.0])
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
            if primitive.input_type != "tensor":
                continue
                
            if primitive.num_args == 0:
                new_applied = AppliedTransformation(primitive, [])
                new_seq = TransformationSequence(sequence.transformations + [new_applied])
                queue.append(new_seq)
            
            # Handle operations needing arguments
            if primitive.name in ["MULTIPLY", "ADD", "POWER", "DIVIDE"]:
                for arg in [1, 2, 3, 4, 5, 10]:
                    new_applied = AppliedTransformation(primitive, [arg])
                    new_seq = TransformationSequence(sequence.transformations + [new_applied])
                    queue.append(new_seq)
    
    def _generate_concept_name(self, sequence: TransformationSequence) -> str:
        """Generate descriptive name for discovered concept."""
        if len(sequence) == 1:
            return f"CONCEPT_{sequence.transformations[0].name}_{uuid.uuid4().hex[:4].upper()}"
        else:
            return f"CONCEPT_COMPOSED_{uuid.uuid4().hex[:4].upper()}"


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
            except:
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
            except:
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


class UnifiedDiscoveryEngine:
    """
    Main discovery engine that orchestrates different strategies.
    """
    
    def __init__(self):
        self.strategies = {
            'sequential': SequentialDiscovery(),
            'conditional': ConditionalDiscovery(),
            'iterative': IterativeDiscovery()
        }
        self.discovery_order = ['sequential', 'conditional', 'iterative']
    
    def discover(self, problems: List[Problem], 
                strategy: Optional[str] = None) -> Optional[RegionND]:
        """
        Discover new concepts using specified or all strategies.
        
        Args:
            problems: Failed problems to analyze
            strategy: Specific strategy to use, or None to try all
            
        Returns:
            Discovered concept region or None
        """
        if strategy:
            if strategy in self.strategies:
                return self.strategies[strategy].discover(problems)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
        
        # Try strategies in order
        for strat_name in self.discovery_order:
            print(f"\nTrying {strat_name} discovery...")
            result = self.strategies[strat_name].discover(problems)
            if result:
                print(f"Success with {strat_name} discovery!")
                return result
        
        return None
    
    def add_strategy(self, name: str, strategy: DiscoveryStrategy):
        """Add a new discovery strategy."""
        self.strategies[name] = strategy
        if name not in self.discovery_order:
            self.discovery_order.append(name)
    
    def set_discovery_order(self, order: List[str]):
        """Set the order in which strategies are tried."""
        # Validate all strategies exist
        for strat in order:
            if strat not in self.strategies:
                raise ValueError(f"Unknown strategy: {strat}")
        self.discovery_order = order