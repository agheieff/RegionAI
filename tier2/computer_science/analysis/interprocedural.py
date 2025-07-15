"""
Interprocedural analysis engine for whole-program analysis.
REFACTORED VERSION: Uses AnalysisContext instead of global state.
"""
import ast
from typing import Dict, List, Optional
from dataclasses import dataclass

from .call_graph import CallGraph, build_call_graph
from .interprocedural_components import CallContext
from .interprocedural_analyzer import InterproceduralFixpointAnalyzer
from .function_summary import (
    FunctionSummary, SummaryComputer, 
    ContextSensitiveSummaryCache
)
from .cfg import build_cfg
from .context import AnalysisContext
from tier1.region_algebra.abstract_domains import (
    AbstractState, Sign, Nullability
)
from tier2.computer_science.semantic.fingerprint import SemanticFingerprint, DocumentedFingerprint
from tier2.computer_science.semantic.fingerprinter import Fingerprinter
from tier2.computer_science.semantic.db import SemanticDB, SemanticEntry, FunctionName
# from tier1.pipeline.documentation_extractor import AdvancedDocumentationExtractor


@dataclass
class AnalysisResult:
    """Result of interprocedural analysis."""
    function_summaries: Dict[str, FunctionSummary]
    errors: List[str]
    warnings: List[str]
    call_graph: CallGraph
    semantic_fingerprints: Dict[CallContext, SemanticFingerprint] = None
    semantic_db: Optional[SemanticDB] = None
    documented_fingerprints: Dict[CallContext, DocumentedFingerprint] = None


class InterproceduralAnalyzer:
    """
    Performs whole-program interprocedural analysis.
    REFACTORED: Now uses AnalysisContext for all state management.
    """
    
    def __init__(self):
        self.call_graph: Optional[CallGraph] = None
        self.function_asts: Dict[str, ast.FunctionDef] = {}
        self.summary_computer = SummaryComputer()
        self.context_cache = ContextSensitiveSummaryCache()
        self.fingerprinter = Fingerprinter()
        self.semantic_fingerprints: Dict[CallContext, SemanticFingerprint] = {}
        self.semantic_db = SemanticDB()
        # self.documentation_extractor = AdvancedDocumentationExtractor()
        self.documented_fingerprints: Dict[CallContext, DocumentedFingerprint] = {}
        self.source_code: Optional[str] = None
        
    def analyze_program(self, tree: ast.AST, source_code: Optional[str] = None) -> AnalysisResult:
        """
        Perform interprocedural analysis on entire program.
        
        Args:
            tree: AST of the program to analyze
            source_code: Optional source code for enhanced documentation extraction
        """
        # Create analysis context for this analysis run
        context = AnalysisContext()
        
        # Store source code for documentation extraction
        self.source_code = source_code
        
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
                self._analyze_function(func_name, context)
                
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
                                if hasattr(next_state, 'range_state') and param_name in next_state.range_state:
                                    param_state.range_state[param_name] = next_state.range_state[param_name]
                                    
                                param_states.append(param_state)
                            
                            check_context = CallContext.from_call(next_func, param_states)
                            
                            # Only analyze if not already done with this context
                            if check_context not in analyzed_contexts:
                                analyzed_contexts.add(check_context)
                                self._analyze_function(next_func, context, next_state)
        
        # Step 4: Check for global errors
        self._check_global_errors(context)
        
        # Return results
        return AnalysisResult(
            function_summaries=self.summary_computer.summaries,
            errors=context.errors,
            warnings=context.warnings,
            call_graph=self.call_graph,
            semantic_fingerprints=self.semantic_fingerprints,
            semantic_db=self.semantic_db,
            documented_fingerprints=self.documented_fingerprints
        )
    
    def _collect_functions(self, tree: ast.AST):
        """Collect all function definitions."""
        class FunctionCollector(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                
            def visit_FunctionDef(self, node):
                self.analyzer.function_asts[node.name] = node
                self.generic_visit(node)
        
        FunctionCollector(self).visit(tree)
    
    def _analyze_function(self, func_name: str, context: AnalysisContext, 
                         initial_param_state: Optional[AbstractState] = None):
        """
        Analyze a single function with given context.
        
        Args:
            func_name: Name of function to analyze
            context: Analysis context containing all state
            initial_param_state: Optional initial state for parameters
        """
        func_ast = self.function_asts.get(func_name)
        if not func_ast:
            return
        
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
            cfg, self.call_graph, self.summary_computer, context,
            self.fingerprinter, self.semantic_fingerprints, self.function_asts
        )
        
        # Copy existing summaries to the analyzer's cache
        if hasattr(self.summary_computer, 'summaries'):
            analyzer.summaries.update(self.summary_computer.summaries)
        
        # Run analysis
        block_states = analyzer.analyze(initial_state)
        
        # Store reference to analyzer for worklist processing
        self._last_analyzer = analyzer
        
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
        
        # For function definition contexts, we don't have a specific call site
        call_context = CallContext.from_call(func_name, param_states, call_site_id=None)
        
        # Store the summary with context in the analyzer's cache
        analyzer.summaries[call_context] = summary
        
        # Also store in summary computer for compatibility
        if not hasattr(self.summary_computer, 'context_summaries'):
            self.summary_computer.context_summaries = {}
        self.summary_computer.context_summaries[call_context] = summary
        
        # Generate semantic fingerprint for this context
        fingerprint = self.fingerprinter.fingerprint(call_context, summary)
        self.semantic_fingerprints[call_context] = fingerprint
        
        # Extract documentation context
        func_ast = self.function_asts.get(func_name)
        if func_ast:
            nl_context = self.documentation_extractor.extract_from_function(
                func_ast, self.source_code
            )
            
            # Create documented fingerprint
            documented_fp = DocumentedFingerprint(
                fingerprint=fingerprint,
                nl_context=nl_context
            )
            self.documented_fingerprints[call_context] = documented_fp
        
        # Add to semantic database
        semantic_entry = SemanticEntry(
            function_name=FunctionName(func_name),
            context=call_context,
            fingerprint=fingerprint,
            documented_fingerprint=self.documented_fingerprints.get(call_context)
        )
        self.semantic_db.add(semantic_entry)
        
        # Store analyzer reference for worklist processing
        self._last_analyzer = analyzer
    
    def _check_global_errors(self, context: AnalysisContext):
        """Check for errors across function boundaries."""
        # Check call sites against function summaries
        for call_site in self.call_graph.get_all_call_sites():
            caller_summary = self.summary_computer.summaries.get(call_site.caller)
            callee_summary = self.summary_computer.summaries.get(call_site.callee)
            
            if not caller_summary or not callee_summary:
                continue
            
            # Check preconditions
            for precond in callee_summary.preconditions:
                # Simplified check - in practice would evaluate precondition
                if "!= 0" in precond:
                    context.add_warning(
                        f"Call from {call_site.caller} to {call_site.callee} "
                        f"at line {call_site.line_number}: ensure {precond}"
                    )


    


def analyze_interprocedural(tree: ast.AST, source_code: Optional[str] = None) -> AnalysisResult:
    """
    Perform interprocedural analysis on a program.
    
    Args:
        tree: AST of the program to analyze
        source_code: Optional source code for enhanced documentation extraction
        
    Returns:
        AnalysisResult containing analysis results
    """
    analyzer = InterproceduralAnalyzer()
    return analyzer.analyze_program(tree, source_code)