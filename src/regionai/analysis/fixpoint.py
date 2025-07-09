"""
Fixpoint computation for abstract interpretation with widening.
"""
import ast
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass
from copy import deepcopy

from .cfg import ControlFlowGraph, BasicBlock, build_cfg
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.regionai.discovery.abstract_domains import (
    AbstractState, Sign, Nullability,
    update_sign_state, reset_abstract_state
)


@dataclass
class AnalysisState:
    """State at a program point during analysis."""
    abstract_state: AbstractState
    iteration_count: int = 0
    
    def copy(self) -> 'AnalysisState':
        """Create a deep copy of the state."""
        new_state = AnalysisState(
            abstract_state=AbstractState(),
            iteration_count=self.iteration_count
        )
        # Copy sign states
        new_state.abstract_state.sign_state = dict(self.abstract_state.sign_state)
        new_state.abstract_state.nullability_state = dict(self.abstract_state.nullability_state)
        return new_state
    
    def equals(self, other: 'AnalysisState') -> bool:
        """Check if two states are equal."""
        if not isinstance(other, AnalysisState):
            return False
        
        # Check sign states
        if set(self.abstract_state.sign_state.keys()) != set(other.abstract_state.sign_state.keys()):
            return False
            
        for var in self.abstract_state.sign_state:
            if self.abstract_state.sign_state[var] != other.abstract_state.sign_state.get(var):
                return False
                
        return True
    
    def join(self, other: 'AnalysisState') -> 'AnalysisState':
        """Join two states (merge at control flow join points)."""
        result = self.copy()
        
        # Join sign states
        all_vars = set(self.abstract_state.sign_state.keys()) | set(other.abstract_state.sign_state.keys())
        
        for var in all_vars:
            self_sign = self.abstract_state.sign_state.get(var, Sign.TOP)
            other_sign = other.abstract_state.sign_state.get(var, Sign.TOP)
            
            if self_sign == other_sign:
                result.abstract_state.sign_state[var] = self_sign
            else:
                # Different signs -> TOP (conservative approximation)
                result.abstract_state.sign_state[var] = Sign.TOP
                
        result.iteration_count = max(self.iteration_count, other.iteration_count)
        return result


class WideningOperator:
    """Widening operators for different abstract domains."""
    
    @staticmethod
    def widen_sign(old: Sign, new: Sign, iteration: int) -> Sign:
        """
        Widening for sign domain.
        After threshold iterations, aggressively widen to TOP.
        """
        WIDENING_THRESHOLD = 3
        
        if old == new:
            return old
            
        if iteration >= WIDENING_THRESHOLD:
            # Aggressive widening to ensure termination
            return Sign.TOP
            
        # Before threshold, allow some refinement
        if old == Sign.TOP:
            return Sign.TOP
        
        # If signs keep changing, widen to TOP
        return Sign.TOP
    
    @staticmethod
    def widen_state(old_state: AnalysisState, new_state: AnalysisState) -> AnalysisState:
        """Apply widening to the entire state."""
        result = new_state.copy()
        
        # Widen each variable's sign
        for var in new_state.abstract_state.sign_state:
            if var in old_state.abstract_state.sign_state:
                old_sign = old_state.abstract_state.sign_state[var]
                new_sign = new_state.abstract_state.sign_state[var]
                widened_sign = WideningOperator.widen_sign(
                    old_sign, new_sign, new_state.iteration_count
                )
                result.abstract_state.sign_state[var] = widened_sign
                
        return result


class FixpointAnalyzer:
    """Performs fixpoint analysis on a control flow graph."""
    
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.block_states: Dict[int, AnalysisState] = {}
        self.max_iterations = 100  # Safety limit
        
    def analyze(self, initial_state: Optional[AbstractState] = None) -> Dict[int, AnalysisState]:
        """
        Perform fixpoint analysis on the CFG.
        Returns the final state at each block.
        """
        # Initialize states
        if initial_state is None:
            initial_state = AbstractState()
            
        # Set initial state at entry
        if self.cfg.entry_block is not None:
            self.block_states[self.cfg.entry_block] = AnalysisState(
                abstract_state=initial_state,
                iteration_count=0
            )
        
        # Worklist algorithm
        worklist = [self.cfg.entry_block] if self.cfg.entry_block else []
        iteration = 0
        
        while worklist and iteration < self.max_iterations:
            iteration += 1
            current_block_id = worklist.pop(0)
            current_block = self.cfg.blocks[current_block_id]
            
            # Compute input state (join of predecessors)
            input_state = self._compute_input_state(current_block)
            if input_state is None:
                continue
                
            # Analyze block
            output_state = self._analyze_block(current_block, input_state)
            
            # Apply widening at loop headers
            if current_block.is_loop_header and current_block_id in self.block_states:
                old_state = self.block_states[current_block_id]
                output_state = WideningOperator.widen_state(old_state, output_state)
                output_state.iteration_count = old_state.iteration_count + 1
            
            # Check if state changed
            if current_block_id not in self.block_states or \
               not self.block_states[current_block_id].equals(output_state):
                
                self.block_states[current_block_id] = output_state
                
                # Add successors to worklist
                for successor in current_block.successors:
                    if successor not in worklist:
                        worklist.append(successor)
        
        return self.block_states
    
    def _compute_input_state(self, block: BasicBlock) -> Optional[AnalysisState]:
        """Compute input state for a block by joining predecessor states."""
        if not block.predecessors:
            # Entry block or unreachable
            return self.block_states.get(block.id)
            
        predecessor_states = []
        for pred_id in block.predecessors:
            if pred_id in self.block_states:
                predecessor_states.append(self.block_states[pred_id])
                
        if not predecessor_states:
            return None
            
        # Join all predecessor states
        result = predecessor_states[0].copy()
        for state in predecessor_states[1:]:
            result = result.join(state)
            
        return result
    
    def _analyze_block(self, block: BasicBlock, input_state: AnalysisState) -> AnalysisState:
        """Analyze a basic block with the given input state."""
        # Start with copy of input state
        current_state = input_state.copy()
        
        # Analyze each statement
        for stmt in block.statements:
            if isinstance(stmt, ast.Assign):
                # Update abstract state based on assignment
                self._analyze_assignment(stmt, current_state.abstract_state)
                
        return current_state
    
    def _analyze_assignment(self, node: ast.Assign, state: AbstractState):
        """Analyze an assignment statement."""
        # For now, delegate to the existing update_sign_state
        # In the future, this should be enhanced to handle all domains
        global _abstract_state
        from src.regionai.discovery import abstract_domains
        
        # Temporarily set global state
        old_state = abstract_domains._abstract_state
        abstract_domains._abstract_state = state
        
        # Analyze
        update_sign_state(node, [])
        
        # Restore
        abstract_domains._abstract_state = old_state


def analyze_with_fixpoint(tree: ast.AST, initial_assumptions: Dict[str, Sign] = None) -> Dict[str, Any]:
    """
    Analyze a program using fixpoint iteration.
    
    Args:
        tree: The AST to analyze
        initial_assumptions: Initial sign assumptions for variables
        
    Returns:
        Final abstract state and analysis results
    """
    # Build CFG
    cfg = build_cfg(tree)
    
    # Set up initial state
    initial_state = AbstractState()
    if initial_assumptions:
        for var, sign in initial_assumptions.items():
            initial_state.set_sign(var, sign)
    
    # Run fixpoint analysis
    analyzer = FixpointAnalyzer(cfg)
    block_states = analyzer.analyze(initial_state)
    
    # Extract final state (at exit block)
    final_state = None
    if cfg.exit_block and cfg.exit_block in block_states:
        final_state = block_states[cfg.exit_block].abstract_state
    
    # Analyze loops
    loop_analysis = {}
    for block_id, block in cfg.blocks.items():
        if block.is_loop_header:
            loop_body = cfg.get_loop_body(block_id)
            loop_analysis[block_id] = {
                'header': block_id,
                'body': loop_body,
                'back_edges': block.back_edge_sources,
                'fixpoint_state': block_states.get(block_id)
            }
    
    return {
        'final_state': final_state,
        'block_states': block_states,
        'cfg': cfg,
        'loops': loop_analysis
    }