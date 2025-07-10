"""
Unified curriculum factory for generating all types of problems.
"""
import ast
import torch
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .problem import Problem


@dataclass
class CurriculumConfig:
    """Configuration for curriculum generation."""
    difficulty: str = "basic"  # basic, intermediate, advanced
    num_problems: Optional[int] = None
    seed: Optional[int] = None
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class CurriculumGenerator(ABC):
    """Base class for curriculum generators."""
    
    @abstractmethod
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        """Generate problems based on configuration."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this curriculum type."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this curriculum teaches."""
        pass


class TransformationCurriculumGenerator(CurriculumGenerator):
    """Generates transformation discovery problems."""
    
    name = "transformation"
    description = "Basic transformation discovery (ADD, MULTIPLY, etc.)"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Simple transformations
            problems.extend([
                Problem(
                    name="discover_add",
                    problem_type="transformation",
                    input_data=torch.tensor([1, 2, 3]),
                    output_data=torch.tensor([3, 4, 5]),
                    description="Discover ADD_2 transformation"
                ),
                Problem(
                    name="discover_multiply",
                    problem_type="transformation",
                    input_data=torch.tensor([1, 2, 3]),
                    output_data=torch.tensor([2, 4, 6]),
                    description="Discover MULTIPLY_2 transformation"
                ),
                Problem(
                    name="discover_sum",
                    problem_type="transformation",
                    input_data=torch.tensor([1, 2, 3]),
                    output_data=torch.tensor(6),
                    description="Discover SUM transformation"
                )
            ])
        
        elif config.difficulty == "intermediate":
            # Composed transformations
            problems.extend([
                Problem(
                    name="discover_add_then_multiply",
                    problem_type="transformation",
                    input_data=torch.tensor([1, 2, 3]),
                    output_data=torch.tensor([6, 8, 10]),
                    description="Discover ADD_2 then MULTIPLY_2"
                )
            ])
        
        return problems[:config.num_problems] if config.num_problems else problems


class SignAnalysisCurriculumGenerator(CurriculumGenerator):
    """Generates abstract sign analysis problems."""
    
    name = "sign_analysis"
    description = "Abstract sign analysis and property proving"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Basic sign proofs
            code1 = ast.parse("""x = input_positive_integer()
y = x * -1
z = y + -5""")
            
            problems.append(Problem(
                name="prove_negative_simple",
                problem_type="property_proof",
                input_data={'code': code1, 'spec': {'z': 'NEGATIVE'}},
                output_data={'z': True},
                description="Prove z is always negative"
            ))
            
            code2 = ast.parse("""a = input_positive_integer()
b = input_positive_integer()
c = a * b""")
            
            problems.append(Problem(
                name="prove_positive_product",
                problem_type="property_proof",
                input_data={'code': code2, 'spec': {'c': 'POSITIVE'}},
                output_data={'c': True},
                description="Prove product of positives is positive"
            ))
        
        elif config.difficulty == "advanced":
            # Complex sign analysis
            code3 = ast.parse("""x = input_integer()
if x > 0:
    y = x * 2
else:
    y = x * -3
z = y * y""")
            
            problems.append(Problem(
                name="prove_conditional_positive",
                problem_type="property_proof",
                input_data={'code': code3, 'spec': {'z': 'POSITIVE_OR_ZERO'}},
                output_data={'z': True},
                description="Prove z is never negative"
            ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class NullabilityCurriculumGenerator(CurriculumGenerator):
    """Generates null safety analysis problems."""
    
    name = "nullability"
    description = "Null pointer detection and safety analysis"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Basic null tracking
            code1 = ast.parse("""x = None
y = 42
z = y""")
            
            problems.append(Problem(
                name="basic_null_tracking",
                problem_type="nullability_analysis",
                input_data={'code': code1},
                output_data={'x': 'DEFINITELY_NULL', 'y': 'NOT_NULL', 'z': 'NOT_NULL'},
                description="Track null and non-null values"
            ))
        
        elif config.difficulty == "intermediate":
            # Null dereference detection
            code2 = ast.parse("""obj = get_object()
if obj is None:
    result = 0
else:
    result = obj.value""")
            
            problems.append(Problem(
                name="safe_null_handling",
                problem_type="null_safety",
                input_data={'code': code2},
                output_data={'errors': 0},
                description="Verify safe null handling"
            ))
            
            code3 = ast.parse("""obj = None
value = obj.field""")
            
            problems.append(Problem(
                name="null_dereference",
                problem_type="null_safety",
                input_data={'code': code3},
                output_data={'errors': 1, 'error_lines': [2]},
                description="Detect null pointer exception"
            ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class RangeAnalysisCurriculumGenerator(CurriculumGenerator):
    """Generates range/bounds analysis problems."""
    
    name = "range_analysis"
    description = "Array bounds checking and range analysis"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Simple bounds checking
            code1 = ast.parse("""arr = [1, 2, 3, 4, 5]
i = 2
value = arr[i]""")
            
            problems.append(Problem(
                name="safe_array_access",
                problem_type="bounds_checking",
                input_data={'code': code1},
                output_data={'errors': 0},
                description="Verify safe array access"
            ))
            
            code2 = ast.parse("""arr = [1, 2, 3]
i = 5
value = arr[i]""")
            
            problems.append(Problem(
                name="array_out_of_bounds",
                problem_type="bounds_checking",
                input_data={'code': code2},
                output_data={'errors': 1, 'error_lines': [3]},
                description="Detect array out of bounds"
            ))
        
        elif config.difficulty == "intermediate":
            # Loop bounds analysis
            code3 = ast.parse("""arr = [1, 2, 3, 4, 5]
for i in range(len(arr)):
    value = arr[i]""")
            
            problems.append(Problem(
                name="loop_bounds_safe",
                problem_type="bounds_checking",
                input_data={'code': code3},
                output_data={'errors': 0},
                description="Verify loop bounds are safe"
            ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class LoopAnalysisCurriculumGenerator(CurriculumGenerator):
    """Generates loop analysis problems."""
    
    name = "loop_analysis"
    description = "Loop termination and fixpoint analysis"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Simple counting loop
            code1 = ast.parse("""i = 0
while i < 10:
    i = i + 1""")
            
            problems.append(Problem(
                name="simple_counting_loop",
                problem_type="loop_analysis",
                input_data={'code': code1},
                output_data={'terminates': True, 'iterations': 10},
                description="Analyze simple counting loop"
            ))
        
        elif config.difficulty == "intermediate":
            # Nested loops
            code2 = ast.parse("""for i in range(5):
    for j in range(3):
        x = i + j""")
            
            problems.append(Problem(
                name="nested_loops",
                problem_type="loop_analysis",
                input_data={'code': code2},
                output_data={'terminates': True, 'total_iterations': 15},
                description="Analyze nested loops"
            ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class ConditionalCurriculumGenerator(CurriculumGenerator):
    """Generates conditional transformation problems."""
    
    name = "conditional"
    description = "IF-THEN-ELSE transformation patterns"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        # Salary bonus based on role
        problems.append(Problem(
            name="conditional_bonus",
            problem_type="transformation",
            input_data=[
                {"role": "engineer", "salary": 100000},
                {"role": "manager", "salary": 100000}
            ],
            output_data=[
                {"role": "engineer", "salary": 110000},
                {"role": "manager", "salary": 103000}
            ],
            description="Different bonus rates by role"
        ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class IterativeCurriculumGenerator(CurriculumGenerator):
    """Generates iterative transformation problems."""
    
    name = "iterative"
    description = "FOR-EACH loops with transformations"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        # Category-based pricing
        problems.append(Problem(
            name="iterative_pricing",
            problem_type="transformation",
            input_data=[
                {"category": "electronics", "price": 100},
                {"category": "books", "price": 50},
                {"category": "food", "price": 30}
            ],
            output_data=[
                {"category": "electronics", "price": 100, "final_price": 120},
                {"category": "books", "price": 50, "final_price": 55},
                {"category": "food", "price": 30, "final_price": 31.5}
            ],
            description="Apply category-specific pricing"
        ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class ASTOptimizationCurriculumGenerator(CurriculumGenerator):
    """Generates AST optimization problems."""
    
    name = "ast_optimization"
    description = "Code optimization through AST transformation"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        if config.difficulty == "basic":
            # Algebraic identities
            code1 = ast.parse("x = y + 0")
            optimized1 = ast.parse("x = y")
            
            problems.append(Problem(
                name="remove_additive_identity",
                problem_type="ast_optimization",
                input_data=code1,
                output_data=optimized1,
                description="Remove x + 0 → x"
            ))
            
            code2 = ast.parse("x = y * 1")
            optimized2 = ast.parse("x = y")
            
            problems.append(Problem(
                name="remove_multiplicative_identity",
                problem_type="ast_optimization",
                input_data=code2,
                output_data=optimized2,
                description="Remove x * 1 → x"
            ))
        
        elif config.difficulty == "intermediate":
            # Constant folding
            code3 = ast.parse("x = 2 + 3")
            optimized3 = ast.parse("x = 5")
            
            problems.append(Problem(
                name="constant_folding",
                problem_type="ast_optimization",
                input_data=code3,
                output_data=optimized3,
                description="Fold constant expressions"
            ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class InterproceduralCurriculumGenerator(CurriculumGenerator):
    """Generates interprocedural analysis problems."""
    
    name = "interprocedural"
    description = "Whole-program analysis across functions"
    
    def generate(self, config: CurriculumConfig) -> List[Problem]:
        problems = []
        
        # Null propagation across functions
        code1 = ast.parse("""def get_data():
    return None

def process():
    data = get_data()
    result = data.value""")
        
        problems.append(Problem(
            name="interprocedural_null",
            problem_type="interprocedural_analysis",
            input_data={'code': code1},
            output_data={'errors': 1, 'error_lines': [6]},
            description="Track null across function calls"
        ))
        
        return problems[:config.num_problems] if config.num_problems else problems


class CurriculumFactory:
    """
    Factory for creating curriculum problems.
    Unifies all curriculum generation into a single interface.
    """
    
    def __init__(self):
        self._generators: Dict[str, CurriculumGenerator] = {}
        self._register_default_generators()
    
    def _register_default_generators(self):
        """Register all default curriculum generators."""
        default_generators = [
            TransformationCurriculumGenerator(),
            SignAnalysisCurriculumGenerator(),
            NullabilityCurriculumGenerator(),
            RangeAnalysisCurriculumGenerator(),
            LoopAnalysisCurriculumGenerator(),
            ConditionalCurriculumGenerator(),
            IterativeCurriculumGenerator(),
            ASTOptimizationCurriculumGenerator(),
            InterproceduralCurriculumGenerator()
        ]
        
        for gen in default_generators:
            self.register_generator(gen.name, gen)
    
    def register_generator(self, name: str, generator: CurriculumGenerator):
        """Register a curriculum generator."""
        self._generators[name] = generator
    
    def create(self, curriculum_type: str, 
              config: Optional[Dict[str, Any]] = None) -> List[Problem]:
        """
        Create curriculum problems of the specified type.
        
        Args:
            curriculum_type: Type of curriculum to generate
            config: Configuration dict (converted to CurriculumConfig)
            
        Returns:
            List of generated problems
        """
        if curriculum_type not in self._generators:
            raise ValueError(f"Unknown curriculum type: {curriculum_type}. "
                           f"Available: {list(self._generators.keys())}")
        
        # Convert dict to config object
        if config is None:
            config = {}
        
        curriculum_config = CurriculumConfig(**config)
        
        # Generate problems
        generator = self._generators[curriculum_type]
        return generator.generate(curriculum_config)
    
    def create_mixed(self, types_and_configs: List[tuple]) -> List[Problem]:
        """
        Create a mixed curriculum from multiple types.
        
        Args:
            types_and_configs: List of (curriculum_type, config) tuples
            
        Returns:
            Combined list of problems
        """
        all_problems = []
        
        for curr_type, config in types_and_configs:
            problems = self.create(curr_type, config)
            all_problems.extend(problems)
        
        return all_problems
    
    def list_available(self) -> Dict[str, str]:
        """List all available curriculum types with descriptions."""
        return {
            name: gen.description 
            for name, gen in self._generators.items()
        }
    
    def get_generator(self, curriculum_type: str) -> CurriculumGenerator:
        """Get a specific generator instance."""
        if curriculum_type not in self._generators:
            raise ValueError(f"Unknown curriculum type: {curriculum_type}")
        return self._generators[curriculum_type]


# Global factory instance
_curriculum_factory = CurriculumFactory()


# Convenience functions
def create_curriculum(curriculum_type: str, **kwargs) -> List[Problem]:
    """Create curriculum problems of the specified type."""
    return _curriculum_factory.create(curriculum_type, kwargs)


def list_curricula() -> Dict[str, str]:
    """List all available curriculum types."""
    return _curriculum_factory.list_available()


def create_mixed_curriculum(curricula: List[tuple]) -> List[Problem]:
    """Create a mixed curriculum from multiple types."""
    return _curriculum_factory.create_mixed(curricula)