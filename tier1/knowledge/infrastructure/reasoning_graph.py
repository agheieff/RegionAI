"""
Core data structures for the knowledge graph architecture.

This module defines the fundamental types used in both the WorldKnowledgeGraph
(for domain-specific facts) and the ReasoningKnowledgeGraph (for abstract
reasoning tools and heuristics).
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from datetime import datetime
import networkx as nx


# ============================================================================
# Shared Base Types
# ============================================================================

# Import the base types from graph.py for now
# These will be moved here in a future refactoring
from typing import NewType

Concept = NewType('Concept', str)
Relation = NewType('Relation', str)


# ============================================================================
# Metadata Classes
# ============================================================================

@dataclass
class ConceptMetadata:
    """
    Metadata associated with a concept in the knowledge graph.
    
    This includes probabilistic belief parameters (alpha/beta for Beta distribution),
    discovery method, and additional properties.
    """
    discovery_method: str
    alpha: float = 1.0  # Prior belief (successes + 1)
    beta: float = 1.0   # Prior disbelief (failures + 1)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence(self) -> float:
        """Calculate the confidence/belief in this concept's existence."""
        return self.alpha / (self.alpha + self.beta)


@dataclass
class RelationMetadata:
    """
    Metadata associated with a relationship in the knowledge graph.
    
    Similar to ConceptMetadata, tracks belief in the relationship's validity.
    """
    relation_type: str
    alpha: float = 1.0  # Prior belief
    beta: float = 1.0   # Prior disbelief
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence(self) -> float:
        """Calculate the confidence/belief in this relationship."""
        return self.alpha / (self.alpha + self.beta)


# ============================================================================
# Reasoning Knowledge Graph Types
# ============================================================================

class ReasoningType(Enum):
    """Types of reasoning concepts."""
    STRATEGY = "strategy"           # High-level reasoning strategies
    HEURISTIC = "heuristic"        # Specific applicable rules
    PRINCIPLE = "principle"        # Fundamental reasoning principles
    PATTERN = "pattern"            # Common reasoning patterns
    FALLACY = "fallacy"            # Common reasoning errors to avoid


@dataclass(frozen=True)
class ReasoningConcept:
    """
    An abstract concept about reasoning itself.
    
    Examples:
    - Causality (understanding cause and effect)
    - Induction (generalizing from examples)
    - Deduction (deriving specifics from general rules)
    - Analogy (reasoning by similarity)
    """
    name: str
    reasoning_type: ReasoningType
    description: str
    
    def __repr__(self):
        return f"ReasoningConcept({self.name}, {self.reasoning_type.value})"
    
    def as_concept(self) -> Concept:
        """Convert to a Concept for graph operations."""
        return Concept(self.name)


@dataclass(frozen=True)
class Heuristic(ReasoningConcept):
    """
    A specific, applicable reasoning rule or guideline.
    
    Examples:
    - Occam's Razor: "Prefer simpler explanations"
    - Means-Ends Analysis: "Work backward from the goal"
    - Divide and Conquer: "Break problems into subproblems"
    """
    applicability_conditions: Tuple[str, ...] = field(default_factory=tuple)
    expected_utility: float = 0.5  # How useful this heuristic typically is
    utility_model: Dict[str, float] = field(default_factory=lambda: {"default": 0.5})  # Context-specific utility scores
    implementation_id: str = ""  # ID linking to executable function in HeuristicRegistry
    
    def __post_init__(self):
        # Ensure reasoning_type is HEURISTIC for all Heuristic instances
        if self.reasoning_type != ReasoningType.HEURISTIC:
            object.__setattr__(self, 'reasoning_type', ReasoningType.HEURISTIC)
        
        # If utility_model doesn't have default, add it
        if "default" not in self.utility_model:
            # Create a new dict with default
            new_model = dict(self.utility_model)
            new_model["default"] = self.expected_utility
            object.__setattr__(self, 'utility_model', new_model)
    
    def get_utility_for_context(self, context_tag: str) -> float:
        """Get the utility score for a specific context."""
        return self.utility_model.get(context_tag, self.utility_model.get("default", 0.5))
    
    def __hash__(self):
        """Make heuristic hashable for use in graphs."""
        # Use immutable attributes for hashing
        return hash((self.name, self.reasoning_type, self.implementation_id))
    
    def __eq__(self, other):
        """Compare heuristics by key attributes."""
        if not isinstance(other, Heuristic):
            return False
        return (self.name == other.name and 
                self.reasoning_type == other.reasoning_type and
                self.implementation_id == other.implementation_id)


@dataclass(frozen=True)
class ComposedHeuristic(Heuristic):
    """
    A synthesized heuristic created by analyzing successful reasoning chains.
    
    Unlike basic heuristics, a ComposedHeuristic doesn't have its own
    implementation. Instead, it executes its component heuristics in sequence,
    representing a discovered reasoning pattern.
    """
    component_heuristic_ids: Tuple[str, ...] = field(default_factory=tuple)
    
    def __post_init__(self):
        # Call parent post_init
        super().__post_init__()
        
        # ComposedHeuristics should not have an implementation_id
        if self.implementation_id:
            raise ValueError("ComposedHeuristic should not have an implementation_id")
        
        # Must have at least 2 components to be meaningful
        if len(self.component_heuristic_ids) < 2:
            raise ValueError("ComposedHeuristic must have at least 2 component heuristics")
    
    def get_pattern_description(self) -> str:
        """Get a description of the reasoning pattern."""
        return f"Sequential execution of {len(self.component_heuristic_ids)} heuristics"
    
    def __hash__(self):
        """Make composed heuristic hashable for use in graphs."""
        # Include component IDs in hash
        return hash((self.name, self.reasoning_type, tuple(self.component_heuristic_ids)))
    
    def __eq__(self, other):
        """Compare composed heuristics by key attributes."""
        if not isinstance(other, ComposedHeuristic):
            return False
        return (self.name == other.name and 
                self.reasoning_type == other.reasoning_type and
                self.component_heuristic_ids == other.component_heuristic_ids)


@dataclass
class ReasoningMetadata:
    """
    Metadata for reasoning concepts and heuristics.
    
    Includes information about when and how to apply reasoning strategies.
    """
    discovery_source: str  # Where this reasoning concept was learned from
    usage_count: int = 0   # How often this has been applied
    success_count: int = 0 # How often it led to successful outcomes
    context_tags: List[str] = field(default_factory=list)  # When to apply
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of this reasoning strategy."""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count


# ============================================================================
# Graph Wrapper Classes
# ============================================================================

class ReasoningKnowledgeGraph:
    """
    A knowledge graph specifically for reasoning concepts and heuristics.
    
    This graph models:
    - Abstract reasoning concepts (induction, deduction, etc.)
    - Specific heuristics and when to apply them
    - Relationships between reasoning strategies
    - Meta-reasoning capabilities
    """
    
    def __init__(self):
        """Initialize an empty reasoning knowledge graph."""
        self.graph = nx.MultiDiGraph()
        self._initialize_core_concepts()
    
    def _initialize_core_concepts(self):
        """Add fundamental reasoning concepts that come pre-loaded."""
        # Core reasoning strategies
        core_strategies = [
            ReasoningConcept(
                name="Deduction",
                reasoning_type=ReasoningType.STRATEGY,
                description="Derive specific conclusions from general premises"
            ),
            ReasoningConcept(
                name="Induction", 
                reasoning_type=ReasoningType.STRATEGY,
                description="Generalize from specific examples to general rules"
            ),
            ReasoningConcept(
                name="Abduction",
                reasoning_type=ReasoningType.STRATEGY,
                description="Infer the most likely explanation for observations"
            ),
            ReasoningConcept(
                name="Analogy",
                reasoning_type=ReasoningType.STRATEGY,
                description="Reason by finding similarities between situations"
            ),
        ]
        
        # Add core strategies to graph
        for concept in core_strategies:
            self.add_concept(concept, ReasoningMetadata(
                discovery_source="built-in",
                context_tags=["fundamental", "always_applicable"]
            ))
        
        # Core heuristics
        core_heuristics = [
            Heuristic(
                name="OccamsRazor",
                reasoning_type=ReasoningType.HEURISTIC,
                description="Prefer simpler explanations over complex ones",
                applicability_conditions=("multiple_explanations_available",),
                expected_utility=0.7
            ),
            Heuristic(
                name="DivideAndConquer",
                reasoning_type=ReasoningType.HEURISTIC,
                description="Break complex problems into smaller subproblems",
                applicability_conditions=("problem_is_decomposable",),
                expected_utility=0.8
            ),
        ]
        
        # Add core heuristics
        for heuristic in core_heuristics:
            self.add_concept(heuristic, ReasoningMetadata(
                discovery_source="built-in",
                context_tags=["problem_solving"]
            ))
    
    def add_concept(self, concept: ReasoningConcept, metadata: Optional[ReasoningMetadata] = None):
        """Add a reasoning concept to the graph."""
        if metadata is None:
            metadata = ReasoningMetadata(discovery_source="unknown")
        
        self.graph.add_node(concept, metadata=metadata)
    
    def add_relation(self, source: ReasoningConcept, target: ReasoningConcept, 
                    relation: Relation, confidence: float = 0.5):
        """Add a relationship between reasoning concepts."""
        self.graph.add_edge(
            source, target,
            label=relation,
            confidence=confidence
        )
    
    def get_applicable_heuristics(self, context_tags: List[str]) -> List[Heuristic]:
        """Find heuristics applicable to the given context."""
        applicable = []
        
        for node in self.graph.nodes():
            if isinstance(node, Heuristic):
                metadata = self.graph.nodes[node]['metadata']
                # Check if any context tags match
                if any(tag in metadata.context_tags for tag in context_tags):
                    applicable.append(node)
        
        # Sort by expected utility
        applicable.sort(key=lambda h: h.expected_utility, reverse=True)
        return applicable
    
    def __contains__(self, concept: ReasoningConcept) -> bool:
        """Check if a concept exists in the graph."""
        return concept in self.graph
    
    def __len__(self) -> int:
        """Return the number of concepts in the graph."""
        return len(self.graph)


# ============================================================================
# World Knowledge Graph Types  
# ============================================================================

# Import NaturalLanguageContext from local interfaces to avoid circular import
from .interfaces import NaturalLanguageContext

@dataclass
class FunctionArtifact:
    """
    Represents a function as an artifact in the world knowledge graph.
    
    This captures both the semantic understanding of what the function does
    and the natural language context from its documentation and comments.
    """
    function_name: str
    file_path: str
    semantic_fingerprint: Optional['SemanticFingerprint'] = None
    natural_language_context: Optional[NaturalLanguageContext] = None
    discovered_concepts: List[Concept] = field(default_factory=list)
    discovery_timestamp: str = field(default_factory=lambda: str(datetime.now()))
    source_code: Optional[str] = None  # The actual source code of the function
    
    def __hash__(self):
        """Make hashable for use in graphs."""
        return hash((self.function_name, self.file_path))
    
    def __eq__(self, other):
        """Compare by key attributes."""
        if not isinstance(other, FunctionArtifact):
            return False
        return (self.function_name == other.function_name and 
                self.file_path == other.file_path)

# Note: The ConceptMetadata and RelationMetadata classes defined above are
# new versions for the separated architecture. The existing ones in graph.py
# will be migrated here in a future step.