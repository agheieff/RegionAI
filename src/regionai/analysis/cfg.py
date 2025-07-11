"""
Control Flow Graph (CFG) construction and analysis for abstract interpretation.
"""
import ast
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


class BlockType(Enum):
    """Types of basic blocks in the CFG."""
    ENTRY = auto()
    EXIT = auto()
    NORMAL = auto()
    LOOP_HEADER = auto()
    CONDITIONAL = auto()


@dataclass
class BasicBlock:
    """A basic block in the control flow graph."""
    id: int
    type: BlockType
    statements: List[ast.AST]
    successors: Set[int] = field(default_factory=set)
    predecessors: Set[int] = field(default_factory=set)
    
    # Loop-specific information
    is_loop_header: bool = False
    back_edge_sources: Set[int] = field(default_factory=set)  # Blocks that jump back to this header
    loop_depth: int = 0
    
    # Path-sensitive information
    branch_condition: Optional[ast.AST] = None  # The test condition for conditional blocks
    successor_conditions: Dict[int, Tuple[ast.AST, bool]] = field(default_factory=dict)  # Maps successor block ID to (condition, is_true_branch)
    
    def add_successor(self, block_id: int):
        """Add a successor block."""
        self.successors.add(block_id)
    
    def add_predecessor(self, block_id: int):
        """Add a predecessor block."""
        self.predecessors.add(block_id)
    
    def has_back_edge(self) -> bool:
        """Check if this block has any back edges (making it a loop header)."""
        return len(self.back_edge_sources) > 0


class ControlFlowGraph:
    """Control flow graph for a function."""
    
    def __init__(self):
        self.blocks: Dict[int, BasicBlock] = {}
        self.entry_block: Optional[int] = None
        self.exit_block: Optional[int] = None
        self._next_block_id = 0
        
    def create_block(self, block_type: BlockType = BlockType.NORMAL) -> int:
        """Create a new basic block and return its ID."""
        block_id = self._next_block_id
        self._next_block_id += 1
        
        block = BasicBlock(id=block_id, type=block_type, statements=[])
        self.blocks[block_id] = block
        
        if block_type == BlockType.ENTRY:
            self.entry_block = block_id
        elif block_type == BlockType.EXIT:
            self.exit_block = block_id
            
        return block_id
    
    def add_edge(self, from_block: int, to_block: int):
        """Add an edge between two blocks."""
        if from_block in self.blocks and to_block in self.blocks:
            self.blocks[from_block].add_successor(to_block)
            self.blocks[to_block].add_predecessor(from_block)
    
    def identify_loops(self):
        """Identify loop headers and back edges using dominance analysis."""
        # First, compute dominators
        dominators = self._compute_dominators()
        
        # Find back edges: edges where target dominates source
        for block_id, block in self.blocks.items():
            for successor in block.successors:
                if successor in dominators.get(block_id, set()):
                    # This is a back edge: block_id -> successor
                    self.blocks[successor].is_loop_header = True
                    self.blocks[successor].type = BlockType.LOOP_HEADER
                    self.blocks[successor].back_edge_sources.add(block_id)
    
    def _compute_dominators(self) -> Dict[int, Set[int]]:
        """Compute dominators for each block."""
        if self.entry_block is None:
            return {}
            
        # Initialize: entry dominates only itself, others dominated by all
        dominators = {}
        all_blocks = set(self.blocks.keys())
        
        dominators[self.entry_block] = {self.entry_block}
        for block_id in self.blocks:
            if block_id != self.entry_block:
                dominators[block_id] = all_blocks.copy()
        
        # Iterate until fixpoint
        changed = True
        while changed:
            changed = False
            for block_id in self.blocks:
                if block_id == self.entry_block:
                    continue
                    
                # Dom(n) = {n} ∪ (∩ Dom(p) for all predecessors p)
                block = self.blocks[block_id]
                if not block.predecessors:
                    continue
                    
                new_dom = {block_id}
                pred_doms = [dominators[pred] for pred in block.predecessors if pred in dominators]
                if pred_doms:
                    new_dom.update(set.intersection(*pred_doms))
                
                if new_dom != dominators[block_id]:
                    dominators[block_id] = new_dom
                    changed = True
        
        return dominators
    
    def get_loop_body(self, header_id: int) -> Set[int]:
        """Get all blocks that are part of the loop with given header."""
        if header_id not in self.blocks or not self.blocks[header_id].is_loop_header:
            return set()
        
        loop_body = {header_id}
        header = self.blocks[header_id]
        
        # Start from back edge sources and find all blocks that can reach them
        worklist = list(header.back_edge_sources)
        
        while worklist:
            current = worklist.pop()
            if current in loop_body:
                continue
                
            loop_body.add(current)
            
            # Add predecessors that aren't already in loop body
            block = self.blocks[current]
            for pred in block.predecessors:
                if pred not in loop_body:
                    worklist.append(pred)
        
        return loop_body


class CFGBuilder(ast.NodeVisitor):
    """Build a control flow graph from an AST."""
    
    def __init__(self):
        self.cfg = ControlFlowGraph()
        self.current_block: Optional[int] = None
        self.after_loop_block: Optional[int] = None
        self.break_targets: List[int] = []
        self.continue_targets: List[int] = []
        
    def build(self, tree: ast.AST) -> ControlFlowGraph:
        """Build CFG from AST."""
        # Create entry block
        entry = self.cfg.create_block(BlockType.ENTRY)
        self.current_block = entry
        
        # Visit the AST
        self.visit(tree)
        
        # Create exit block
        exit_block = self.cfg.create_block(BlockType.EXIT)
        
        # Connect final block to exit
        if self.current_block is not None:
            self.cfg.add_edge(self.current_block, exit_block)
        
        # Identify loops
        self.cfg.identify_loops()
        
        return self.cfg
    
    def visit_Module(self, node):
        """Visit module."""
        for stmt in node.body:
            self.visit(stmt)
    
    def visit_Assign(self, node):
        """Visit assignment - add to current block."""
        if self.current_block is not None:
            self.cfg.blocks[self.current_block].statements.append(node)
    
    def visit_AugAssign(self, node):
        """Visit augmented assignment."""
        if self.current_block is not None:
            self.cfg.blocks[self.current_block].statements.append(node)
    
    def visit_If(self, node):
        """Visit if statement - creates branching."""
        if self.current_block is None:
            return
            
        # Add test to current block
        test_block = self.current_block
        # Store the condition in the test block
        self.cfg.blocks[test_block].branch_condition = node.test
        self.cfg.blocks[test_block].type = BlockType.CONDITIONAL
        
        # Create blocks for then and else branches
        then_block = self.cfg.create_block()
        self.cfg.add_edge(test_block, then_block)
        # Store condition info for the then branch
        self.cfg.blocks[test_block].successor_conditions[then_block] = (node.test, True)
        
        # Visit then branch
        self.current_block = then_block
        for stmt in node.body:
            self.visit(stmt)
        then_exit = self.current_block
        
        # Handle else branch
        if node.orelse:
            else_block = self.cfg.create_block()
            self.cfg.add_edge(test_block, else_block)
            # Store condition info for the else branch (negated condition)
            self.cfg.blocks[test_block].successor_conditions[else_block] = (node.test, False)
            
            self.current_block = else_block
            for stmt in node.orelse:
                self.visit(stmt)
            else_exit = self.current_block
        else:
            else_exit = test_block
            
        # Create merge block
        merge_block = self.cfg.create_block()
        if then_exit is not None:
            self.cfg.add_edge(then_exit, merge_block)
        if else_exit is not None and else_exit != test_block:
            self.cfg.add_edge(else_exit, merge_block)
        elif else_exit == test_block:
            # Direct edge from test to merge for missing else
            self.cfg.add_edge(test_block, merge_block)
            # Store condition info for skipping to merge (negated condition)
            self.cfg.blocks[test_block].successor_conditions[merge_block] = (node.test, False)
            
        self.current_block = merge_block
    
    def visit_While(self, node):
        """Visit while loop - creates loop structure."""
        if self.current_block is None:
            return
            
        # Create loop header block
        loop_header = self.cfg.create_block()
        self.cfg.add_edge(self.current_block, loop_header)
        
        # Create loop body block
        loop_body = self.cfg.create_block()
        self.cfg.add_edge(loop_header, loop_body)
        
        # Create after-loop block
        after_loop = self.cfg.create_block()
        self.cfg.add_edge(loop_header, after_loop)
        
        # Save break target
        old_after_loop = self.after_loop_block
        self.after_loop_block = after_loop
        self.break_targets.append(after_loop)
        self.continue_targets.append(loop_header)
        
        # Visit loop body
        self.current_block = loop_body
        for stmt in node.body:
            self.visit(stmt)
            
        # Connect back to header (back edge)
        if self.current_block is not None:
            self.cfg.add_edge(self.current_block, loop_header)
        
        # Restore state
        self.after_loop_block = old_after_loop
        self.break_targets.pop()
        self.continue_targets.pop()
        self.current_block = after_loop
    
    def visit_For(self, node):
        """Visit for loop - similar to while."""
        # For simplicity, treat like while loop
        self.visit_While(node)
    
    def visit_Break(self, node):
        """Visit break statement."""
        if self.current_block is not None and self.break_targets:
            self.cfg.add_edge(self.current_block, self.break_targets[-1])
            self.current_block = None  # Dead code after break
    
    def visit_Continue(self, node):
        """Visit continue statement."""
        if self.current_block is not None and self.continue_targets:
            self.cfg.add_edge(self.current_block, self.continue_targets[-1])
            self.current_block = None  # Dead code after continue
    
    def generic_visit(self, node):
        """Default visit for other statements."""
        if self.current_block is not None and isinstance(node, ast.stmt):
            self.cfg.blocks[self.current_block].statements.append(node)
        super().generic_visit(node)


def build_cfg(tree: ast.AST) -> ControlFlowGraph:
    """Build a control flow graph from an AST."""
    builder = CFGBuilder()
    return builder.build(tree)