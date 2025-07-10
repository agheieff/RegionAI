"""
Semantic fingerprints for high-level behavioral understanding of functions.

This module bridges the gap between low-level analysis data and high-level
semantic understanding by classifying functions based on their behavior patterns.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Set, Optional, Dict, Any, List


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


@dataclass
class NaturalLanguageContext:
    """
    Holds the natural language context associated with a function.
    
    This captures human-readable information that describes what a function
    does, forming the basis for connecting code semantics to natural language.
    """
    function_name: str
    docstring: Optional[str] = None
    parameter_names: List[str] = field(default_factory=list)
    return_description: Optional[str] = None  # Extracted from docstring
    
    # Additional context that could be valuable
    comments: List[str] = field(default_factory=list)  # Inline comments
    variable_names: List[str] = field(default_factory=list)  # Local variable names
    
    def has_documentation(self) -> bool:
        """Check if function has any natural language documentation."""
        return (self.docstring is not None or 
                len(self.comments) > 0 or
                self.return_description is not None)
    
    def get_text_content(self) -> str:
        """Get all text content concatenated for analysis."""
        parts = []
        if self.docstring:
            parts.append(self.docstring)
        if self.return_description:
            parts.append(f"Returns: {self.return_description}")
        if self.comments:
            parts.extend(self.comments)
        return " ".join(parts)


@dataclass
class DocumentedFingerprint:
    """
    Links a semantic fingerprint to its natural language context.
    
    This is the fundamental data structure for the Language Bridge - it connects
    machine-understandable semantic behaviors with human-written descriptions,
    enabling the training of models that understand both code and language.
    """
    fingerprint: SemanticFingerprint
    nl_context: NaturalLanguageContext
    
    def get_semantic_summary(self) -> str:
        """Get a human-readable summary of semantic behaviors."""
        if not self.fingerprint.behaviors:
            return "Function with no identified behaviors"
        
        behavior_names = [b.name.lower().replace('_', ' ') for b in self.fingerprint.behaviors]
        return f"Function with behaviors: {', '.join(behavior_names)}"
    
    def is_well_documented(self) -> bool:
        """Check if function has both semantic fingerprint and documentation."""
        return (len(self.fingerprint.behaviors) > 0 and 
                self.nl_context.has_documentation())
    
    def __str__(self) -> str:
        """Human-readable representation for debugging."""
        return (f"DocumentedFingerprint:\n"
                f"  Function: {self.nl_context.function_name}\n"
                f"  Behaviors: {[b.name for b in self.fingerprint.behaviors]}\n"
                f"  Documented: {self.nl_context.has_documentation()}")


class DocumentationQuality:
    """
    Utilities for assessing the quality of documentation for training purposes.
    """
    
    @staticmethod
    def score_documentation(nl_context: NaturalLanguageContext) -> float:
        """
        Score documentation quality from 0.0 to 1.0.
        
        Higher scores indicate better training data for language models.
        """
        score = 0.0
        
        # Docstring presence and quality
        if nl_context.docstring:
            doc_len = len(nl_context.docstring.strip())
            if doc_len > 10:  # Meaningful docstring
                score += 0.4
            if doc_len > 50:  # Detailed docstring
                score += 0.2
            if "return" in nl_context.docstring.lower():  # Describes return value
                score += 0.1
        else:
            # No docstring significantly hurts the score
            score = 0.0
        
        # Parameter descriptions
        if nl_context.parameter_names:
            # Bonus if parameters have meaningful names
            meaningful_params = sum(1 for name in nl_context.parameter_names 
                                  if len(name) > 2 and name not in ['x', 'y', 'z', 'i', 'j', 'k'])
            if meaningful_params > 0:
                score += 0.1 * min(meaningful_params / len(nl_context.parameter_names), 1.0)
        
        # Additional comments
        if nl_context.comments:
            score += min(0.1, len(nl_context.comments) * 0.05)
        
        return min(score, 1.0)
    
    @staticmethod
    def is_suitable_for_training(documented_fp: DocumentedFingerprint) -> bool:
        """
        Determine if this documented fingerprint is suitable for training.
        
        Good training examples have clear semantics and good documentation.
        """
        # Must have some behaviors identified
        if len(documented_fp.fingerprint.behaviors) == 0:
            return False
        
        # Must have decent documentation
        doc_score = DocumentationQuality.score_documentation(documented_fp.nl_context)
        if doc_score < 0.3:
            return False
        
        # Avoid very complex functions (too many behaviors might be confusing)
        if len(documented_fp.fingerprint.behaviors) > 5:
            return False
        
        return True