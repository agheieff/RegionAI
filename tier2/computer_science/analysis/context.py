"""
Defines the AnalysisContext, a container for all state related to a
single analysis run. This is crucial for eliminating global state and
ensuring that analysis is re-entrant and thread-safe.
"""
from dataclasses import dataclass, field
from typing import Dict, Union, TYPE_CHECKING, Set, Optional
import ast
from enum import Enum, auto

# Import the centralized configuration
from tier1.config import RegionAIConfig, DEFAULT_CONFIG

# Avoid circular imports
if TYPE_CHECKING:
    from tier1.region_algebra.abstract_domain_base import AbstractState
    from .function_summary import FunctionSummary
else:
    # Forward-declare types to avoid circular imports at runtime
    # Import the actual classes - abstract_domain_base has no circular deps
    from tier1.region_algebra.abstract_domain_base import AbstractState
    
    class FunctionSummary:
        pass


class LocationType(Enum):
    """Types of abstract memory locations."""
    STACK = auto()      # Stack-allocated variable
    HEAP = auto()       # Heap-allocated object
    GLOBAL = auto()     # Global variable
    UNKNOWN = auto()    # Unknown location


@dataclass(frozen=True)
class AbstractLocation:
    """
    Represents an abstract memory location for alias analysis.
    
    Locations are immutable and can be used as dictionary keys.
    """
    name: str               # Identifier for the location
    loc_type: LocationType  # Type of location
    allocation_site: Optional[int] = None  # Line number where allocated (for heap objects)
    
    def __str__(self):
        if self.allocation_site:
            return f"{self.name}@{self.allocation_site}"
        return self.name
    
    @classmethod
    def stack_var(cls, var_name: str) -> 'AbstractLocation':
        """Create a stack variable location."""
        return cls(name=var_name, loc_type=LocationType.STACK)
    
    @classmethod
    def heap_object(cls, alloc_site: int, obj_type: str = "object") -> 'AbstractLocation':
        """Create a heap object location."""
        return cls(name=f"heap_{obj_type}", loc_type=LocationType.HEAP, allocation_site=alloc_site)
    
    @classmethod
    def global_var(cls, var_name: str) -> 'AbstractLocation':
        """Create a global variable location."""
        return cls(name=var_name, loc_type=LocationType.GLOBAL)


@dataclass
class AnalysisContext:
    """Encapsulates all state for a single analysis run."""
    
    # The current abstract state of variables
    abstract_state: AbstractState = field(default_factory=lambda: AbstractState())
    
    # Cache for function summaries
    summaries: Dict[str, FunctionSummary] = field(default_factory=dict)
    
    # The configuration for this specific run
    config: RegionAIConfig = field(default_factory=lambda: DEFAULT_CONFIG)

    # You can add more state here as needed, e.g., error logs, warnings, etc.
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    
    # Variable state map for constant propagation analysis
    # Maps variable names to their constant values (as AST nodes) or "UNKNOWN"
    variable_state_map: Dict[str, Union[ast.AST, str]] = field(default_factory=dict)
    
    # Points-to map for alias analysis
    # Maps variable names to sets of abstract locations they may point to
    points_to_map: Dict[str, Set[AbstractLocation]] = field(default_factory=dict)

    def reset(self):
        """Resets the context for a new analysis."""
        self.abstract_state = AbstractState()
        self.summaries = {}
        self.errors = []
        self.warnings = []
        self.variable_state_map = {}
        self.points_to_map = {}
    
    def add_error(self, error: str):
        """Add an error message to the context."""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning message to the context."""
        self.warnings.append(warning)
    
    def get_or_compute_summary(self, function_name: str, compute_fn) -> 'FunctionSummary':
        """Get cached summary or compute it if not available."""
        if function_name not in self.summaries:
            self.summaries[function_name] = compute_fn()
        return self.summaries[function_name]
    
    # Alias analysis helper methods
    def add_points_to(self, var_name: str, location: AbstractLocation):
        """Add a location to the points-to set of a variable."""
        if var_name not in self.points_to_map:
            self.points_to_map[var_name] = set()
        self.points_to_map[var_name].add(location)
    
    def set_points_to(self, var_name: str, locations: Set[AbstractLocation]):
        """Set the complete points-to set for a variable."""
        self.points_to_map[var_name] = locations.copy()
    
    def get_points_to(self, var_name: str) -> Set[AbstractLocation]:
        """Get the points-to set for a variable."""
        return self.points_to_map.get(var_name, set())
    
    def clear_points_to(self, var_name: str):
        """Clear the points-to set for a variable."""
        if var_name in self.points_to_map:
            del self.points_to_map[var_name]
    
    def may_alias(self, var1: str, var2: str) -> bool:
        """Check if two variables may alias (point to same location)."""
        pts1 = self.get_points_to(var1)
        pts2 = self.get_points_to(var2)
        return bool(pts1 & pts2)  # Non-empty intersection means may alias