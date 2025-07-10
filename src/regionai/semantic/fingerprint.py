"""
Semantic fingerprints for high-level behavioral understanding of functions.

This module bridges the gap between low-level analysis data and high-level
semantic understanding by classifying functions based on their behavior patterns.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Set, Optional, Dict, Any


class Behavior(Enum):
    """Enumerates conceptual behaviors of a function."""
    
    # Identity: returns one of its arguments unchanged
    IDENTITY = auto()
    
    # Constant Return: always returns the same constant value
    CONSTANT_RETURN = auto()
    
    # Nullable Return: may return a None value
    NULLABLE_RETURN = auto()
    
    # Preserves Sign: if input is positive, output is positive (and vice-versa)
    PRESERVES_SIGN = auto()
    
    # Pure Function: no side effects, always returns same output for same input
    PURE = auto()
    
    # May Not Return: function might not return (infinite loop, exception)
    MAY_NOT_RETURN = auto()
    
    # May Throw: function might throw an exception
    MAY_THROW = auto()
    
    # Modifies Parameters: function modifies mutable parameters
    MODIFIES_PARAMETERS = auto()
    
    # Modifies Globals: function modifies global state
    MODIFIES_GLOBALS = auto()
    
    # Performs IO: function performs input/output operations
    PERFORMS_IO = auto()
    
    # Monotonic: output increases/decreases monotonically with input
    MONOTONIC_INCREASING = auto()
    MONOTONIC_DECREASING = auto()
    
    # Range Preserving: output range is subset of input range
    RANGE_PRESERVING = auto()
    
    # Range Expanding: output range is superset of input range
    RANGE_EXPANDING = auto()
    
    # Null Safe: never returns null if input is not null
    NULL_SAFE = auto()
    
    # Null Propagating: returns null if any input is null
    NULL_PROPAGATING = auto()
    
    # Validator: returns boolean based on input validation
    VALIDATOR = auto()
    
    # Transformer: transforms input to different type/structure
    TRANSFORMER = auto()
    
    # Aggregator: reduces multiple inputs to single output
    AGGREGATOR = auto()
    
    # Generator: produces values (possibly infinite sequence)
    GENERATOR = auto()
    
    # Recursive: function calls itself
    RECURSIVE = auto()
    
    # Tail Recursive: recursive with tail call optimization possible
    TAIL_RECURSIVE = auto()
    
    # Idempotent: f(f(x)) = f(x)
    IDEMPOTENT = auto()
    
    # Commutative: f(a, b) = f(b, a)
    COMMUTATIVE = auto()
    
    # Associative: f(f(a, b), c) = f(a, f(b, c))
    ASSOCIATIVE = auto()


@dataclass
class SemanticFingerprint:
    """
    Holds the set of identified behaviors for a function in a specific context.
    
    A semantic fingerprint captures the essential behavioral characteristics
    of a function, abstracting away from specific values to conceptual properties.
    """
    behaviors: Set[Behavior] = field(default_factory=set)
    
    # Optional metadata for richer semantic understanding
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_behavior(self, behavior: Behavior, **kwargs):
        """Add a behavior to the fingerprint with optional metadata."""
        self.behaviors.add(behavior)
        if kwargs:
            self.metadata[behavior.name] = kwargs
    
    def has_behavior(self, behavior: Behavior) -> bool:
        """Check if the fingerprint includes a specific behavior."""
        return behavior in self.behaviors
    
    def is_pure(self) -> bool:
        """Check if function is pure (no side effects)."""
        return (self.has_behavior(Behavior.PURE) or
                (not self.has_behavior(Behavior.MODIFIES_PARAMETERS) and
                 not self.has_behavior(Behavior.MODIFIES_GLOBALS) and
                 not self.has_behavior(Behavior.PERFORMS_IO) and
                 not self.has_behavior(Behavior.MAY_THROW)))
    
    def is_safe(self) -> bool:
        """Check if function is safe (no exceptions, always returns)."""
        return (not self.has_behavior(Behavior.MAY_NOT_RETURN) and
                not self.has_behavior(Behavior.MAY_THROW))
    
    def is_deterministic(self) -> bool:
        """Check if function is deterministic (same input -> same output)."""
        return (self.is_pure() and
                not self.has_behavior(Behavior.GENERATOR))
    
    def get_behavior_metadata(self, behavior: Behavior) -> Optional[Dict[str, Any]]:
        """Get metadata associated with a specific behavior."""
        return self.metadata.get(behavior.name)
    
    def __str__(self) -> str:
        """Human-readable representation of the fingerprint."""
        if not self.behaviors:
            return "SemanticFingerprint: No behaviors identified"
        
        lines = ["SemanticFingerprint:"]
        for behavior in sorted(self.behaviors, key=lambda b: b.name):
            line = f"  - {behavior.name}"
            if behavior.name in self.metadata:
                line += f" {self.metadata[behavior.name]}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        behavior_names = sorted(b.name for b in self.behaviors)
        return f"SemanticFingerprint({behavior_names})"


@dataclass
class FingerprintComparison:
    """
    Represents the comparison between two semantic fingerprints.
    
    Useful for understanding how function behavior changes across contexts
    or how two functions relate semantically.
    """
    fingerprint1: SemanticFingerprint
    fingerprint2: SemanticFingerprint
    
    @property
    def common_behaviors(self) -> Set[Behavior]:
        """Behaviors present in both fingerprints."""
        return self.fingerprint1.behaviors & self.fingerprint2.behaviors
    
    @property
    def unique_to_first(self) -> Set[Behavior]:
        """Behaviors only in the first fingerprint."""
        return self.fingerprint1.behaviors - self.fingerprint2.behaviors
    
    @property
    def unique_to_second(self) -> Set[Behavior]:
        """Behaviors only in the second fingerprint."""
        return self.fingerprint2.behaviors - self.fingerprint1.behaviors
    
    @property
    def similarity_score(self) -> float:
        """
        Compute similarity between fingerprints (Jaccard index).
        
        Returns a value between 0 (no overlap) and 1 (identical).
        """
        if not self.fingerprint1.behaviors and not self.fingerprint2.behaviors:
            return 1.0
        
        union = self.fingerprint1.behaviors | self.fingerprint2.behaviors
        if not union:
            return 0.0
        
        intersection = self.fingerprint1.behaviors & self.fingerprint2.behaviors
        return len(intersection) / len(union)
    
    def are_semantically_equivalent(self) -> bool:
        """Check if the fingerprints represent semantically equivalent functions."""
        # For now, consider them equivalent if they have the same behaviors
        # In the future, this could be more sophisticated
        return self.fingerprint1.behaviors == self.fingerprint2.behaviors