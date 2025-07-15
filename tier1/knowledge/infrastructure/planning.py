"""
Planning domain models for goal-oriented reasoning.

This module defines the core data structures that represent goals, plans, and
execution strategies. These models form the vocabulary for RegionAI's planning
layer, enabling it to transition from passive analysis to proactive problem-solving.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from tier1.knowledge.infrastructure.world_graph import Concept
from tier1.knowledge.infrastructure.reasoning_graph import Heuristic, FunctionArtifact


@dataclass
class Goal:
    """
    Represents a high-level objective for the planning system.
    
    A goal encapsulates what the user wants to achieve, which concepts
    are relevant, and any constraints on how to achieve it.
    
    Examples:
        Goal(
            description="Find all functions that might contain SQL injection vulnerabilities",
            target_concepts=[Concept("User"), Concept("Query")],
            constraints={'max_depth': 5, 'focus_on_behaviors': ['PERFORMS_IO']}
        )
    """
    description: str
    target_concepts: List[Concept]
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate goal data."""
        if not self.description:
            raise ValueError("Goal must have a description")
        if not self.target_concepts:
            raise ValueError("Goal must have at least one target concept")


@dataclass
class PlanStep:
    """
    Represents a single action in an execution plan.
    
    Each step specifies which heuristic to apply, what code artifact
    to apply it to, and why this step was chosen.
    """
    heuristic: Heuristic
    target_artifact: FunctionArtifact
    justification: str
    
    def __str__(self):
        """Human-readable representation of the plan step."""
        return (f"Apply {self.heuristic.name} to {self.target_artifact.function_name}: "
                f"{self.justification}")


@dataclass
class ExecutionPlan:
    """
    Represents a complete plan to achieve a goal.
    
    An execution plan consists of an ordered sequence of steps that,
    when executed, should accomplish the specified goal.
    """
    goal: Goal
    steps: List[PlanStep]
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    
    def __post_init__(self):
        """Validate plan status."""
        valid_statuses = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the plan."""
        return (f"Plan to achieve: {self.goal.description}\n"
                f"Status: {self.status}\n"
                f"Steps: {len(self.steps)}")
    
    def mark_in_progress(self):
        """Mark the plan as being executed."""
        self.status = "IN_PROGRESS"
    
    def mark_completed(self):
        """Mark the plan as successfully completed."""
        self.status = "COMPLETED"
    
    def mark_failed(self):
        """Mark the plan as failed."""
        self.status = "FAILED"


from .actions import GeneratedFix  # Import for generated fixes


@dataclass
class PlanResult:
    """
    Represents the outcome of executing a plan.
    
    This captures what was discovered, what happened during execution,
    whether the plan succeeded in achieving its goal, and any fixes generated.
    """
    plan: ExecutionPlan
    new_discoveries: List[str] = field(default_factory=list)
    execution_log: List[str] = field(default_factory=list)
    status: str = "PENDING"  # SUCCESS, PARTIAL_SUCCESS, FAILURE
    generated_fixes: List[GeneratedFix] = field(default_factory=list)  # Stores code fixes
    
    def __post_init__(self):
        """Validate result status."""
        valid_statuses = {"PENDING", "SUCCESS", "PARTIAL_SUCCESS", "FAILURE"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
    
    def add_discovery(self, discovery: str):
        """Add a new discovery to the results."""
        self.new_discoveries.append(discovery)
    
    def add_log_entry(self, entry: str):
        """Add an entry to the execution log."""
        self.execution_log.append(entry)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the execution results."""
        return (f"Plan execution {self.status}\n"
                f"Steps executed: {len([s for s in self.execution_log if 'Executing' in s])}\n"
                f"New discoveries: {len(self.new_discoveries)}\n"
                f"Generated fixes: {len(self.generated_fixes)}")