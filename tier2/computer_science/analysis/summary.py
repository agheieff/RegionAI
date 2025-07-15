"""
Function summary system for interprocedural analysis.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, List, Tuple, Any
from tier1.region_algebra.abstract_domains import AbstractState


@dataclass(frozen=True)
class CallContext:
    """
    Represents the context of a function call for context-sensitive analysis.
    
    The context includes the function name and the abstract states of arguments,
    allowing different summaries for different calling contexts.
    """
    function_name: str
    parameter_states: Tuple[Any, ...]  # Using tuple for hashability
    call_site_id: Optional[int] = None  # Line number or unique ID of the call site
    
    @classmethod
    def from_call(cls, function_name: str, arg_states: List[AbstractState], call_site_id: Optional[int] = None) -> 'CallContext':
        """
        Create a CallContext from function name and argument states.
        
        We need to convert AbstractState objects to a hashable representation.
        """
        # Convert each AbstractState to a hashable tuple representation
        hashable_states = []
        for state in arg_states:
            # Extract key properties that define the state
            state_tuple = (
                # Sign states
                tuple(sorted((k, v) for k, v in getattr(state, 'sign_state', {}).items())),
                # Nullability states  
                tuple(sorted((k, v) for k, v in getattr(state, 'null_state', {}).items())),
                # Range states (if available)
                tuple(sorted((k, str(v)) for k, v in getattr(state, 'range_state', {}).items()))
            )
            hashable_states.append(state_tuple)
        
        return CallContext(function_name, tuple(hashable_states), call_site_id)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.function_name}{self.parameter_states}"


@dataclass
class FunctionSummary:
    """
    Captures the abstract behavior of a function for reuse in analysis.
    
    A function summary represents what we know about a function's behavior
    without having to re-analyze it every time it's called.
    """
    # Function identification
    function_name: str
    
    # Abstract states for parameters at function entry
    parameter_states: Dict[str, AbstractState] = field(default_factory=dict)
    
    # Abstract state of the return value
    return_state: AbstractState = field(default_factory=AbstractState)
    
    # Additional information for more precise analysis
    parameters: List[str] = field(default_factory=list)  # Parameter names in order
    always_returns: bool = True  # False if function might not return (infinite loop, exception)
    may_throw: bool = False  # True if function might throw an exception
    
    # Side effects tracking
    modifies_globals: Set[str] = field(default_factory=set)  # Global variables modified
    modifies_parameters: Set[str] = field(default_factory=set)  # Parameters modified (for mutables)
    
    # Preconditions and postconditions (for contract-based analysis)
    preconditions: List[str] = field(default_factory=list)  # Conditions that must hold on entry
    postconditions: List[str] = field(default_factory=list)  # Conditions guaranteed on exit
    
    def apply_to_call(self, call_args: Dict[str, AbstractState]) -> AbstractState:
        """
        Apply this summary to a specific function call.
        
        Args:
            call_args: Mapping of parameter names to their abstract states at call site
            
        Returns:
            The abstract state of the return value for this call
        """
        # For now, return the stored return state
        # In the future, this could be more sophisticated (e.g., context-sensitive)
        return self.return_state.copy()
    
    def is_pure(self) -> bool:
        """Check if function has no side effects."""
        return (not self.modifies_globals and 
                not self.modifies_parameters and
                self.always_returns and 
                not self.may_throw)
    
    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [f"Summary of {self.function_name}:"]
        
        # Parameters
        if self.parameter_states:
            lines.append("  Parameters:")
            for param, state in self.parameter_states.items():
                sign = state.get_sign(param) if hasattr(state, 'get_sign') else None
                null = state.get_nullability(param) if hasattr(state, 'get_nullability') else None
                lines.append(f"    {param}: sign={sign}, nullability={null}")
        
        # Return value
        lines.append("  Returns:")
        # Extract return properties from the abstract state
        return_sign = None
        return_null = None
        if hasattr(self.return_state, 'sign_state') and '__return__' in self.return_state.sign_state:
            return_sign = self.return_state.sign_state['__return__']
        if hasattr(self.return_state, 'null_state') and '__return__' in self.return_state.null_state:
            return_null = self.return_state.null_state['__return__']
        lines.append(f"    sign={return_sign}, nullability={return_null}")
        
        # Properties
        props = []
        if self.is_pure():
            props.append("pure")
        if not self.always_returns:
            props.append("may not return")
        if self.may_throw:
            props.append("may throw")
        if props:
            lines.append(f"  Properties: {', '.join(props)}")
        
        # Side effects
        if self.modifies_globals:
            lines.append(f"  Modifies globals: {', '.join(sorted(self.modifies_globals))}")
        if self.modifies_parameters:
            lines.append(f"  Modifies parameters: {', '.join(sorted(self.modifies_parameters))}")
        
        return "\n".join(lines)


@dataclass 
class SummaryCache:
    """
    Cache for function summaries to avoid recomputation.
    """
    summaries: Dict[str, FunctionSummary] = field(default_factory=dict)
    
    def add(self, summary: FunctionSummary):
        """Add a summary to the cache."""
        self.summaries[summary.function_name] = summary
    
    def get(self, function_name: str) -> Optional[FunctionSummary]:
        """Get a summary from the cache."""
        return self.summaries.get(function_name)
    
    def has(self, function_name: str) -> bool:
        """Check if a summary exists."""
        return function_name in self.summaries
    
    def clear(self):
        """Clear all cached summaries."""
        self.summaries.clear()
    
    def __len__(self) -> int:
        return len(self.summaries)
    
    def __str__(self) -> str:
        """Display all cached summaries."""
        if not self.summaries:
            return "Summary cache is empty"
        
        lines = ["Summary Cache:"]
        for name in sorted(self.summaries.keys()):
            lines.append(f"\n{self.summaries[name]}")
        
        return "\n".join(lines)


class SummaryComputer:
    """
    Computes function summaries from analysis results.
    """
    
    @staticmethod
    def compute_summary(func_name: str, 
                       parameters: List[str],
                       entry_state: AbstractState,
                       exit_state: AbstractState) -> FunctionSummary:
        """
        Compute a function summary from entry and exit states.
        
        Args:
            func_name: Name of the function
            parameters: List of parameter names
            entry_state: Abstract state at function entry
            exit_state: Abstract state at function exit
            
        Returns:
            FunctionSummary capturing the function's behavior
        """
        summary = FunctionSummary(
            function_name=func_name,
            parameters=parameters
        )
        
        # Extract parameter states from entry
        for param in parameters:
            param_state = AbstractState()
            
            # Copy relevant states for this parameter
            if hasattr(entry_state, 'sign_state') and param in entry_state.sign_state:
                param_state.sign_state[param] = entry_state.sign_state[param]
            if hasattr(entry_state, 'null_state') and param in entry_state.null_state:
                param_state.null_state[param] = entry_state.null_state[param]
            if hasattr(entry_state, 'range_state') and param in entry_state.range_state:
                param_state.range_state[param] = entry_state.range_state[param]
            
            summary.parameter_states[param] = param_state
        
        # Extract return state from exit
        summary.return_state = AbstractState()
        
        # Look for __return__ variable in exit state
        if hasattr(exit_state, 'sign_state') and '__return__' in exit_state.sign_state:
            summary.return_state.sign_state['__return__'] = exit_state.sign_state['__return__']
        if hasattr(exit_state, 'null_state') and '__return__' in exit_state.null_state:
            summary.return_state.null_state['__return__'] = exit_state.null_state['__return__']
        if hasattr(exit_state, 'range_state') and '__return__' in exit_state.range_state:
            summary.return_state.range_state['__return__'] = exit_state.range_state['__return__']
        
        # TODO: Detect side effects, exceptions, etc. from the analysis
        
        return summary


# Context-sensitive extension for more precise analysis
@dataclass
class CallSiteContext:
    """
    Represents the context of a specific call site for context-sensitive analysis.
    """
    caller: str
    call_site_id: int
    argument_states: Dict[str, AbstractState]
    
    def __hash__(self):
        # Simple hash based on caller and call site
        return hash((self.caller, self.call_site_id))
    
    def __eq__(self, other):
        return (self.caller == other.caller and 
                self.call_site_id == other.call_site_id)


class ContextSensitiveSummaryCache:
    """
    Advanced cache that can store different summaries for different calling contexts.
    """
    
    def __init__(self):
        # Maps (function_name, context) -> summary
        self.context_summaries: Dict[tuple[str, CallSiteContext], FunctionSummary] = {}
        # Fallback context-insensitive summaries
        self.default_summaries: Dict[str, FunctionSummary] = {}
    
    def add_context_summary(self, func_name: str, context: CallSiteContext, summary: FunctionSummary):
        """Add a context-specific summary."""
        self.context_summaries[(func_name, context)] = summary
    
    def add_default_summary(self, func_name: str, summary: FunctionSummary):
        """Add a context-insensitive summary."""
        self.default_summaries[func_name] = summary
    
    def get_summary(self, func_name: str, context: Optional[CallSiteContext] = None) -> Optional[FunctionSummary]:
        """Get the most specific summary available."""
        # Try context-specific first
        if context and (func_name, context) in self.context_summaries:
            return self.context_summaries[(func_name, context)]
        # Fall back to default
        return self.default_summaries.get(func_name)