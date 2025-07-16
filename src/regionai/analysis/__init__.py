"""
Analysis module for RegionAI - contains CFG, fixpoint, and interprocedural analysis.
"""
from .cfg import ControlFlowGraph, BasicBlock, build_cfg
from .fixpoint import FixpointAnalyzer, analyze_with_fixpoint, WideningOperator
from .call_graph import CallGraph, build_call_graph, visualize_call_graph
from .function_summary import FunctionSummary, SummaryComputer
from .context import AnalysisContext
# Enhanced analysis components
from .pointer_analysis import (
    PointerAnalysis, PointsToLocation, HeapObject, 
    StackVariable, FieldLocation, GlobalVariable
)
from .heap_model import (
    HeapAnalyzer, HeapState, HeapValue,
    PrimitiveValue, ReferenceValue, NullValue
)
from .virtual_dispatch import (
    ClassHierarchyAnalyzer, VirtualMethodResolver,
    EnhancedCallAnalyzer, ClassInfo
)
# Import enhanced_interprocedural directly when needed to avoid circular imports
# from .enhanced_interprocedural import (
#     EnhancedInterproceduralAnalyzer,
#     analyze_with_enhanced_interprocedural,
#     EnhancedAnalysisState,
#     EnhancedAnalysisResult
# )
# Avoid circular import - import interprocedural directly when needed
# from .interprocedural import InterproceduralAnalyzer, analyze_interprocedural

__all__ = [
    'ControlFlowGraph',
    'BasicBlock', 
    'build_cfg',
    'FixpointAnalyzer',
    'analyze_with_fixpoint',
    'WideningOperator',
    'CallGraph',
    'build_call_graph',
    'visualize_call_graph',
    'FunctionSummary',
    'SummaryComputer',
    'AnalysisContext',
    # Enhanced analysis
    'PointerAnalysis',
    'PointsToLocation',
    'HeapObject',
    'StackVariable', 
    'FieldLocation',
    'GlobalVariable',
    'HeapAnalyzer',
    'HeapState',
    'HeapValue',
    'PrimitiveValue',
    'ReferenceValue',
    'NullValue',
    'ClassHierarchyAnalyzer',
    'VirtualMethodResolver',
    'EnhancedCallAnalyzer',
    'ClassInfo',
    # Enhanced interprocedural - import directly to avoid circular imports
    # 'EnhancedInterproceduralAnalyzer',
    # 'analyze_with_enhanced_interprocedural',
    # 'EnhancedAnalysisState',
    # 'EnhancedAnalysisResult',
    # 'InterproceduralAnalyzer',
    # 'analyze_interprocedural'
]