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
        
        for func_name in analysis_order:
            if func_name in self.function_asts:
                self._analyze_function(func_name)
        
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
    
    def _analyze_function(self, func_name: str):
        """Analyze a single function with interprocedural context."""
        func_ast = self.function_asts[func_name]
        
        # Build CFG for the function
        cfg = build_cfg(func_ast)
        
        # Set up initial state with parameter assumptions
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
        """Handle interprocedural function call."""
        call = assign_stmt.value
        
        # Try to identify called function
        if isinstance(call.func, ast.Name):
            callee_name = call.func.id
            
            # Get function summary if available
            summary = self.summary_computer.summaries.get(callee_name)
            
            if summary:
                # Apply summary to update state
                self._apply_function_summary(assign_stmt, summary, state)
            else:
                # Conservative: function might return anything
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


def analyze_interprocedural(tree: ast.AST) -> AnalysisResult:
    """
    Perform interprocedural analysis on a program.
    """
    analyzer = InterproceduralAnalyzer()
    return analyzer.analyze_program(tree)