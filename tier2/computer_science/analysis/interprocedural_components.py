"""
Helper components for interprocedural analysis.
Extracted from InterproceduralFixpointAnalyzer for better modularity.
"""
import ast
from typing import Dict, List, Optional, Tuple
from .function_summary import FunctionSummary
from .summary import CallContext
from .fixpoint import AnalysisState
from .context import AnalysisContext
from tier1.region_algebra.abstract_domains import AbstractState, Sign, Nullability


class FunctionSummaryApplicator:
    """Applies function summaries to update abstract states."""
    
    def __init__(self, context: AnalysisContext):
        self.context = context
    
    def apply_summary(self, assign_stmt: ast.Assign, 
                     summary: FunctionSummary, 
                     state: AnalysisState) -> None:
        """Apply function summary to update abstract state."""
        if not assign_stmt.targets:
            return
            
        target = assign_stmt.targets[0]
        if not isinstance(target, ast.Name):
            return
        
        # Update state based on return summary
        target_var = target.id
        state.abstract_state.set_sign(target_var, summary.returns.sign)
        state.abstract_state.set_nullability(
            target_var, summary.returns.nullability
        )
        
        # Check for potential errors
        if summary.returns.may_throw:
            self.context.add_warning(
                f"Function {summary.function_name} may throw exception"
            )


class CalleeStateBuilder:
    """Builds initial states for callee functions based on arguments."""
    
    def __init__(self, function_asts: Dict[str, ast.FunctionDef]):
        self.function_asts = function_asts
    
    def create_callee_initial_state(self, callee_name: str, 
                                   arg_states: List[AbstractState]) -> AbstractState:
        """
        Create initial state for callee based on arguments.
        
        Maps argument states to the function's parameter names using the
        actual function signature.
        """
        combined = AbstractState()
        
        # Get the function definition to know parameter names
        func_ast = self.function_asts.get(callee_name)
        if not func_ast or not hasattr(func_ast, 'args'):
            # Fallback to simple numbered parameters if we can't find the function
            for i, arg_state in enumerate(arg_states):
                self._merge_argument_state(combined, arg_state, f'param_{i}')
            return combined
        
        # Get parameter names from function signature
        func_args = func_ast.args
        param_names = [arg.arg for arg in func_args.args]
        
        # Map positional arguments to parameters
        for i, arg_state in enumerate(arg_states):
            if i < len(param_names):
                param_name = param_names[i]
                self._merge_argument_state(combined, arg_state, param_name)
            else:
                # Extra arguments (could be *args in the future)
                self._merge_argument_state(combined, arg_state, f'extra_arg_{i}')
        
        # Handle parameters with no corresponding arguments (use default or TOP)
        for i in range(len(arg_states), len(param_names)):
            param_name = param_names[i]
            # Check if parameter has a default value
            if i - len(arg_states) < len(func_args.defaults):
                default = func_args.defaults[i - len(arg_states)]
                if isinstance(default, ast.Constant):
                    # Set state based on default value
                    combined.set_nullability(param_name, 
                                           Nullability.DEFINITELY_NULL if default.value is None 
                                           else Nullability.NOT_NULL)
                    if isinstance(default.value, (int, float)):
                        if default.value > 0:
                            combined.set_sign(param_name, Sign.POSITIVE)
                        elif default.value < 0:
                            combined.set_sign(param_name, Sign.NEGATIVE)
                        else:
                            combined.set_sign(param_name, Sign.ZERO)
                else:
                    # Non-constant default, assume TOP
                    combined.set_sign(param_name, Sign.TOP)
                    combined.set_nullability(param_name, Nullability.NULLABLE)
            else:
                # No default, parameter is required but missing
                # This would be a runtime error, but for analysis assume TOP
                combined.set_sign(param_name, Sign.TOP)
                combined.set_nullability(param_name, Nullability.NULLABLE)
        
        return combined
    
    def _merge_argument_state(self, target: AbstractState, arg_state: AbstractState, param_name: str):
        """Helper to merge argument state into target state for a specific parameter."""
        # Handle sign state
        for var, sign in arg_state.sign_state.items():
            if var == '__const__' or len(arg_state.sign_state) == 1:
                # This is a constant or single-value state
                target.sign_state[param_name] = sign
                break
        
        # Handle nullability state
        for var, null in arg_state.null_state.items():
            if var == '__const__' or len(arg_state.null_state) == 1:
                # This is a constant or single-value state
                target.null_state[param_name] = null
                break
        
        # Handle range state if present
        if hasattr(arg_state, 'range_state'):
            for var, range_val in arg_state.range_state.items():
                if var == '__const__' or len(arg_state.range_state) == 1:
                    target.range_state[param_name] = range_val
                    break


class ArgumentStateExtractor:
    """Extracts argument states from function calls."""
    
    @staticmethod
    def extract_argument_states(call: ast.Call, current_state: AbstractState) -> List[AbstractState]:
        """Extract abstract states for function call arguments."""
        arg_states = []
        
        for arg in call.args:
            if isinstance(arg, ast.Name):
                # Create a state capturing this argument's properties
                arg_state = AbstractState()
                var_name = arg.id
                
                # Copy relevant properties from current state
                if hasattr(current_state, 'sign_state') and var_name in current_state.sign_state:
                    arg_state.sign_state[var_name] = current_state.sign_state[var_name]
                if hasattr(current_state, 'null_state') and var_name in current_state.null_state:
                    arg_state.null_state[var_name] = current_state.null_state[var_name]
                if hasattr(current_state, 'range_state') and var_name in current_state.range_state:
                    arg_state.range_state[var_name] = current_state.range_state[var_name]
                
                arg_states.append(arg_state)
            elif isinstance(arg, ast.Constant):
                # Handle constant arguments
                const_state = AbstractState()
                if arg.value is None:
                    const_state.null_state['__const__'] = Nullability.DEFINITELY_NULL
                else:
                    const_state.null_state['__const__'] = Nullability.NOT_NULL
                    if isinstance(arg.value, int):
                        if arg.value > 0:
                            const_state.sign_state['__const__'] = Sign.POSITIVE
                        elif arg.value < 0:
                            const_state.sign_state['__const__'] = Sign.NEGATIVE
                        else:
                            const_state.sign_state['__const__'] = Sign.ZERO
                arg_states.append(const_state)
            else:
                # Unknown argument type - use TOP state
                arg_states.append(AbstractState())
        
        return arg_states


class WorklistManager:
    """Manages the worklist of functions to analyze with specific contexts."""
    
    def __init__(self):
        self.worklist: List[Tuple[str, AbstractState]] = []
        self.analyzed_contexts: set = set()
    
    def add_function(self, func_name: str, initial_state: AbstractState) -> None:
        """Add a function to the worklist if not already analyzed."""
        # Could add context checking here to avoid duplicates
        self.worklist.append((func_name, initial_state))
    
    def pop_next(self) -> Optional[Tuple[str, AbstractState]]:
        """Get the next function to analyze."""
        if self.worklist:
            return self.worklist.pop(0)
        return None
    
    def is_empty(self) -> bool:
        """Check if worklist is empty."""
        return len(self.worklist) == 0
    
    def mark_analyzed(self, context: CallContext) -> None:
        """Mark a context as analyzed."""
        self.analyzed_contexts.add(context)
    
    def was_analyzed(self, context: CallContext) -> bool:
        """Check if a context was already analyzed."""
        return context in self.analyzed_contexts