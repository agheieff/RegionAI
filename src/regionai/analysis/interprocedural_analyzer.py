"""
Interprocedural fixpoint analyzer for whole-program analysis.

This module contains the InterproceduralFixpointAnalyzer class that extends
the basic fixpoint analysis with interprocedural capabilities.
"""
import ast
from typing import Dict, List, Tuple

from .fixpoint import FixpointAnalyzer, AnalysisState
from .context import AnalysisContext
from .function_summary import FunctionSummary
from .interprocedural_components import (
    CallContext,
    FunctionSummaryApplicator,
    CalleeStateBuilder,
    ArgumentStateExtractor,
    WorklistManager
)
from ..core.abstract_domains import Sign, Nullability, analyze_assignment


class InterproceduralFixpointAnalyzer(FixpointAnalyzer):
    """
    Enhanced fixpoint analyzer that handles interprocedural calls.
    REFACTORED: Now uses AnalysisContext and delegates to specialized helper components.
    """
    
    def __init__(self, cfg, call_graph, summary_computer, context: AnalysisContext,
                 fingerprinter=None, semantic_fingerprints=None, function_asts=None):
        super().__init__(cfg, context)
        self.call_graph = call_graph
        self.summary_computer = summary_computer
        self.context = context
        # Cache for context-sensitive function summaries
        self.summaries: Dict[CallContext, FunctionSummary] = {}
        # Track functions to analyze with specific contexts
        self.analysis_worklist: List[Tuple[str, AnalysisState]] = []
        # Optional fingerprinting support
        self.fingerprinter = fingerprinter
        self.semantic_fingerprints = semantic_fingerprints or {}
        # Store reference to semantic fingerprints dict
        if semantic_fingerprints is not None:
            self.semantic_fingerprints = semantic_fingerprints
        # Store function ASTs for parameter resolution
        self.function_asts = function_asts or {}
        
        # Initialize helper components
        self._summary_applicator = FunctionSummaryApplicator(context)
        self._callee_builder = CalleeStateBuilder(self.function_asts)
        self._argument_extractor = ArgumentStateExtractor()
        self._worklist_manager = WorklistManager()
    
    def _analyze_block(self, block, input_state):
        """Override to handle function calls."""
        current_state = input_state.copy()
        
        for stmt in block.statements:
            # Skip function definitions and other non-executable statements
            if isinstance(stmt, (ast.FunctionDef, ast.ClassDef)):
                continue
            
            if isinstance(stmt, ast.Assign):
                # Check if RHS is a function call
                if isinstance(stmt.value, ast.Call):
                    self._handle_function_call(stmt, current_state)
                else:
                    # Regular assignment - use context-aware function
                    # Create a temporary context with current state for this assignment
                    temp_context = AnalysisContext()
                    temp_context.abstract_state = current_state.abstract_state
                    analyze_assignment(stmt, temp_context)
                    # Update current state from the temporary context
                    current_state.abstract_state = temp_context.abstract_state
            
            # Check for null dereferences with current state
            temp_context = AnalysisContext()
            temp_context.abstract_state = current_state.abstract_state
            self._check_null_safety(stmt, temp_context)
        
        return current_state
    
    def _handle_function_call(self, assign_stmt: ast.Assign, state: AnalysisState):
        """Handle interprocedural function call with context sensitivity."""
        call = assign_stmt.value
        
        # Try to identify called function
        if isinstance(call.func, ast.Name):
            callee_name = call.func.id
            
            # Delegate argument extraction to helper component
            arg_states = self._argument_extractor.extract_argument_states(
                call, state.abstract_state
            )
            
            # Create context for this specific call with call site information
            call_site_id = call.lineno if hasattr(call, 'lineno') else None
            context = CallContext.from_call(callee_name, arg_states, call_site_id)
            
            # Store this context-specific summary in the summary computer
            if not hasattr(self.summary_computer, 'context_summaries'):
                self.summary_computer.context_summaries = {}
            
            # Check if we have a summary for this context
            if context in self.summaries:
                summary = self.summaries[context]
                self._summary_applicator.apply_summary(assign_stmt, summary, state)
                # Also store in summary computer for test visibility
                self.summary_computer.context_summaries[context] = summary
                # Generate fingerprint for this call-site-specific context
                if self.fingerprinter and context not in self.semantic_fingerprints:
                    fingerprint = self.fingerprinter.fingerprint(context, summary)
                    self.semantic_fingerprints[context] = fingerprint
            elif context in self.summary_computer.context_summaries:
                # Check the summary computer's context cache
                summary = self.summary_computer.context_summaries[context]
                self._summary_applicator.apply_summary(assign_stmt, summary, state)
                # Generate fingerprint if needed
                if self.fingerprinter and context not in self.semantic_fingerprints:
                    fingerprint = self.fingerprinter.fingerprint(context, summary)
                    self.semantic_fingerprints[context] = fingerprint
            elif callee_name in self.summary_computer.summaries:
                # Check if we have a context-insensitive summary
                summary = self.summary_computer.summaries[callee_name]
                self._summary_applicator.apply_summary(assign_stmt, summary, state)
                # Store this as a context-specific summary
                self.summary_computer.context_summaries[context] = summary
                # Generate fingerprint for this call-site-specific context
                if self.fingerprinter and context not in self.semantic_fingerprints:
                    fingerprint = self.fingerprinter.fingerprint(context, summary)
                    self.semantic_fingerprints[context] = fingerprint
            else:
                # No summary for this context yet
                # Add to worklist for analysis if we know about the function
                if hasattr(self.call_graph, 'functions') and callee_name in self.call_graph.functions:
                    # Delegate initial state creation to helper component
                    callee_initial_state = self._callee_builder.create_callee_initial_state(
                        callee_name, arg_states
                    )
                    self._worklist_manager.add_function(callee_name, callee_initial_state)
                    self.analysis_worklist.append((callee_name, callee_initial_state))
                
                # For now, assume conservative TOP state to continue analysis
                if assign_stmt.targets:
                    target = assign_stmt.targets[0]
                    if isinstance(target, ast.Name):
                        state.abstract_state.set_sign(target.id, Sign.TOP)
                        state.abstract_state.set_nullability(
                            target.id, Nullability.NULLABLE
                        )
    
    
    def _check_null_safety(self, stmt: ast.AST, context: AnalysisContext):
        """Check for null pointer dereferences using context."""
        from ..discovery.abstract_domains import check_null_dereference
        
        # Use the refactored function that accepts context
        errors = check_null_dereference(stmt, context)
        for error in errors:
            if "exception" in error:
                self.context.add_error(error)  # Add to main context, not temp
            else:
                self.context.add_warning(error)  # Add to main context, not temp