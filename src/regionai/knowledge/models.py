"""
Core data structures for the knowledge graph architecture.

This module defines the fundamental types used in both the WorldKnowledgeGraph
(for domain-specific facts) and the ReasoningKnowledgeGraph (for abstract
reasoning tools and heuristics).
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
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
    utility_score: float = 0.5  # Tracks the actual effectiveness of this heuristic
    implementation_id: str = ""  # ID linking to executable function in HeuristicRegistry
    
    def __post_init__(self):
        # Ensure reasoning_type is HEURISTIC for all Heuristic instances
        if self.reasoning_type != ReasoningType.HEURISTIC:
            object.__setattr__(self, 'reasoning_type', ReasoningType.HEURISTIC)


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

# Note: The ConceptMetadata and RelationMetadata classes defined above are
# new versions for the separated architecture. The existing ones in graph.py
# will be migrated here in a future step.