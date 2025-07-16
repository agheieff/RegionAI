"""
Symbolic Language Engine - Core Data Models

This module implements the foundational data structures for the symbolic language
parsing system, as defined in DESIGN-XV.md. These structures support lazy evaluation,
beam-width disambiguation, and memoization for efficient natural language understanding.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict
from ...knowledge.graph import Concept


@dataclass
class RegionCandidate:
    """
    Represents one possible meaning for a linguistic constraint.
    
    A RegionCandidate maps a text phrase to a set of concepts in the knowledge graph,
    along with a probability score indicating the likelihood of this interpretation.
    This is a key component of the beam search strategy for managing ambiguity.
    
    Attributes:
        concept_intersections: The set of concepts defining this potential meaning.
                             These concepts may be existing ones from the knowledge graph
                             or newly proposed concepts.
        probability: The initial score or probability for this candidate (0.0 to 1.0).
                    Higher scores indicate more likely interpretations.
        source_heuristic: The name of the method/heuristic that proposed this candidate.
                         This helps track the reasoning process and can be used for
                         debugging or improving heuristics.
    """
    concept_intersections: Set[Concept]
    probability: float
    source_heuristic: str
    
    def __post_init__(self):
        """Validate the probability is in valid range."""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"Probability must be between 0.0 and 1.0, got {self.probability}")
    
    def __eq__(self, other):
        """Two candidates are equal if they have the same concepts and source."""
        if not isinstance(other, RegionCandidate):
            return False
        return (self.concept_intersections == other.concept_intersections and
                self.source_heuristic == other.source_heuristic)
    
    def __hash__(self):
        """Hash based on concepts and source for use in sets/dicts."""
        # Convert set to sorted tuple for consistent hashing
        # Concept is a NewType of str, so we sort directly
        concepts_tuple = tuple(sorted(self.concept_intersections))
        return hash((concepts_tuple, self.source_heuristic))


@dataclass
class SymbolicConstraint:
    """
    Represents an unresolved linguistic unit that can be lazily evaluated.
    
    A SymbolicConstraint encapsulates a text phrase along with its potential
    interpretations (RegionCandidates). The constraint remains ungrounded until
    explicitly resolved, supporting the lazy evaluation principle.
    
    Attributes:
        text: The original text phrase (e.g., "the red car", "ate quickly").
        possible_regions: The list of top k candidates from beam search.
                         Initially empty, populated when grounding is requested.
        is_grounded: Flag tracking if this constraint has been resolved.
                    False by default, supporting lazy evaluation.
        memoization_key: Unique key for caching this constraint's resolution.
                        Should incorporate both text and syntactic context.
    """
    text: str
    possible_regions: List[RegionCandidate] = field(default_factory=list)
    is_grounded: bool = False
    memoization_key: str = ""
    
    def __post_init__(self):
        """Generate default memoization key if not provided."""
        if not self.memoization_key:
            # Simple default: use the text itself
            # In practice, this should include syntactic context
            self.memoization_key = f"constraint_{self.text.lower().replace(' ', '_')}"
    
    def add_candidate(self, candidate: RegionCandidate, beam_width: Optional[int] = None):
        """
        Add a candidate to the possible regions, maintaining beam width if specified.
        
        Args:
            candidate: The RegionCandidate to add
            beam_width: Optional maximum number of candidates to keep.
                       If specified, keeps only the top k by probability.
        """
        self.possible_regions.append(candidate)
        
        if beam_width is not None and len(self.possible_regions) > beam_width:
            # Sort by probability (descending) and keep top k
            self.possible_regions.sort(key=lambda c: c.probability, reverse=True)
            self.possible_regions = self.possible_regions[:beam_width]
    
    def ground(self, candidates: List[RegionCandidate]):
        """
        Ground this constraint with the provided candidates.
        
        This marks the constraint as grounded and stores the candidates.
        Used when lazy evaluation is triggered and the constraint needs resolution.
        
        Args:
            candidates: List of RegionCandidate objects representing possible meanings
        """
        self.possible_regions = candidates
        self.is_grounded = True
    
    def get_top_candidate(self) -> Optional[RegionCandidate]:
        """
        Get the most probable candidate if any exist.
        
        Returns:
            The RegionCandidate with highest probability, or None if no candidates
        """
        if not self.possible_regions:
            return None
        return max(self.possible_regions, key=lambda c: c.probability)
    
    def __repr__(self):
        """String representation showing key information."""
        status = "grounded" if self.is_grounded else "ungrounded"
        n_candidates = len(self.possible_regions)
        return f"SymbolicConstraint(text='{self.text}', {status}, {n_candidates} candidates)"
    
    def __eq__(self, other):
        """Two constraints are equal if they have the same text and memoization key."""
        if not isinstance(other, SymbolicConstraint):
            return False
        return self.text == other.text and self.memoization_key == other.memoization_key
    
    def __hash__(self):
        """Hash based on text and memoization key."""
        return hash((self.text, self.memoization_key))


@dataclass
class ParseTree:
    """
    Hierarchical representation of a parsed sentence.
    
    A ParseTree represents the nested structure of a sentence, with a root
    SymbolicConstraint representing the main clause and optional children
    representing sub-clauses, modifiers, or dependent phrases.
    
    This recursive structure allows for natural representation of complex
    linguistic constructions like relative clauses, prepositional phrases,
    and coordinate structures.
    
    Attributes:
        root_constraint: The top-level constraint representing the entire
                        sentence or the main clause of this subtree.
        children: Dictionary mapping constraints to their own subtrees,
                 enabling recursive nesting of linguistic structures.
    """
    root_constraint: SymbolicConstraint
    children: Dict[SymbolicConstraint, 'ParseTree'] = field(default_factory=dict)
    
    def add_child(self, parent_constraint: SymbolicConstraint, child_tree: 'ParseTree'):
        """
        Add a child subtree to a specific constraint.
        
        Args:
            parent_constraint: The constraint to attach the child to
            child_tree: The subtree representing the child structure
        """
        self.children[parent_constraint] = child_tree
    
    def get_all_constraints(self) -> List[SymbolicConstraint]:
        """
        Get all constraints in the tree (recursive).
        
        Returns:
            List of all SymbolicConstraints in the tree, including
            those in child subtrees.
        """
        constraints = [self.root_constraint]
        
        # Add constraints from children recursively
        for child_tree in self.children.values():
            constraints.extend(child_tree.get_all_constraints())
        
        return constraints
    
    def get_depth(self) -> int:
        """
        Get the maximum depth of the parse tree.
        
        Returns:
            The depth of the tree (1 for a single node, 2 for one level of children, etc.)
        """
        if not self.children:
            return 1
        
        max_child_depth = max(child.get_depth() for child in self.children.values())
        return 1 + max_child_depth
    
    def __repr__(self):
        """
        String representation showing tree structure.
        """
        n_children = len(self.children)
        depth = self.get_depth()
        return f"ParseTree(root='{self.root_constraint.text}', children={n_children}, depth={depth})"