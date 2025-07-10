"""
Analysis module for RegionAI - contains CFG, fixpoint, and interprocedural analysis.
"""
from .cfg import ControlFlowGraph, BasicBlock, build_cfg
from .fixpoint import FixpointAnalyzer, analyze_with_fixpoint, WideningOperator
from .call_graph import CallGraph, build_call_graph, visualize_call_graph
from .function_summary import FunctionSummary, SummaryComputer
from .interprocedural import InterproceduralAnalyzer, analyze_interprocedural

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
    'InterproceduralAnalyzer',
    'analyze_interprocedural'
]