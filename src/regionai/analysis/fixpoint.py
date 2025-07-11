"""
Fixpoint computation for abstract interpretation with widening.
REFACTORED VERSION: Uses AnalysisContext instead of global state.
"""
import ast
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass
from copy import deepcopy

from .cfg import ControlFlowGraph, BasicBlock, build_cfg
from .context import AnalysisContext
from ..discovery.abstract_domains import (
    AbstractState, Sign, Nullability,
    analyze_assignment
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
        new_state.abstract_state.null_state = dict(self.abstract_state.null_state)
        if hasattr(self.abstract_state, 'range_state'):
            new_state.abstract_state.range_state = dict(self.abstract_state.range_state)
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
    def widen_sign(old: Sign, new: Sign, iteration: int, threshold: int = 3) -> Sign:
        """
        Widening for sign domain.
        After threshold iterations, aggressively widen to TOP.
        
        Args:
            old: Previous sign value
            new: New sign value
            iteration: Current iteration number
            threshold: Widening threshold (from config)
        """
        if old == new:
            return old
            
        if iteration >= threshold:
            # Aggressive widening to ensure termination
            return Sign.TOP
            
        # Before threshold, allow some refinement
        if old == Sign.TOP:
            return Sign.TOP
        
        # If signs keep changing, widen to TOP
        return Sign.TOP
    
    @staticmethod
    def widen_state(old_state: AnalysisState, new_state: AnalysisState, 
                   threshold: int = 3) -> AnalysisState:
        """
        Apply widening to abstract state.
        
        Args:
            old_state: Previous state
            new_state: New state
            threshold: Widening threshold from config
        """
        widened = old_state.copy()
        widened.iteration_count = new_state.iteration_count
        
        # Widen sign states
        for var in new_state.abstract_state.sign_state:
            if var in old_state.abstract_state.sign_state:
                old_sign = old_state.abstract_state.sign_state[var]
                new_sign = new_state.abstract_state.sign_state[var]
                widened.abstract_state.sign_state[var] = WideningOperator.widen_sign(
                    old_sign, new_sign, new_state.iteration_count, threshold
                )
            else:
                widened.abstract_state.sign_state[var] = new_state.abstract_state.sign_state[var]
        
        return widened


class FixpointAnalyzer:
    """
    Performs fixpoint computation on a CFG with abstract interpretation.
    REFACTORED: Now accepts AnalysisContext for state management.
    """
    
    def __init__(self, cfg: ControlFlowGraph, context: AnalysisContext = None):
        """
        Initialize the fixpoint analyzer.
        
        Args:
            cfg: Control flow graph to analyze
            context: Analysis context for state management
        """
        self.cfg = cfg
        self.context = context if context is not None else AnalysisContext()
        self.block_states: Dict[int, AnalysisState] = {}
        self.worklist: Set[int] = set()
        
    def analyze(self, initial_state: AbstractState) -> Dict[int, AnalysisState]:
        """
        Perform fixpoint analysis starting from initial state.
        
        Args:
            initial_state: Initial abstract state
            
        Returns:
            Mapping from block IDs to their final abstract states
        """
        # Initialize entry block with initial state
        if self.cfg.entry_block is not None:
            entry_state = AnalysisState(
                abstract_state=initial_state,
                iteration_count=0
            )
            self.block_states[self.cfg.entry_block] = entry_state
            self.worklist.add(self.cfg.entry_block)
        
        # Fixpoint iteration
        iteration = 0
        max_iterations = self.context.config.max_fixpoint_iterations
        
        while self.worklist and iteration < max_iterations:
            iteration += 1
            
            # Pick a block from worklist
            block_id = self.worklist.pop()
            block = self.cfg.blocks[block_id]
            
            # Get input state by joining predecessor states
            input_state = self._compute_join_state(block)
            if input_state is None:
                continue
                
            # Analyze the block
            input_state.iteration_count = iteration
            new_state = self._analyze_block(block, input_state)
            
            # Check if state changed (with widening for loops)
            if block_id in self.block_states:
                old_state = self.block_states[block_id]
                
                # Apply widening if this is a loop header
                if block.is_loop_header and iteration > 1:
                    new_state = WideningOperator.widen_state(
                        old_state, new_state, self.context.config.widening_threshold
                    )
                
                # Check for convergence
                if not old_state.equals(new_state):
                    self.block_states[block_id] = new_state
                    # Add successors to worklist
                    self.worklist.update(block.successors)
            else:
                # First time visiting this block
                self.block_states[block_id] = new_state
                self.worklist.update(block.successors)
        
        # Check if we hit the iteration limit
        if self.worklist and iteration >= max_iterations:
            self.context.add_warning(
                f"Fixpoint analysis reached maximum iteration limit ({max_iterations}). "
                "Analysis may be incomplete."
            )
        
        return self.block_states
    
    def _compute_join_state(self, block: BasicBlock) -> Optional[AnalysisState]:
        """Compute input state by joining predecessor states."""
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
        """
        Analyze a basic block with the given input state.
        
        Creates a temporary context for this block's analysis to avoid
        modifying the shared context.
        """
        # Start with copy of input state
        current_state = input_state.copy()
        
        # Create a temporary context for this block's analysis
        from .context import AnalysisContext
        block_context = AnalysisContext()
        
        # Copy configuration and other shared data from the main context
        block_context.config = self.context.config
        block_context.errors = self.context.errors  # Share error list
        block_context.warnings = self.context.warnings  # Share warning list
        
        # Set the block's current state
        block_context.abstract_state = current_state.abstract_state
        
        # Analyze each statement with the temporary context
        for stmt in block.statements:
            if isinstance(stmt, ast.Assign):
                # Use the context-aware analyze_assignment
                analyze_assignment(stmt, block_context)
                    
        # Copy the modified state back to the result
        current_state.abstract_state = block_context.abstract_state
                
        return current_state


def analyze_with_fixpoint(tree: ast.AST, initial_assumptions: Dict[str, Sign] = None, 
                         context: AnalysisContext = None) -> Dict[str, Any]:
    """
    Analyze a program using fixpoint iteration.
    
    Args:
        tree: The AST to analyze
        initial_assumptions: Initial sign assumptions for variables
        context: Analysis context to use (creates new one if not provided)
        
    Returns:
        Final abstract state and analysis results
    """
    # Use provided context or create a new one
    if context is None:
        context = AnalysisContext()
    
    # Build CFG
    cfg = build_cfg(tree)
    
    # Set up initial state
    initial_state = AbstractState()
    if initial_assumptions:
        for var, sign in initial_assumptions.items():
            initial_state.set_sign(var, sign)
    
    # Run fixpoint analysis
    analyzer = FixpointAnalyzer(cfg, context)
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
        'loops': loop_analysis,
        'context': context  # Include context with any errors/warnings
    }