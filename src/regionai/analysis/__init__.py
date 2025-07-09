"""
Analysis module for RegionAI - contains CFG and fixpoint analysis.
"""
from .cfg import ControlFlowGraph, BasicBlock, build_cfg
from .fixpoint import FixpointAnalyzer, analyze_with_fixpoint, WideningOperator

__all__ = [
    'ControlFlowGraph',
    'BasicBlock', 
    'build_cfg',
    'FixpointAnalyzer',
    'analyze_with_fixpoint',
    'WideningOperator'
]