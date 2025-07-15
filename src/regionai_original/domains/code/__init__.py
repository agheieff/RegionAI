"""Code analysis domain - static analysis tools and abstract interpretation."""

# Import key functions and classes
from .cfg import build_cfg, ControlFlowGraph, BasicBlock
from .call_graph import build_call_graph, CallGraph
from .fixpoint import FixpointAnalyzer, analyze_with_fixpoint
from .alias_analysis import analyze_alias_assignment
from .range_domain import Range, range_add, range_widen, check_array_bounds

__all__ = [
    # CFG
    'build_cfg',
    'ControlFlowGraph', 
    'BasicBlock',
    
    # Call graph
    'build_call_graph',
    'CallGraph',
    
    # Fixpoint analysis
    'FixpointAnalyzer',
    'analyze_with_fixpoint',
    
    # Alias analysis
    'analyze_alias_assignment',
    
    # Range domain
    'Range',
    'range_add', 
    'range_widen',
    'check_array_bounds',
]