"""
Data structures for representing Lean proofs in RegionAI.

This module defines the core AST (Abstract Syntax Tree) structures for
internal representation of Lean theorem proofs. These structures form
the foundation for the mathematical reasoning capabilities of RegionAI.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class TacticType(Enum):
    """Types of tactics available in Lean proofs."""
    INTRO = "intro"
    APPLY = "apply"
    EXACT = "exact"
    REWRITE = "rewrite"
    SIMP = "simp"
    RING = "ring"
    NORM_NUM = "norm_num"
    ASSUMPTION = "assumption"
    CONSTRUCTOR = "constructor"
    CASES = "cases"
    INDUCTION = "induction"
    BY_CONTRA = "by_contra"
    USE = "use"
    HAVE = "have"
    SHOW = "show"
    CUSTOM = "custom"


@dataclass
class Hypothesis:
    """
    Represents a hypothesis in a Lean proof context.
    
    A hypothesis is an assumption or given fact that can be used
    in the proof. It has a name (identifier) and a type (proposition).
    
    Attributes:
        name: The identifier for this hypothesis (e.g., 'h1', 'n_pos')
        type_expr: The type/proposition of the hypothesis (e.g., 'n > 0')
        value: Optional value if the hypothesis has a definition
        metadata: Additional information about the hypothesis
    """
    name: str
    type_expr: str
    value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        if self.value:
            return f"{self.name} : {self.type_expr} := {self.value}"
        return f"{self.name} : {self.type_expr}"
    
    def to_lean(self) -> str:
        """Convert to Lean syntax."""
        return str(self)


@dataclass
class Tactic:
    """
    Represents a single tactic application in a Lean proof.
    
    Tactics are the atomic steps in a proof that transform the goal
    state. Each tactic may have arguments and can produce new subgoals.
    
    Attributes:
        tactic_type: The type of tactic being applied
        arguments: Arguments passed to the tactic
        target: Optional target hypothesis or expression
        new_hypotheses: Hypotheses introduced by this tactic
        metadata: Additional information (e.g., source location, timing)
    """
    tactic_type: TacticType
    arguments: List[str] = field(default_factory=list)
    target: Optional[str] = None
    new_hypotheses: List[Hypothesis] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        parts = [self.tactic_type.value]
        
        if self.target:
            parts.append(self.target)
            
        if self.arguments:
            parts.extend(self.arguments)
            
        return " ".join(parts)
    
    def to_lean(self) -> str:
        """Convert to Lean tactic syntax."""
        return str(self)
    
    def is_closing_tactic(self) -> bool:
        """Check if this tactic typically closes goals."""
        return self.tactic_type in [
            TacticType.EXACT, 
            TacticType.ASSUMPTION,
            TacticType.RING,
            TacticType.NORM_NUM
        ]


@dataclass
class ProofState:
    """
    Represents the state at a point in the proof.
    
    Attributes:
        theorem_name: Name of theorem being proved
        hypotheses: Available hypotheses in context
        current_goal: Current goal to prove (empty if complete)
        remaining_goals: Other goals still to prove
        is_complete: Whether all goals have been proven
        applied_tactics: Tactics applied so far
        metadata: Additional state information
    """
    theorem_name: Optional[str] = None
    hypotheses: List[Hypothesis] = field(default_factory=list)
    current_goal: str = ""
    remaining_goals: List[str] = field(default_factory=list)
    is_complete: bool = False
    applied_tactics: List[Tactic] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def goals(self) -> List[str]:
        """Get all goals (current + remaining)."""
        if self.is_complete:
            return []
        goals = []
        if self.current_goal:
            goals.append(self.current_goal)
        goals.extend(self.remaining_goals)
        return goals
    
    @property
    def completed(self) -> bool:
        """Alias for is_complete for compatibility."""
        return self.is_complete
    
    def __str__(self) -> str:
        if self.completed:
            return "Proof complete!"
        
        lines = ["Current proof state:"]
        
        if self.hypotheses:
            lines.append("Hypotheses:")
            for hyp in self.hypotheses:
                lines.append(f"  {hyp}")
                
        if self.goals:
            lines.append("Goals:")
            for i, goal in enumerate(self.goals, 1):
                lines.append(f"  {i}. {goal}")
                
        return "\n".join(lines)


@dataclass
class Theorem:
    """
    Represents a complete theorem with its proof.
    
    A theorem consists of a statement (what we want to prove) and
    a sequence of tactics that constitute the proof.
    
    Attributes:
        name: The name of the theorem
        statement: The proposition to be proved
        proof_tactics: Sequence of tactics that prove the theorem
        hypotheses: Initial hypotheses/parameters of the theorem
        metadata: Additional information (e.g., source file, difficulty)
        proof_states: Optional recording of intermediate proof states
    """
    name: str
    statement: str
    proof_tactics: List[Tactic] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list) 
    metadata: Dict[str, Any] = field(default_factory=dict)
    proof_states: Optional[List[ProofState]] = None
    
    def __str__(self) -> str:
        lines = [f"theorem {self.name} : {self.statement} := by"]
        
        for tactic in self.proof_tactics:
            lines.append(f"  {tactic.to_lean()}")
            
        return "\n".join(lines)
    
    def to_lean(self) -> str:
        """Convert to Lean theorem syntax."""
        return str(self)
    
    def add_tactic(self, tactic: Tactic) -> None:
        """Add a tactic to the proof."""
        self.proof_tactics.append(tactic)
        
    def get_proof_length(self) -> int:
        """Get the number of tactics in the proof."""
        return len(self.proof_tactics)
    
    def uses_tactic(self, tactic_type: TacticType) -> bool:
        """Check if the proof uses a specific tactic type."""
        return any(t.tactic_type == tactic_type for t in self.proof_tactics)
    
    def get_tactic_distribution(self) -> Dict[TacticType, int]:
        """Get count of each tactic type used in the proof."""
        distribution = {}
        for tactic in self.proof_tactics:
            tactic_type = tactic.tactic_type
            distribution[tactic_type] = distribution.get(tactic_type, 0) + 1
        return distribution


@dataclass
class ProofStep:
    """
    Represents a single step in a proof attempt.
    
    This is used for recording proof traces and includes timing
    and state information.
    
    Attributes:
        step_number: Sequential step number
        tactic: The tactic applied at this step
        before_state: State before applying the tactic
        after_state: State after applying the tactic
        success: Whether the tactic application succeeded
        error: Error message if the tactic failed
        time_ms: Time taken to apply the tactic in milliseconds
    """
    step_number: int
    tactic: Tactic
    before_state: ProofState
    after_state: Optional[ProofState] = None
    success: bool = False
    error: Optional[str] = None
    time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'step_number': self.step_number,
            'tactic': str(self.tactic),
            'tactic_type': self.tactic.tactic_type.value,
            'before_goals': [str(g) for g in self.before_state.goals],
            'after_goals': [str(g) for g in self.after_state.goals] if self.after_state else [],
            'success': self.success,
            'error': self.error,
            'time_ms': self.time_ms,
            'hypotheses_count': len(self.before_state.hypotheses)
        }


class TheoremDatabase:
    """
    Simple database for storing and retrieving theorems.
    
    This will be expanded in future phases to support:
    - Semantic search
    - Difficulty estimation
    - Proof pattern extraction
    """
    
    def __init__(self):
        self.theorems: Dict[str, Theorem] = {}
        self.by_tactic: Dict[TacticType, List[str]] = {}
        
    def add_theorem(self, theorem: Theorem) -> None:
        """Add a theorem to the database."""
        self.theorems[theorem.name] = theorem
        
        # Index by tactics used
        for tactic in theorem.proof_tactics:
            if tactic.tactic_type not in self.by_tactic:
                self.by_tactic[tactic.tactic_type] = []
            if theorem.name not in self.by_tactic[tactic.tactic_type]:
                self.by_tactic[tactic.tactic_type].append(theorem.name)
                
    def get_theorem(self, name: str) -> Optional[Theorem]:
        """Retrieve a theorem by name."""
        return self.theorems.get(name)
    
    def find_theorems_using_tactic(self, tactic_type: TacticType) -> List[Theorem]:
        """Find all theorems that use a specific tactic."""
        theorem_names = self.by_tactic.get(tactic_type, [])
        return [self.theorems[name] for name in theorem_names]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        total_tactics = sum(t.get_proof_length() for t in self.theorems.values())
        
        return {
            'total_theorems': len(self.theorems),
            'total_tactics': total_tactics,
            'average_proof_length': total_tactics / len(self.theorems) if self.theorems else 0,
            'tactic_usage': {
                tactic_type.value: len(theorems) 
                for tactic_type, theorems in self.by_tactic.items()
            }
        }