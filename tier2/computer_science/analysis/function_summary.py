"""
Function summaries for interprocedural analysis.
"""
import ast
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from tier1.region_algebra.abstract_domains import Sign, Nullability, AbstractState
from tier2.computer_science.range_domain import Range, TOP


@dataclass
class ParameterSummary:
    """Summary of a function parameter's properties."""
    name: str
    sign: Optional[Sign] = None
    nullability: Optional[Nullability] = None
    range: Optional[Range] = None
    
    def is_compatible(self, arg_sign: Sign = None, arg_null: Nullability = None, arg_range: Range = None) -> bool:
        """Check if an argument is compatible with this parameter."""
        if self.sign and arg_sign and self.sign != arg_sign:
            return False
        if self.nullability and arg_null and self.nullability != arg_null:
            return False
        if self.range and arg_range and not self._ranges_compatible(self.range, arg_range):
            return False
        return True
    
    def _ranges_compatible(self, param_range: Range, arg_range: Range) -> bool:
        """Check if argument range is within parameter range."""
        return (arg_range.min >= param_range.min and 
                arg_range.max <= param_range.max)


@dataclass
class ReturnSummary:
    """Summary of what a function returns."""
    sign: Sign = Sign.TOP
    nullability: Nullability = Nullability.NULLABLE
    range: Range = field(default_factory=lambda: TOP)
    
    # Special flags
    always_returns: bool = True  # False if function might not return
    may_throw: bool = False  # True if function might throw exception


@dataclass
class SideEffectSummary:
    """Summary of a function's side effects."""
    modifies_globals: Set[str] = field(default_factory=set)
    modifies_parameters: Set[str] = field(default_factory=set)  # For mutable params
    performs_io: bool = False
    calls_external: bool = False


@dataclass
class FunctionSummary:
    """
    Complete summary of a function's behavior.
    """
    function_name: str
    parameters: List[ParameterSummary]
    returns: ReturnSummary
    side_effects: SideEffectSummary
    
    # Preconditions that must hold at call site
    preconditions: List[str] = field(default_factory=list)
    
    # Postconditions that hold after call
    postconditions: List[str] = field(default_factory=list)
    
    # Additional semantic information
    returns_parameter: Optional[str] = None  # Name of parameter if function returns it unchanged
    
    def __hash__(self):
        return hash(self.function_name)


class SummaryComputer:
    """Compute function summaries from analysis results."""
    
    def __init__(self):
        self.summaries: Dict[str, FunctionSummary] = {}
        
    def compute_summary(self, func_def: ast.FunctionDef, 
                       entry_state: AbstractState,
                       exit_state: AbstractState) -> FunctionSummary:
        """
        Compute a function summary from its definition and analysis states.
        """
        # Extract parameter summaries
        param_summaries = []
        for param in func_def.args.args:
            param_name = param.arg
            param_summary = ParameterSummary(
                name=param_name,
                sign=entry_state.get_sign(param_name),
                nullability=entry_state.get_nullability(param_name),
                # Range would come from entry_state if we tracked it
            )
            param_summaries.append(param_summary)
        
        # Analyze return statements to compute return summary
        return_summary, returned_param = self._analyze_returns(func_def, exit_state)
        
        # Detect side effects
        side_effects = self._analyze_side_effects(func_def)
        
        # Create summary
        summary = FunctionSummary(
            function_name=func_def.name,
            parameters=param_summaries,
            returns=return_summary,
            side_effects=side_effects,
            returns_parameter=returned_param
        )
        
        # Add specific preconditions/postconditions based on analysis
        self._add_conditions(summary, func_def, entry_state, exit_state)
        
        self.summaries[func_def.name] = summary
        return summary
    
    def _analyze_returns(self, func_def: ast.FunctionDef, exit_state: AbstractState) -> Tuple[ReturnSummary, Optional[str]]:
        """Analyze all return statements in a function."""
        return_visitor = ReturnAnalyzer(exit_state, func_def)
        return_visitor.visit(func_def)
        
        # Check if function consistently returns a parameter
        returned_param = None
        if return_visitor.returned_parameters:
            # If all returns are the same parameter, it's an identity function
            if all(p == return_visitor.returned_parameters[0] for p in return_visitor.returned_parameters):
                returned_param = return_visitor.returned_parameters[0]
        
        return return_visitor.get_summary(), returned_param
    
    def _analyze_side_effects(self, func_def: ast.FunctionDef) -> SideEffectSummary:
        """Detect side effects in a function."""
        effects = SideEffectSummary()
        
        # Simple analysis - could be enhanced
        class SideEffectVisitor(ast.NodeVisitor):
            def visit_Global(self, node):
                for name in node.names:
                    effects.modifies_globals.add(name)
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['print', 'input', 'open']:
                        effects.performs_io = True
                    elif node.func.id not in self.known_functions:
                        effects.calls_external = True
        
        visitor = SideEffectVisitor()
        visitor.known_functions = set(self.summaries.keys())
        visitor.visit(func_def)
        
        return effects
    
    def _add_conditions(self, summary: FunctionSummary, func_def: ast.FunctionDef,
                       entry_state: AbstractState, exit_state: AbstractState):
        """Add preconditions and postconditions to summary."""
        # Example: If function has division, add non-zero precondition
        class DivisionChecker(ast.NodeVisitor):
            def __init__(self):
                self.has_division = False
                self.divisors = []
                
            def visit_BinOp(self, node):
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    self.has_division = True
                    if isinstance(node.right, ast.Name):
                        self.divisors.append(node.right.id)
                self.generic_visit(node)
        
        checker = DivisionChecker()
        checker.visit(func_def)
        
        if checker.has_division:
            for divisor in checker.divisors:
                if divisor in [p.name for p in summary.parameters]:
                    summary.preconditions.append(f"{divisor} != 0")


class ReturnAnalyzer(ast.NodeVisitor):
    """Analyze return statements to compute return summary."""
    
    def __init__(self, exit_state: AbstractState, func_def: ast.FunctionDef = None):
        self.exit_state = exit_state
        self.func_def = func_def
        self.return_signs = []
        self.return_nullabilities = []
        self.has_return = False
        self.all_paths_return = True  # Simplified
        self.returned_parameters = []  # Track which parameters are returned
        
    def visit_Return(self, node):
        self.has_return = True
        
        if node.value:
            # Analyze return value
            if isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, (int, float)):
                    if node.value.value > 0:
                        self.return_signs.append(Sign.POSITIVE)
                    elif node.value.value < 0:
                        self.return_signs.append(Sign.NEGATIVE)
                    else:
                        self.return_signs.append(Sign.ZERO)
                
                if node.value.value is None:
                    self.return_nullabilities.append(Nullability.DEFINITELY_NULL)
                else:
                    self.return_nullabilities.append(Nullability.NOT_NULL)
                    
            elif isinstance(node.value, ast.Name):
                # Look up in exit state
                sign = self.exit_state.get_sign(node.value.id)
                if sign:
                    self.return_signs.append(sign)
                    
                null = self.exit_state.get_nullability(node.value.id)
                if null:
                    self.return_nullabilities.append(null)
                
                # Check if this is a parameter being returned
                if self.func_def:
                    param_names = [arg.arg for arg in self.func_def.args.args]
                    if node.value.id in param_names:
                        self.returned_parameters.append(node.value.id)
        
        self.generic_visit(node)
    
    def get_summary(self) -> ReturnSummary:
        """Compute return summary from collected data."""
        summary = ReturnSummary()
        
        # Combine signs
        if self.return_signs:
            result_sign = self.return_signs[0]
            for sign in self.return_signs[1:]:
                if sign != result_sign:
                    result_sign = Sign.TOP
                    break
            summary.sign = result_sign
        
        # Combine nullabilities
        if self.return_nullabilities:
            result_null = self.return_nullabilities[0]
            for null in self.return_nullabilities[1:]:
                if null != result_null:
                    result_null = Nullability.NULLABLE
                    break
            summary.nullability = result_null
        
        summary.always_returns = self.has_return and self.all_paths_return
        
        return summary


# Context-sensitive summaries
@dataclass
class ContextKey:
    """Key for context-sensitive function summaries."""
    function_name: str
    parameter_signs: Tuple[Sign, ...]
    parameter_nullabilities: Tuple[Nullability, ...]
    
    def __hash__(self):
        return hash((self.function_name, self.parameter_signs, self.parameter_nullabilities))


class ContextSensitiveSummaryCache:
    """Cache for context-sensitive function summaries."""
    
    def __init__(self):
        self.cache: Dict[ContextKey, FunctionSummary] = {}
        
    def get_summary(self, func_name: str, arg_signs: List[Sign], 
                   arg_nulls: List[Nullability]) -> Optional[FunctionSummary]:
        """Get cached summary for specific context."""
        key = ContextKey(
            function_name=func_name,
            parameter_signs=tuple(arg_signs),
            parameter_nullabilities=tuple(arg_nulls)
        )
        return self.cache.get(key)
    
    def add_summary(self, func_name: str, arg_signs: List[Sign],
                   arg_nulls: List[Nullability], summary: FunctionSummary):
        """Cache summary for specific context."""
        key = ContextKey(
            function_name=func_name,
            parameter_signs=tuple(arg_signs),
            parameter_nullabilities=tuple(arg_nulls)
        )
        self.cache[key] = summary