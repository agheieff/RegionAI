"""
Interprocedural analysis engine for whole-program analysis.
"""
import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import deque

from .call_graph import CallGraph, build_call_graph
from .function_summary import (
    FunctionSummary, SummaryComputer, 
    ContextSensitiveSummaryCache, ReturnSummary
)
from .summary import CallContext
from .fixpoint import FixpointAnalyzer, AnalysisState
from .cfg import build_cfg
from ..discovery.abstract_domains import (
    AbstractState, Sign, Nullability,
    reset_abstract_state
)


@dataclass
class AnalysisResult:
    """Result of interprocedural analysis."""
    function_summaries: Dict[str, FunctionSummary]
    errors: List[str]
    warnings: List[str]
    call_graph: CallGraph


class InterproceduralAnalyzer:
    """
    Performs whole-program interprocedural analysis.
    """
    
    def __init__(self):
        self.call_graph: Optional[CallGraph] = None
        self.function_asts: Dict[str, ast.FunctionDef] = {}
        self.summary_computer = SummaryComputer()
        self.context_cache = ContextSensitiveSummaryCache()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def analyze_program(self, tree: ast.AST) -> AnalysisResult:
        """
        Perform interprocedural analysis on entire program.
        """
        # Step 1: Build call graph
        self.call_graph = build_call_graph(tree)
        
        # Step 2: Collect all function definitions
        self._collect_functions(tree)
        
        # Step 3: Analyze functions in bottom-up order
        analysis_order = self.call_graph.topological_sort()
        
        # Keep track of analyzed contexts to avoid duplicates
        analyzed_contexts = set()
        
        # Initial analysis with default contexts
        for func_name in analysis_order:
            if func_name in self.function_asts:
                self._analyze_function(func_name)
                
                # Check if any analyzer added functions to worklist
                if hasattr(self, '_last_analyzer') and self._last_analyzer:
                    while self._last_analyzer.analysis_worklist:
                        next_func, next_state = self._last_analyzer.analysis_worklist.pop(0)
                        
                        # Create context to check if already analyzed
                        param_states = []
                        if next_func in self.function_asts:
                            for param in self.function_asts[next_func].args.args:
                                param_state = AbstractState()
                                param_name = param.arg
                                
                                if hasattr(next_state, 'sign_state') and param_name in next_state.sign_state:
                                    param_state.sign_state[param_name] = next_state.sign_state[param_name]
                                if hasattr(next_state, 'null_state') and param_name in next_state.null_state:
                                    param_state.null_state[param_name] = next_state.null_state[param_name]
                                
                                param_states.append(param_state)
                        
                        context = CallContext.from_call(next_func, param_states)
                        
                        if context not in analyzed_contexts:
                            analyzed_contexts.add(context)
                            self._analyze_function(next_func, next_state)
        
        # Step 4: Perform global error checking
        self._check_global_errors()
        
        return AnalysisResult(
            function_summaries=self.summary_computer.summaries,
            errors=self.errors,
            warnings=self.warnings,
            call_graph=self.call_graph
        )
    
    def _collect_functions(self, tree: ast.AST):
        """Collect all function definitions."""
        class FunctionCollector(ast.NodeVisitor):
            def __init__(self, container):
                self.container = container
                
            def visit_FunctionDef(self, node):
                self.container[node.name] = node
                self.generic_visit(node)
        
        collector = FunctionCollector(self.function_asts)
        collector.visit(tree)
    
    def _analyze_function(self, func_name: str, initial_param_state: Optional[AbstractState] = None):
        """Analyze a single function with interprocedural context."""
        func_ast = self.function_asts[func_name]
        
        # Build CFG for the function
        cfg = build_cfg(func_ast)
        
        # Set up initial state with parameter assumptions
        if initial_param_state is not None:
            # Use provided initial state for context-sensitive analysis
            initial_state = initial_param_state
        else:
            # Default to TOP state for entry points
            initial_state = AbstractState()
            
            # For entry points, assume parameters could have any value
            if func_name in self.call_graph.entry_points:
                for param in func_ast.args.args:
                    initial_state.set_sign(param.arg, Sign.TOP)
                    initial_state.set_nullability(param.arg, Nullability.NULLABLE)
        
        # Create enhanced analyzer that handles function calls
        analyzer = InterproceduralFixpointAnalyzer(
            cfg, self.call_graph, self.summary_computer, self.errors, self.warnings
        )
        
        # Copy existing summaries to the analyzer's cache
        if hasattr(self.summary_computer, 'summaries'):
            analyzer.summaries.update(self.summary_computer.summaries)
        
        # Run analysis
        block_states = analyzer.analyze(initial_state)
        
        # Extract exit state
        exit_state = None
        if cfg.exit_block and cfg.exit_block in block_states:
            exit_state = block_states[cfg.exit_block].abstract_state
        else:
            exit_state = AbstractState()
        
        # Compute function summary
        summary = self.summary_computer.compute_summary(
            func_ast, initial_state, exit_state
        )
        
        # Create context for this analysis
        # Extract parameter states from initial state
        param_states = []
        for param in func_ast.args.args:
            param_state = AbstractState()
            param_name = param.arg
            
            if hasattr(initial_state, 'sign_state') and param_name in initial_state.sign_state:
                param_state.sign_state[param_name] = initial_state.sign_state[param_name]
            if hasattr(initial_state, 'null_state') and param_name in initial_state.null_state:
                param_state.null_state[param_name] = initial_state.null_state[param_name]
            if hasattr(initial_state, 'range_state') and param_name in initial_state.range_state:
                param_state.range_state[param_name] = initial_state.range_state[param_name]
            
            param_states.append(param_state)
        
        context = CallContext.from_call(func_name, param_states)
        
        # Store the summary with context in the analyzer's cache
        analyzer.summaries[context] = summary
        
        # Also store in summary computer for compatibility
        if not hasattr(self.summary_computer, 'context_summaries'):
            self.summary_computer.context_summaries = {}
        self.summary_computer.context_summaries[context] = summary
        
        # Store analyzer reference for worklist processing
        self._last_analyzer = analyzer
    
    def _check_global_errors(self):
        """Check for errors that span multiple functions."""
        # Example: Check for null propagation across functions
        for call_site in self.call_graph.call_sites:
            self._check_call_site_safety(call_site)
    
    def _check_call_site_safety(self, call_site):
        """Check if a function call is safe."""
        caller_summary = self.summary_computer.summaries.get(call_site.caller)
        callee_summary = self.summary_computer.summaries.get(call_site.callee)
        
        if not caller_summary or not callee_summary:
            return
        
        # Check preconditions
        for precond in callee_summary.preconditions:
            # Simplified check - in practice would evaluate precondition
            if "!= 0" in precond:
                self.warnings.append(
                    f"Call from {call_site.caller} to {call_site.callee} "
                    f"at line {call_site.line_number}: ensure {precond}"
                )


class InterproceduralFixpointAnalyzer(FixpointAnalyzer):
    """
    Enhanced fixpoint analyzer that handles interprocedural calls.
    """
    
    def __init__(self, cfg, call_graph, summary_computer, errors, warnings):
        super().__init__(cfg)
        self.call_graph = call_graph
        self.summary_computer = summary_computer
        self.errors = errors
        self.warnings = warnings
        # Cache for context-sensitive function summaries
        self.summaries: Dict[CallContext, FunctionSummary] = {}
        # Track functions to analyze with specific contexts
        self.analysis_worklist: List[Tuple[str, AbstractState]] = []
    
    def _analyze_block(self, block, input_state):
        """Override to handle function calls."""
        current_state = input_state.copy()
        
        for stmt in block.statements:
            if isinstance(stmt, ast.Assign):
                # Check if RHS is a function call
                if isinstance(stmt.value, ast.Call):
                    self._handle_function_call(stmt, current_state)
                else:
                    # Regular assignment
                    self._analyze_assignment(stmt, current_state.abstract_state)
            
            # Check for null dereferences
            self._check_null_safety(stmt, current_state.abstract_state)
        
        return current_state
    
    def _handle_function_call(self, assign_stmt: ast.Assign, state: AnalysisState):
        """Handle interprocedural function call with context sensitivity."""
        call = assign_stmt.value
        
        # Try to identify called function
        if isinstance(call.func, ast.Name):
            callee_name = call.func.id
            
            # Extract argument states from the current context
            arg_states = []
            for arg in call.args:
                if isinstance(arg, ast.Name):
                    # Create a state capturing this argument's properties
                    arg_state = AbstractState()
                    var_name = arg.id
                    
                    # Copy relevant properties from current state
                    if hasattr(state.abstract_state, 'sign_state') and var_name in state.abstract_state.sign_state:
                        arg_state.sign_state[var_name] = state.abstract_state.sign_state[var_name]
                    if hasattr(state.abstract_state, 'null_state') and var_name in state.abstract_state.null_state:
                        arg_state.null_state[var_name] = state.abstract_state.null_state[var_name]
                    if hasattr(state.abstract_state, 'range_state') and var_name in state.abstract_state.range_state:
                        arg_state.range_state[var_name] = state.abstract_state.range_state[var_name]
                    
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
            
            # Create context for this specific call
            context = CallContext.from_call(callee_name, arg_states)
            
            # Check if we have a summary for this context
            if context in self.summaries:
                summary = self.summaries[context]
                self._apply_function_summary(assign_stmt, summary, state)
            elif hasattr(self.summary_computer, 'context_summaries') and context in self.summary_computer.context_summaries:
                # Check the summary computer's context cache
                summary = self.summary_computer.context_summaries[context]
                self._apply_function_summary(assign_stmt, summary, state)
            else:
                # No summary for this context yet
                # Add to worklist for analysis if we know about the function
                if hasattr(self.call_graph, 'functions') and callee_name in self.call_graph.functions:
                    # Create initial state for the callee based on arguments
                    callee_initial_state = self._create_callee_initial_state(callee_name, arg_states)
                    self.analysis_worklist.append((callee_name, callee_initial_state))
                
                # For now, assume conservative TOP state to continue analysis
                if assign_stmt.targets:
                    target = assign_stmt.targets[0]
                    if isinstance(target, ast.Name):
                        state.abstract_state.set_sign(target.id, Sign.TOP)
                        state.abstract_state.set_nullability(
                            target.id, Nullability.NULLABLE
                        )
    
    def _apply_function_summary(self, assign_stmt: ast.Assign, 
                               summary: FunctionSummary, 
                               state: AnalysisState):
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
            self.warnings.append(
                f"Function {summary.function_name} may throw exception"
            )
    
    def _check_null_safety(self, stmt: ast.AST, state: AbstractState):
        """Check for null pointer dereferences."""
        class NullCheckVisitor(ast.NodeVisitor):
            def __init__(self, analyzer, state):
                self.analyzer = analyzer
                self.state = state
                
            def visit_Attribute(self, node):
                # Check obj.attr for null safety
                if isinstance(node.value, ast.Name):
                    var_name = node.value.id
                    null_state = self.state.get_nullability(var_name)
                    
                    if null_state == Nullability.DEFINITELY_NULL:
                        self.analyzer.errors.append(
                            f"Null pointer exception: {var_name}.{node.attr}"
                        )
                    elif null_state == Nullability.NULLABLE:
                        self.analyzer.warnings.append(
                            f"Potential null pointer: {var_name}.{node.attr}"
                        )
                
                self.generic_visit(node)
        
        visitor = NullCheckVisitor(self, state)
        visitor.visit(stmt)
    
    def _create_callee_initial_state(self, func_name: str, arg_states: List[AbstractState]) -> AbstractState:
        """Create initial state for a function based on argument states."""
        initial_state = AbstractState()
        
        # Get function parameters
        if func_name in self.call_graph.functions:
            func_info = self.call_graph.functions[func_name]
            params = func_info.parameters
            
            # Map argument states to parameters
            for i, (param, arg_state) in enumerate(zip(params, arg_states)):
                # Transfer properties from argument to parameter
                for var, sign in getattr(arg_state, 'sign_state', {}).items():
                    initial_state.sign_state[param] = sign
                for var, null in getattr(arg_state, 'null_state', {}).items():
                    initial_state.null_state[param] = null
                for var, range_val in getattr(arg_state, 'range_state', {}).items():
                    initial_state.range_state[param] = range_val
        
        return initial_state


def analyze_interprocedural(tree: ast.AST) -> AnalysisResult:
    """
    Perform interprocedural analysis on a program.
    """
    analyzer = InterproceduralAnalyzer()
    return analyzer.analyze_program(tree)