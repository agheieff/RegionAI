"""
Defines the AnalysisContext, a container for all state related to a
single analysis run. This is crucial for eliminating global state and
ensuring that analysis is re-entrant and thread-safe.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Union, TYPE_CHECKING
import ast

# Import the centralized configuration
from ..config import RegionAIConfig, DEFAULT_CONFIG

# Avoid circular imports
if TYPE_CHECKING:
    from ..discovery.abstract_domain_base import AbstractState
    from .function_summary import FunctionSummary
else:
    # Forward-declare types to avoid circular imports at runtime
    # Import the actual classes - abstract_domain_base has no circular deps
    from ..discovery.abstract_domain_base import AbstractState
    
    class FunctionSummary:
        pass


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

    def reset(self):
        """Resets the context for a new analysis."""
        self.abstract_state = AbstractState()
        self.summaries = {}
        self.errors = []
        self.warnings = []
        self.variable_state_map = {}
    
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