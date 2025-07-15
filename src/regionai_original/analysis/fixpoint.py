"""
Fixpoint computation for abstract interpretation with widening.
REFACTORED VERSION: Uses AnalysisContext instead of global state.
"""
import ast
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field

from .cfg import ControlFlowGraph, BasicBlock, build_cfg
from .context import AnalysisContext
from ..core.abstract_domains import (
    AbstractState, Sign, Nullability,
    analyze_assignment
)


@dataclass 
class PathConstraint:
    """Represents a constraint on a path (e.g., x > 0)."""
    condition: ast.AST
    is_true: bool  # True if condition holds, False if negation holds
    
    def __str__(self):
        return f"{'¬' if not self.is_true else ''}{ast.dump(self.condition)}"
    
    def __hash__(self):
        return hash((ast.dump(self.condition), self.is_true))
    
    def __eq__(self, other):
        if not isinstance(other, PathConstraint):
            return False
        return ast.dump(self.condition) == ast.dump(other.condition) and self.is_true == other.is_true


@dataclass
class AnalysisState:
    """State at a program point during analysis."""
    abstract_state: AbstractState
    iteration_count: int = 0
    path_constraints: List[PathConstraint] = field(default_factory=list)
    points_to_map: Dict[str, Set['AbstractLocation']] = field(default_factory=dict)
    
    def copy(self) -> 'AnalysisState':
        """Create a deep copy of the state."""
        new_state = AnalysisState(
            abstract_state=AbstractState(),
            iteration_count=self.iteration_count,
            path_constraints=self.path_constraints.copy(),  # Copy the list of constraints
            points_to_map={}  # Will copy below
        )
        # Copy sign states
        new_state.abstract_state.sign_state = dict(self.abstract_state.sign_state)
        new_state.abstract_state.null_state = dict(self.abstract_state.null_state)
        if hasattr(self.abstract_state, 'range_state'):
            new_state.abstract_state.range_state = dict(self.abstract_state.range_state)
        
        # Copy points-to map (deep copy the sets)
        for var, pts in self.points_to_map.items():
            new_state.points_to_map[var] = pts.copy()
        
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
        
        # Join points-to maps (union of points-to sets)
        from .alias_analysis import merge_points_to_maps
        result.points_to_map = merge_points_to_maps(self.points_to_map, other.points_to_map)
                
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
    Now supports path-sensitive analysis with multiple states per block.
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
        self.block_states: Dict[int, AnalysisState] = {}  # Single state per block for non-path-sensitive
        self.worklist: Set[int] = set()
        
    def analyze(self, initial_state: AbstractState) -> Dict[int, AnalysisState]:
        """
        Perform fixpoint analysis starting from initial state.
        
        Args:
            initial_state: Initial abstract state
            
        Returns:
            Mapping from block IDs to their abstract states
        """
        # Initialize entry block with initial state
        if self.cfg.entry_block is not None:
            entry_state = AnalysisState(
                abstract_state=initial_state,
                iteration_count=0,
                path_constraints=[]
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
        
        Uses the main context for configuration and error reporting while
        passing the current abstract state explicitly to analysis functions.
        Now also tracks alias relationships.
        """
        # Start with copy of input state
        current_state = input_state.copy()
        
        # Update context's points-to map with current state
        self.context.points_to_map = current_state.points_to_map.copy()
        
        # Analyze each statement, including alias analysis
        from .alias_analysis import analyze_statement_for_aliases
        
        for stmt in block.statements:
            if isinstance(stmt, ast.Assign):
                # First do alias analysis
                analyze_statement_for_aliases(stmt, self.context)
                
                # Then regular abstract domain analysis
                analyze_assignment(stmt, self.context, current_state.abstract_state)
            
            elif isinstance(stmt, ast.Delete):
                # Handle deletions for alias analysis
                analyze_statement_for_aliases(stmt, self.context)
        
        # Copy updated points-to map back to state
        current_state.points_to_map = self.context.points_to_map.copy()
                    
        return current_state
    
    def _apply_path_constraint(self, state: AnalysisState, constraint: PathConstraint) -> AnalysisState:
        """
        Apply a path constraint to refine the abstract state.
        For now, this is a simplified version that handles basic comparisons.
        """
        result = state.copy()
        
        # Handle simple variable comparisons with constants
        if isinstance(constraint.condition, ast.Compare) and len(constraint.condition.ops) == 1:
            if isinstance(constraint.condition.left, ast.Name) and isinstance(constraint.condition.comparators[0], ast.Constant):
                var_name = constraint.condition.left.id
                const_val = constraint.condition.comparators[0].value
                op = constraint.condition.ops[0]
                
                # Apply constraint based on operator and whether it's true or negated
                if isinstance(const_val, int):
                    if isinstance(op, ast.Gt):  # x > const
                        if constraint.is_true and const_val >= 0:
                            result.abstract_state.set_sign(var_name, Sign.POSITIVE)
                    elif isinstance(op, ast.Lt):  # x < const  
                        if constraint.is_true and const_val <= 0:
                            result.abstract_state.set_sign(var_name, Sign.NEGATIVE)
                    elif isinstance(op, ast.Eq):  # x == const
                        if constraint.is_true:
                            if const_val > 0:
                                result.abstract_state.set_sign(var_name, Sign.POSITIVE)
                            elif const_val < 0:
                                result.abstract_state.set_sign(var_name, Sign.NEGATIVE)
                            else:
                                result.abstract_state.set_sign(var_name, Sign.ZERO)
        
        # Add the constraint to the path
        result.path_constraints.append(constraint)
        return result


class PathSensitiveFixpointAnalyzer(FixpointAnalyzer):
    """
    Path-sensitive version of the fixpoint analyzer.
    Tracks multiple states per program point with path constraints.
    """
    
    def analyze(self, initial_state: AbstractState) -> Dict[int, List[AnalysisState]]:
        """
        Perform path-sensitive fixpoint analysis.
        """
        # Initialize entry block
        if self.cfg.entry_block is not None:
            entry_state = AnalysisState(
                abstract_state=initial_state,
                iteration_count=0,
                path_constraints=[]
            )
            self.block_states[self.cfg.entry_block] = [entry_state]
            self.worklist.add(self.cfg.entry_block)
        
        iteration = 0
        max_iterations = self.context.config.max_fixpoint_iterations
        
        while self.worklist and iteration < max_iterations:
            iteration += 1
            block_id = self.worklist.pop()
            block = self.cfg.blocks[block_id]
            
            # Get all input states from predecessors
            input_states = self._compute_input_states(block)
            if not input_states:
                continue
            
            # Process each input state through the block
            new_states = []
            for input_state in input_states:
                input_state.iteration_count = iteration
                
                # If this is a conditional block, fork the state
                if block.branch_condition and block.successor_conditions:
                    # Analyze the block up to the branch
                    pre_branch_state = self._analyze_block(block, input_state)
                    
                    # Fork for each successor based on the condition
                    for succ_id, (condition, is_true) in block.successor_conditions.items():
                        constraint = PathConstraint(condition, is_true)
                        forked_state = self._apply_path_constraint(pre_branch_state, constraint)
                        
                        # Add forked state to successor's input
                        if succ_id not in self.block_states:
                            self.block_states[succ_id] = []
                        
                        # Check if this state is new or different
                        if not self._state_exists(self.block_states[succ_id], forked_state):
                            self.block_states[succ_id].append(forked_state)
                            self.worklist.add(succ_id)
                else:
                    # Normal block - just analyze and propagate
                    output_state = self._analyze_block(block, input_state)
                    new_states.append(output_state)
                    
                    # Propagate to successors
                    for succ_id in block.successors:
                        if succ_id not in self.block_states:
                            self.block_states[succ_id] = []
                        
                        if not self._state_exists(self.block_states[succ_id], output_state):
                            self.block_states[succ_id].append(output_state)
                            self.worklist.add(succ_id)
            
            # Update block states if not a conditional
            if not block.branch_condition:
                self.block_states[block_id] = new_states
        
        return self.block_states
    
    def _compute_input_states(self, block: BasicBlock) -> List[AnalysisState]:
        """Get all input states from predecessors and merge at join points."""
        if not block.predecessors:
            return self.block_states.get(block.id, [])
        
        input_states = []
        for pred_id in block.predecessors:
            if pred_id in self.block_states:
                input_states.extend(self.block_states[pred_id])
        
        # If this is a join point (multiple predecessors), merge states
        if len(block.predecessors) > 1 and len(input_states) > 0:
            # This is a control flow join point - apply merging
            input_states = self.merge_states_at_join(input_states)
        
        return input_states
    
    def _state_exists(self, states: List[AnalysisState], new_state: AnalysisState) -> bool:
        """Check if an equivalent state already exists in the list."""
        for state in states:
            if state.equals(new_state) and state.path_constraints == new_state.path_constraints:
                return True
        return False
    
    def merge_states_at_join(self, states: List[AnalysisState]) -> List[AnalysisState]:
        """
        Merge states at control flow join points.
        
        Strategy:
        1. Group states with identical abstract values
        2. Merge path constraints for identical states
        3. If too many distinct states remain, merge them all
        """
        if len(states) <= 1:
            return states
        
        # Get the maximum states per point from config
        MAX_STATES_PER_POINT = self.context.config.max_states_per_point if hasattr(self.context.config, 'max_states_per_point') else 5
        
        # First check if we need aggressive merging due to too many states
        if len(states) > MAX_STATES_PER_POINT:
            # Aggressive merge: combine all states into one
            final_merged = states[0].copy()
            final_merged.path_constraints = []  # Clear path constraints
            
            # Collect all variables
            all_vars = set()
            for state in states:
                all_vars.update(state.abstract_state.sign_state.keys())
                all_vars.update(state.abstract_state.null_state.keys())
            
            # For each variable, join the values from ALL states
            for var in all_vars:
                # Sign domain
                signs = set()
                for state in states:
                    if var in state.abstract_state.sign_state:
                        signs.add(state.abstract_state.sign_state[var])
                
                if len(signs) == 0:
                    pass  # Variable not present
                elif len(signs) == 1:
                    final_merged.abstract_state.set_sign(var, signs.pop())
                else:
                    # Multiple different values - set to TOP
                    final_merged.abstract_state.set_sign(var, Sign.TOP)
                
                # Nullability domain
                nulls = set()
                for state in states:
                    if var in state.abstract_state.null_state:
                        nulls.add(state.abstract_state.null_state[var])
                
                if len(nulls) == 0:
                    pass  # Variable not present
                elif len(nulls) == 1:
                    final_merged.abstract_state.set_nullability(var, nulls.pop())
                else:
                    # Multiple different values - set to NULLABLE (conservative)
                    final_merged.abstract_state.set_nullability(var, Nullability.NULLABLE)
            
            return [final_merged]
        
        # Otherwise, group states by their abstract values
        from collections import defaultdict
        state_groups = defaultdict(list)
        
        for state in states:
            # Create a hashable key from the abstract state
            # For now, just use sign states as the key
            state_key = tuple(sorted([
                (var, sign) for var, sign in state.abstract_state.sign_state.items()
            ]))
            state_groups[state_key].append(state)
        
        # Merge states within each group (same abstract values, different paths)
        merged_states = []
        for state_key, group in state_groups.items():
            if len(group) == 1:
                merged_states.append(group[0])
            else:
                # States have same abstract values but came from different paths
                # Keep one representative and merge path constraints
                representative = group[0].copy()
                # Collect all unique constraints
                all_constraints = []
                seen_constraints = set()
                for state in group:
                    for constraint in state.path_constraints:
                        constraint_key = (ast.dump(constraint.condition), constraint.is_true)
                        if constraint_key not in seen_constraints:
                            seen_constraints.add(constraint_key)
                            all_constraints.append(constraint)
                
                # If we have contradictory constraints, this path is infeasible
                # For now, just keep all constraints
                representative.path_constraints = all_constraints
                merged_states.append(representative)
        
        return merged_states


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