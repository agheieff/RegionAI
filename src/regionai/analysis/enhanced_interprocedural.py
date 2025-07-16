"""
Enhanced interprocedural analysis with pointer analysis, heap modeling,
and virtual method resolution.

This module integrates all the advanced analysis components to provide
precise whole-program analysis.
"""
import ast
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass, field

from .interprocedural import InterproceduralAnalyzer, AnalysisResult
from .pointer_analysis import PointerAnalysis, StackVariable
from .heap_model import HeapAnalyzer, HeapState
from .virtual_dispatch import (
    ClassHierarchyAnalyzer, VirtualMethodResolver, EnhancedCallAnalyzer
)
from .context import AnalysisContext
from .fixpoint import AnalysisState
from .cfg import build_cfg
from ..core.abstract_domains import AbstractState
from ..config import RegionAIConfig, DEFAULT_CONFIG


@dataclass
class EnhancedAnalysisState(AnalysisState):
    """
    Extended analysis state that includes heap state.
    
    This state tracks both local abstract state and heap state
    for precise modeling of program behavior.
    """
    heap_state: HeapState = field(default_factory=HeapState)
    
    def copy(self) -> 'EnhancedAnalysisState':
        """Create a deep copy."""
        new_state = EnhancedAnalysisState(
            abstract_state=self.abstract_state.copy()
        )
        new_state.heap_state = self.heap_state.copy()
        return new_state
    
    def merge(self, other: 'EnhancedAnalysisState') -> 'EnhancedAnalysisState':
        """Merge with another state."""
        merged = EnhancedAnalysisState(
            abstract_state=self.abstract_state.merge(other.abstract_state)
        )
        merged.heap_state = self.heap_state.merge(other.heap_state)
        return merged


@dataclass
class EnhancedAnalysisResult(AnalysisResult):
    """Extended analysis result with additional information."""
    pointer_analysis: Optional[PointerAnalysis] = None
    class_hierarchy: Optional[ClassHierarchyAnalyzer] = None
    heap_states: Dict[Any, HeapState] = field(default_factory=dict)
    virtual_call_targets: Dict[ast.Call, Set[str]] = field(default_factory=dict)


class EnhancedInterproceduralAnalyzer(InterproceduralAnalyzer):
    """
    Enhanced interprocedural analyzer with advanced features.
    
    This analyzer integrates:
    - Pointer analysis for precise aliasing information
    - Heap modeling for tracking object mutations
    - Virtual method resolution for polymorphic calls
    - Enhanced context sensitivity
    """
    
    def __init__(self, config: Optional[RegionAIConfig] = None):
        """Initialize enhanced analyzer."""
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        
        # Additional analysis components
        self.pointer_analysis = PointerAnalysis(self.config)
        self.class_hierarchy = ClassHierarchyAnalyzer()
        self.virtual_resolver: Optional[VirtualMethodResolver] = None
        self.heap_analyzer: Optional[HeapAnalyzer] = None
        self.call_analyzer: Optional[EnhancedCallAnalyzer] = None
        
        # Enhanced state tracking
        self.heap_states: Dict[Any, HeapState] = {}
        self.virtual_call_targets: Dict[ast.Call, Set[str]] = {}
        
    def analyze_program(self, tree: ast.AST, source_code: Optional[str] = None) -> EnhancedAnalysisResult:
        """
        Perform enhanced interprocedural analysis.
        
        Args:
            tree: AST of the program
            source_code: Optional source code
            
        Returns:
            Enhanced analysis result
        """
        # Phase 1: Build class hierarchy
        self.class_hierarchy.analyze_module(tree)
        
        # Phase 2: Run pointer analysis
        self.pointer_analysis.analyze_module(tree)
        
        # Phase 3: Initialize advanced components
        self.virtual_resolver = VirtualMethodResolver(
            self.class_hierarchy, self.pointer_analysis
        )
        self.heap_analyzer = HeapAnalyzer(self.pointer_analysis)
        self.call_analyzer = EnhancedCallAnalyzer(self.virtual_resolver)
        
        # Phase 4: Run base interprocedural analysis
        # This will call our overridden methods
        base_result = super().analyze_program(tree, source_code)
        
        # Return enhanced result
        return EnhancedAnalysisResult(
            function_summaries=base_result.function_summaries,
            errors=base_result.errors,
            warnings=base_result.warnings,
            call_graph=base_result.call_graph,
            semantic_fingerprints=base_result.semantic_fingerprints,
            semantic_db=base_result.semantic_db,
            documented_fingerprints=base_result.documented_fingerprints,
            pointer_analysis=self.pointer_analysis,
            class_hierarchy=self.class_hierarchy,
            heap_states=self.heap_states,
            virtual_call_targets=self.virtual_call_targets
        )
    
    def _analyze_function(self, func_name: str, context: AnalysisContext,
                         initial_param_state: Optional[AbstractState] = None):
        """
        Override to use enhanced analysis state.
        
        This method extends the base implementation to track
        heap state throughout the analysis.
        """
        func_ast = self.function_asts.get(func_name)
        if not func_ast:
            return
        
        # Build CFG
        cfg = build_cfg(func_ast)
        
        # Create enhanced initial state
        initial_abstract = initial_param_state or AbstractState()
        initial_heap = HeapState()
        
        # Initialize parameters in heap if they're objects
        for param in func_ast.args.args:
            param_name = param.arg
            # Check if parameter points to heap objects
            pointed_objs = self.pointer_analysis.get_pointed_objects(
                param_name, func_name
            )
            for obj in pointed_objs:
                # Mark as initialized parameter
                initial_heap.initialized_objects.add(obj)
        
        # Run analysis with enhanced state
        self._run_enhanced_analysis(
            func_name, cfg, initial_abstract, initial_heap, context
        )
    
    def _run_enhanced_analysis(self, func_name: str, cfg: Any,
                             initial_abstract: AbstractState,
                             initial_heap: HeapState,
                             context: AnalysisContext):
        """Run analysis with heap tracking."""
        # This is a simplified version - full implementation would
        # integrate with the fixpoint analyzer
        
        # Track heap state at each program point
        entry_state = EnhancedAnalysisState(
            abstract_state=initial_abstract,
            heap_state=initial_heap
        )
        
        # Store for later use
        self.heap_states[f"{func_name}_entry"] = initial_heap
        
        # Run base analysis (this will use our enhanced call handling)
        super()._analyze_function(func_name, context, initial_abstract)
    
    def _handle_enhanced_call(self, call_expr: ast.Call,
                            state: AnalysisState,
                            current_function: Optional[str] = None) -> Set[str]:
        """
        Enhanced call handling with virtual dispatch.
        
        Args:
            call_expr: Call expression
            state: Current analysis state
            current_function: Current function
            
        Returns:
            Set of possible target functions
        """
        # Use enhanced call analyzer
        targets = self.call_analyzer.analyze_call(call_expr, current_function)
        
        # Store for result
        self.virtual_call_targets[call_expr] = targets
        
        return targets
    
    def check_enhanced_null_safety(self, expr: ast.AST,
                                 context: AnalysisContext,
                                 heap_state: HeapState,
                                 current_function: Optional[str] = None) -> bool:
        """
        Enhanced null safety checking using heap information.
        
        Args:
            expr: Expression to check
            context: Analysis context
            heap_state: Current heap state
            current_function: Current function
            
        Returns:
            True if safe, False if may be null
        """
        if isinstance(expr, ast.Attribute):
            # Use heap analyzer for precise checking
            return self.heap_analyzer.check_null_field_access(
                expr, context.abstract_state, heap_state, current_function
            )
        
        # Fall back to base checking
        return self._check_null_safety(expr, context)
    
    def analyze_mutations(self, stmt: ast.AST,
                         abstract_state: AbstractState,
                         heap_state: HeapState,
                         current_function: Optional[str] = None) -> HeapState:
        """
        Analyze statement for heap mutations.
        
        Args:
            stmt: Statement to analyze
            abstract_state: Current abstract state
            heap_state: Current heap state
            current_function: Current function
            
        Returns:
            Updated heap state
        """
        return self.heap_analyzer.analyze_statement_with_heap(
            stmt, abstract_state, heap_state, current_function
        )
    
    def get_aliasing_info(self, var1: str, var2: str,
                         function: Optional[str] = None) -> bool:
        """
        Check if two variables may alias.
        
        Args:
            var1: First variable
            var2: Second variable
            function: Function context
            
        Returns:
            True if variables may alias
        """
        loc1 = StackVariable(var1, function)
        loc2 = StackVariable(var2, function)
        return self.pointer_analysis.may_alias(loc1, loc2)
    
    def get_escape_info(self, var_name: str,
                       function: Optional[str] = None) -> bool:
        """
        Check if a variable's objects may escape the function.
        
        Args:
            var_name: Variable name
            function: Function name
            
        Returns:
            True if objects may escape
        """
        # Simple escape analysis: check if pointed objects
        # are reachable from globals or return values
        pointed_objs = self.pointer_analysis.get_pointed_objects(
            var_name, function
        )
        
        # Check if any pointed object is reachable from globals
        for obj in pointed_objs:
            # This is simplified - full implementation would
            # track data flow to returns and global stores
            pass
        
        return False  # Conservative for now


def analyze_with_enhanced_interprocedural(tree: ast.AST,
                                        source_code: Optional[str] = None,
                                        config: Optional[RegionAIConfig] = None) -> EnhancedAnalysisResult:
    """
    Perform enhanced interprocedural analysis.
    
    Args:
        tree: AST of the program
        source_code: Optional source code
        config: Analysis configuration
        
    Returns:
        Enhanced analysis result with all information
    """
    analyzer = EnhancedInterproceduralAnalyzer(config)
    return analyzer.analyze_program(tree, source_code)