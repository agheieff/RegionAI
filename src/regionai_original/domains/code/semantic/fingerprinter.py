"""
Fingerprinter service for analyzing function summaries and generating semantic fingerprints.

This service contains the logic to inspect a FunctionSummary and identify
high-level behavioral patterns, creating a SemanticFingerprint that captures
the conceptual essence of what a function does.
"""
from typing import Optional, List

from ....analysis.interprocedural_components import CallContext
from ....analysis.function_summary import FunctionSummary
from .fingerprint import SemanticFingerprint, Behavior
from ....core.abstract_domains import (
    Sign, Nullability
)
from ..range_domain import Range


class Fingerprinter:
    """Analyzes a FunctionSummary to create a SemanticFingerprint."""
    
    def fingerprint(self, context: CallContext, summary: FunctionSummary) -> SemanticFingerprint:
        """
        Generate a semantic fingerprint for a function given its context and summary.
        
        Args:
            context: The calling context containing parameter states
            summary: The function summary with analysis results
            
        Returns:
            SemanticFingerprint capturing the function's behavioral patterns
        """
        fingerprint = SemanticFingerprint()
        
        # Apply all behavioral detectors
        if self._is_identity(context, summary):
            fingerprint.add_behavior(Behavior.IDENTITY)
            
        if self._is_constant_return(summary):
            fingerprint.add_behavior(Behavior.CONSTANT_RETURN)
            
        if self._is_nullable_return(summary):
            fingerprint.add_behavior(Behavior.NULLABLE_RETURN)
            
        if self._is_null_safe(summary):
            fingerprint.add_behavior(Behavior.NULL_SAFE)
            
        if self._is_null_propagating(context, summary):
            fingerprint.add_behavior(Behavior.NULL_PROPAGATING)
            
        if self._preserves_sign(context, summary):
            fingerprint.add_behavior(Behavior.PRESERVES_SIGN)
            
        if self._is_pure(summary):
            fingerprint.add_behavior(Behavior.PURE)
            
        if self._may_not_return(summary):
            fingerprint.add_behavior(Behavior.MAY_NOT_RETURN)
            
        if self._may_throw(summary):
            fingerprint.add_behavior(Behavior.MAY_THROW)
            
        if self._modifies_parameters(summary):
            fingerprint.add_behavior(Behavior.MODIFIES_PARAMETERS)
            
        if self._modifies_globals(summary):
            fingerprint.add_behavior(Behavior.MODIFIES_GLOBALS)
            
        if self._performs_io(summary):
            fingerprint.add_behavior(Behavior.PERFORMS_IO)
            
        if self._is_range_preserving(context, summary):
            fingerprint.add_behavior(Behavior.RANGE_PRESERVING)
            
        if self._is_validator(summary):
            fingerprint.add_behavior(Behavior.VALIDATOR)
            
        # Add more detector calls as we implement them
        
        return fingerprint
    
    def _is_identity(self, context: CallContext, summary: FunctionSummary) -> bool:
        """
        Check if the function returns one of its arguments unchanged.
        
        This is a fundamental pattern where f(x) = x or f(x, y) = x/y.
        """
        if not summary.parameters:
            return False
            
        # For now, use a simple heuristic:
        # If a function has parameters and is pure with no complex operations,
        # it might be identity. This is a placeholder for more sophisticated
        # AST-based analysis that would track data flow.
        
        # Identity functions can be pure or impure
        # The key is that they return a parameter unchanged
            
        # Additional checks could include:
        # - AST analysis to see if return statement directly returns a parameter
        # - Data flow analysis to track if parameter flows unchanged to return
        # - Checking if return properties match at least one parameter's properties
        
        # For simple cases, if the function is pure and has one parameter,
        # and doesn't perform complex operations, it might be identity
        # This is a simplified heuristic that would need enhancement
        
        # Check if summary indicates a parameter is returned unchanged
        if hasattr(summary, 'returns_parameter') and summary.returns_parameter:
            return True
            
        # Fallback: check if the function name suggests identity behavior
        if summary.function_name in ['identity', 'id', 'passthrough']:
            return True
            
        return False
    
    def _is_constant_return(self, summary: FunctionSummary) -> bool:
        """
        Check if the function always returns the same constant value.
        
        This includes functions that return literals or computed constants.
        """
        # Check if return range has min == max (single value)
        return_range = self._get_return_range(summary)
        if return_range and return_range.min == return_range.max and return_range.min != float('-inf'):
            return True
            
        # Check if return sign is ZERO (constant 0) AND not nullable
        # If it can return None, it's not a constant function
        return_sign = self._get_return_sign(summary)
        return_null = self._get_return_nullability(summary)
        if return_sign == Sign.ZERO and return_null == Nullability.NOT_NULL:
            return True
            
        # Check if function has no parameters and always returns
        # This suggests it might be a constant function
        if (not summary.parameters and 
            summary.returns.always_returns and 
            not summary.returns.may_throw):
            # Additional heuristic for parameterless functions
            return True
            
        return False
    
    def _is_nullable_return(self, summary: FunctionSummary) -> bool:
        """Check if the function may return None."""
        return_null = self._get_return_nullability(summary)
        return return_null in [Nullability.NULLABLE, Nullability.DEFINITELY_NULL]
    
    def _is_null_safe(self, summary: FunctionSummary) -> bool:
        """Check if the function never returns null."""
        return_null = self._get_return_nullability(summary)
        return return_null == Nullability.NOT_NULL
    
    def _is_null_propagating(self, context: CallContext, summary: FunctionSummary) -> bool:
        """
        Check if the function returns null when any input is null.
        
        Common pattern in functions that can't handle null inputs.
        """
        # This would require more sophisticated analysis of the function body
        # For now, simple heuristic: if any precondition mentions null checks
        for precond in summary.preconditions:
            if "!= None" in precond or "is not None" in precond:
                return True
        return False
    
    def _preserves_sign(self, context: CallContext, summary: FunctionSummary) -> bool:
        """
        Check if output sign matches input sign.
        
        Examples: abs() doesn't preserve sign, but double(x) = 2*x does.
        """
        return_sign = self._get_return_sign(summary)
        if not return_sign or return_sign == Sign.TOP:
            return False
            
        # Check if any parameter has matching sign
        for i, param in enumerate(summary.parameters):
            if i < len(context.parameter_states):
                param_state_tuple = context.parameter_states[i]
                if len(param_state_tuple) > 0:
                    sign_items = param_state_tuple[0]
                    for var, sign in sign_items:
                        if sign == return_sign:
                            return True
        
        return False
    
    def _is_pure(self, summary: FunctionSummary) -> bool:
        """Check if function has no side effects."""
        return (not summary.side_effects.modifies_globals and
                not summary.side_effects.modifies_parameters and
                not summary.side_effects.performs_io and
                not summary.side_effects.calls_external and
                summary.returns.always_returns and
                not summary.returns.may_throw)
    
    def _may_not_return(self, summary: FunctionSummary) -> bool:
        """Check if function might not return (infinite loop, etc)."""
        return not summary.returns.always_returns
    
    def _may_throw(self, summary: FunctionSummary) -> bool:
        """Check if function might throw an exception."""
        return summary.returns.may_throw
    
    def _modifies_parameters(self, summary: FunctionSummary) -> bool:
        """Check if function modifies its parameters."""
        return bool(summary.side_effects.modifies_parameters)
    
    def _modifies_globals(self, summary: FunctionSummary) -> bool:
        """Check if function modifies global state."""
        return bool(summary.side_effects.modifies_globals)
    
    def _performs_io(self, summary: FunctionSummary) -> bool:
        """Check if function performs I/O operations."""
        return summary.side_effects.performs_io
    
    def _is_range_preserving(self, context: CallContext, summary: FunctionSummary) -> bool:
        """
        Check if output range is subset of input range.
        
        Example: clamp(x, 0, 100) is range preserving if x is in [0, 100].
        """
        return_range = self._get_return_range(summary)
        if not return_range:
            return False
            
        # Would need to compare with input ranges from context
        # Placeholder for now
        return False
    
    def _is_validator(self, summary: FunctionSummary) -> bool:
        """
        Check if function is a validator (returns boolean).
        
        Validators typically have specific range characteristics.
        """
        return_range = self._get_return_range(summary)
        if return_range:
            # Boolean values are typically 0 or 1
            return (return_range.min == 0 and return_range.max == 1)
        return False
    
    # Helper methods to extract properties from summaries
    
    def _get_return_sign(self, summary: FunctionSummary) -> Optional[Sign]:
        """Extract sign of return value from summary."""
        return summary.returns.sign
    
    def _get_return_nullability(self, summary: FunctionSummary) -> Optional[Nullability]:
        """Extract nullability of return value from summary."""
        return summary.returns.nullability
    
    def _get_return_range(self, summary: FunctionSummary) -> Optional[Range]:
        """Extract range of return value from summary."""
        if hasattr(summary.returns, 'range'):
            return summary.returns.range
        return None


class BehaviorPattern:
    """
    Represents a pattern of behaviors that commonly occur together.
    
    This can be used to identify higher-level semantic concepts from
    combinations of primitive behaviors.
    """
    
    def __init__(self, name: str, required_behaviors: List[Behavior], 
                 forbidden_behaviors: Optional[List[Behavior]] = None):
        self.name = name
        self.required_behaviors = set(required_behaviors)
        self.forbidden_behaviors = set(forbidden_behaviors or [])
    
    def matches(self, fingerprint: SemanticFingerprint) -> bool:
        """Check if a fingerprint matches this pattern."""
        # All required behaviors must be present
        if not self.required_behaviors.issubset(fingerprint.behaviors):
            return False
            
        # No forbidden behaviors should be present
        if self.forbidden_behaviors.intersection(fingerprint.behaviors):
            return False
            
        return True


# Common behavior patterns
COMMON_PATTERNS = [
    BehaviorPattern(
        "Pure Function",
        required_behaviors=[Behavior.PURE],
        forbidden_behaviors=[Behavior.MODIFIES_GLOBALS, Behavior.MODIFIES_PARAMETERS]
    ),
    BehaviorPattern(
        "Safe Function", 
        required_behaviors=[],
        forbidden_behaviors=[Behavior.MAY_NOT_RETURN, Behavior.MAY_THROW]
    ),
    BehaviorPattern(
        "Deterministic Function",
        required_behaviors=[Behavior.PURE],
        forbidden_behaviors=[Behavior.GENERATOR]
    ),
    BehaviorPattern(
        "Null-Safe Identity",
        required_behaviors=[Behavior.IDENTITY, Behavior.NULL_SAFE],
        forbidden_behaviors=[]
    ),
    BehaviorPattern(
        "Constant Function",
        required_behaviors=[Behavior.CONSTANT_RETURN, Behavior.PURE],
        forbidden_behaviors=[]
    ),
]