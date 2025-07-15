"""
Core Knowledge Graph data structures for representing real-world concepts.

This module provides the foundation for RegionAI's Common Sense Engine,
enabling it to build and reason about a structured model of reality
based on the code it analyzes.
"""
from typing import Any, Dict, List, Optional, Set, Tuple, NewType, Union
from dataclasses import dataclass, field
from datetime import datetime
import networkx as nx
import json


# Type definitions for clarity and type safety
Concept = NewType('Concept', str)
Relation = NewType('Relation', str)


@dataclass
class ConceptMetadata:
    """
    Metadata associated with a discovered concept.
    
    Tracks where and how a concept was discovered, providing traceability
    back to the source code that revealed its existence.
    """
    # Discovery information
    discovered_at: datetime = field(default_factory=datetime.now)
    discovery_method: str = ""  # e.g., "CRUD_PATTERN", "NLP_EXTRACTION"
    
    # NEW: Bayesian belief parameters for concept existence confidence
    # Represents our belief that this concept truly exists in the domain
    alpha: float = 1.0  # Evidence for the concept's existence
    beta: float = 1.0   # Evidence against the concept's existence
    
    # Source information
    source_functions: List[str] = field(default_factory=list)
    source_files: Set[str] = field(default_factory=set)
    
    # Semantic information
    related_behaviors: Set[str] = field(default_factory=set)  # Behavior names
    docstring_mentions: List[str] = field(default_factory=list)
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence(self) -> float:
        """Calculate confidence from alpha/beta parameters."""
        # Using mean of Beta distribution: alpha / (alpha + beta)
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def belief(self) -> float:
        """
        Calculates the expected belief score from the Beta distribution.
        Returns a probability between 0 and 1.
        """
        if self.alpha + self.beta == 0:
            return 0.5  # Avoid division by zero, return max uncertainty
        return self.alpha / (self.alpha + self.beta)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'discovered_at': self.discovered_at.isoformat(),
            'discovery_method': self.discovery_method,
            'alpha': self.alpha,
            'beta': self.beta,
            'belief': self.belief,  # Include calculated belief for convenience
            'source_functions': self.source_functions,
            'source_files': list(self.source_files),
            'related_behaviors': list(self.related_behaviors),
            'docstring_mentions': self.docstring_mentions,
            'properties': self.properties
        }
    
    @property
    def confidence(self) -> float:
        """Backward compatibility property - returns belief."""
        return self.belief


@dataclass
class RelationMetadata:
    """
    Metadata for relationships between concepts.
    
    Captures not just that two concepts are related, but how we know
    they're related based on code analysis and textual evidence.
    """
    relation_type: str  # e.g., "HAS_ONE", "HAS_MANY", "BELONGS_TO"
    discovered_at: datetime = field(default_factory=datetime.now)
    
    # NEW: Bayesian belief parameters (alpha/beta) instead of simple confidence
    # Represents the belief in this relationship's truthfulness.
    # Starts at (1, 1) which is a uniform (max uncertainty) distribution.
    alpha: float = 1.0
    beta: float = 1.0
    
    # Evidence for this relationship
    evidence_functions: List[str] = field(default_factory=list)
    evidence_patterns: List[str] = field(default_factory=list)
    
    @property
    def belief(self) -> float:
        """
        Calculates the expected belief score from the Beta distribution.
        Returns a probability between 0 and 1.
        """
        if self.alpha + self.beta == 0:
            return 0.5  # Avoid division by zero, return max uncertainty
        return self.alpha / (self.alpha + self.beta)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'relation_type': self.relation_type,
            'discovered_at': self.discovered_at.isoformat(),
            'alpha': self.alpha,
            'beta': self.beta,
            'belief': self.belief,  # Include the calculated belief for convenience
            'evidence_functions': self.evidence_functions,
            'evidence_patterns': self.evidence_patterns
        }
    
    @property
    def confidence(self) -> float:
        """Backward compatibility property - returns belief."""
        return self.belief


class WorldKnowledgeGraph:
    """
    A graph representing real-world concepts and their relationships.
    
    This is the core data structure of RegionAI's Common Sense Engine.
    It builds a model of reality by analyzing how code manipulates
    real-world entities. This graph specifically focuses on domain-specific
    knowledge about the world, as opposed to abstract reasoning strategies.
    """
    
    def __init__(self):
        """Initialize an empty knowledge graph."""
        # Use MultiDiGraph to allow multiple relationships between concepts
        self.graph = nx.MultiDiGraph()
        
        # Track concept hierarchies separately for efficient queries
        self._concept_hierarchy: Dict[Concept, Set[Concept]] = {}
        
        # Statistics
        self._stats = {
            'concepts_added': 0,
            'relations_added': 0,
            'last_modified': datetime.now()
        }
    
    def add_concept(self, concept: Concept, 
                   metadata: Optional[ConceptMetadata] = None) -> None:
        """
        Add a concept node to the graph.
        
        Args:
            concept: The concept name (e.g., "User", "Invoice")
            metadata: Optional metadata about how this concept was discovered
        """
        # Don't overwrite existing concepts
        if concept in self.graph:
            return
            
        if metadata is None:
            metadata = ConceptMetadata()
        
        self.graph.add_node(concept, metadata=metadata)
        self._stats['concepts_added'] += 1
        self._stats['last_modified'] = datetime.now()
    
    def add_relation(self, source: Concept, target: Concept, 
                    relation: Relation,
                    metadata: Optional[RelationMetadata] = None,
                    confidence: Optional[float] = None,
                    evidence: Optional[str] = None) -> None:
        """
        Add a directed relationship between two concepts.
        
        Args:
            source: The source concept
            target: The target concept
            relation: The type of relationship
            metadata: Optional metadata about this relationship
            confidence: Confidence score for this relationship (0.0 to 1.0)
            evidence: Evidence supporting this relationship (e.g., source text)
        """
        if metadata is None:
            metadata = RelationMetadata(relation_type=relation)
        
        # Update metadata with confidence and evidence if provided
        if confidence is not None:
            # Convert confidence to alpha/beta parameters
            # For beta=1, alpha = confidence/(1-confidence) gives belief=confidence
            if confidence >= 0.99:  # Avoid division by zero
                metadata.alpha = 99.0
                metadata.beta = 1.0
            elif confidence <= 0.01:
                metadata.alpha = 1.0
                metadata.beta = 99.0
            else:
                metadata.alpha = confidence / (1 - confidence)
                metadata.beta = 1.0
        if evidence is not None:
            if evidence not in metadata.evidence_patterns:
                metadata.evidence_patterns.append(evidence)
        
        # Ensure both concepts exist (but don't overwrite existing metadata)
        if source not in self.graph:
            self.add_concept(source)
        if target not in self.graph:
            self.add_concept(target)
        
        # Check if this exact relationship already exists
        existing_edges = self.graph.get_edge_data(source, target)
        if existing_edges:
            # Check if we already have this exact relation type
            for key, edge_data in existing_edges.items():
                if edge_data['label'] == relation:
                    # Update existing relationship if new evidence or higher belief
                    current_belief = edge_data['metadata'].belief
                    if confidence and confidence > current_belief:
                        # Update alpha/beta with new evidence
                        # Add pseudo-counts based on confidence
                        if confidence > 0.5:
                            edge_data['metadata'].alpha += confidence
                            edge_data['metadata'].beta += 1 - confidence
                        else:
                            edge_data['metadata'].alpha += confidence
                            edge_data['metadata'].beta += 1 - confidence
                        edge_data['confidence'] = edge_data['metadata'].belief
                    if evidence and evidence not in edge_data['metadata'].evidence_patterns:
                        edge_data['metadata'].evidence_patterns.append(evidence)
                        edge_data['evidence'] = evidence
                    return  # Don't add duplicate
        
        self.graph.add_edge(source, target, 
                           label=relation,
                           metadata=metadata,
                           confidence=metadata.belief,
                           evidence=evidence or "code_pattern")
        self._stats['relations_added'] += 1
        self._stats['last_modified'] = datetime.now()
    
    def get_concepts(self) -> List[Concept]:
        """Get all concepts in the graph."""
        return [Concept(node) for node in self.graph.nodes()]
    
    def get_concept_metadata(self, concept: Union[Concept, str]) -> Optional[ConceptMetadata]:
        """Get metadata for a specific concept."""
        # Handle string input for backward compatibility
        if isinstance(concept, str):
            concept = Concept(concept)
        if concept in self.graph:
            return self.graph.nodes[concept].get('metadata')
        return None
    
    def get_relations(self, concept: Concept) -> List[Tuple[Concept, Concept, Relation]]:
        """
        Get all relationships involving a concept.
        
        Returns:
            List of (source, target, relation) tuples
        """
        relations = []
        
        # Outgoing relations
        for target in self.graph.successors(concept):
            for data in self.graph.get_edge_data(concept, target).values():
                relations.append((concept, Concept(target), 
                                Relation(data['label'])))
        
        # Incoming relations
        for source in self.graph.predecessors(concept):
            for data in self.graph.get_edge_data(source, concept).values():
                relations.append((Concept(source), concept,
                                Relation(data['label'])))
        
        return relations
    
    def get_relations_with_confidence(self, concept) -> List[Dict[str, Any]]:
        """
        Get all relationships involving a concept with confidence and evidence.
        
        Returns:
            List of dictionaries containing relationship details
        """
        # Handle both string and Concept inputs
        if isinstance(concept, str):
            concept = Concept(concept)
            
        relations = []
        
        # Outgoing relations
        for target in self.graph.successors(concept):
            for data in self.graph.get_edge_data(concept, target).values():
                relations.append({
                    'source': concept,
                    'target': Concept(target),
                    'relation': Relation(data['label']),
                    'confidence': data['metadata'].belief if 'metadata' in data and data['metadata'] else 0.5,
                    'evidence': data.get('evidence', 'code_pattern'),
                    'metadata': data.get('metadata')
                })
        
        # Incoming relations
        for source in self.graph.predecessors(concept):
            for data in self.graph.get_edge_data(source, concept).values():
                relations.append({
                    'source': Concept(source),
                    'target': concept,
                    'relation': Relation(data['label']),
                    'confidence': data['metadata'].belief if 'metadata' in data and data['metadata'] else 0.5,
                    'evidence': data.get('evidence', 'code_pattern'),
                    'metadata': data.get('metadata')
                })
        
        return relations
    
    def find_related_concepts(self, concept: Concept, 
                            relation_type: Optional[str] = None) -> List[Concept]:
        """
        Find concepts related to the given concept.
        
        Args:
            concept: The concept to search from
            relation_type: Optional filter for specific relation types
            
        Returns:
            List of related concepts
        """
        related = []
        
        if concept not in self.graph:
            return related
        
        # Check outgoing edges
        for target in self.graph.successors(concept):
            for data in self.graph.get_edge_data(concept, target).values():
                if relation_type is None or data['label'] == relation_type:
                    related.append(Concept(target))
        
        return related
    
    def get_concept_hierarchy(self, root: Concept) -> Dict[Concept, List[Concept]]:
        """
        Get the hierarchy of concepts starting from a root.
        
        Useful for understanding inheritance or composition relationships.
        """
        hierarchy = {}
        
        def traverse(concept: Concept, visited: Set[Concept]):
            if concept in visited:
                return
            visited.add(concept)
            
            children = self.find_related_concepts(concept, "IS_A")
            if children:
                hierarchy[concept] = children
                for child in children:
                    traverse(child, visited)
        
        traverse(root, set())
        return hierarchy
    
    def merge_concepts(self, concept1: Concept, concept2: Concept,
                      merged_name: Concept) -> None:
        """
        Merge two concepts that represent the same real-world entity.
        
        This is useful when the same concept is discovered through
        different patterns (e.g., "User" and "Account" might be the same).
        """
        # Create merged concept with combined metadata
        metadata1 = self.get_concept_metadata(concept1)
        metadata2 = self.get_concept_metadata(concept2)
        
        # If merged_name already exists, update its metadata
        existing_metadata = self.get_concept_metadata(merged_name)
        
        if existing_metadata and metadata1 and metadata2:
            # Update existing concept's metadata
            # Only add functions from concept2 if merging into concept1
            if merged_name == concept1:
                existing_metadata.source_functions.extend(metadata2.source_functions)
                existing_metadata.source_files.update(metadata2.source_files)
                existing_metadata.related_behaviors.update(metadata2.related_behaviors)
                # Update beliefs by adding evidence from concept2
                existing_metadata.alpha += metadata2.alpha - 1  # Subtract prior
                existing_metadata.beta += metadata2.beta - 1
            elif merged_name == concept2:
                existing_metadata.source_functions.extend(metadata1.source_functions)
                existing_metadata.source_files.update(metadata1.source_files)
                existing_metadata.related_behaviors.update(metadata1.related_behaviors)
                # Update beliefs by adding evidence from concept1
                existing_metadata.alpha += metadata1.alpha - 1  # Subtract prior
                existing_metadata.beta += metadata1.beta - 1
            else:
                # Merging into a different concept - add both
                existing_metadata.source_functions.extend(metadata1.source_functions)
                existing_metadata.source_functions.extend(metadata2.source_functions)
                existing_metadata.source_files.update(metadata1.source_files)
                existing_metadata.source_files.update(metadata2.source_files)
                existing_metadata.related_behaviors.update(metadata1.related_behaviors)
                existing_metadata.related_behaviors.update(metadata2.related_behaviors)
                # Update beliefs by summing evidence
                existing_metadata.alpha += metadata1.alpha + metadata2.alpha - 2  # Subtract priors
                existing_metadata.beta += metadata1.beta + metadata2.beta - 2
        else:
            # Create new merged metadata
            merged_metadata = ConceptMetadata()
            if metadata1 and metadata2:
                # Combine source information
                merged_metadata.source_functions = (
                    metadata1.source_functions + metadata2.source_functions
                )
                merged_metadata.source_files = metadata1.source_files | metadata2.source_files
                merged_metadata.related_behaviors = (
                    metadata1.related_behaviors | metadata2.related_behaviors
                )
                # Combine beliefs by summing evidence
                merged_metadata.alpha = metadata1.alpha + metadata2.alpha - 1  # Subtract 1 to avoid double-counting prior
                merged_metadata.beta = metadata1.beta + metadata2.beta - 1
            
            self.add_concept(merged_name, merged_metadata)
        
        # Transfer all relationships
        for source, target, relation in self.get_relations(concept1):
            if source == concept1:
                self.add_relation(merged_name, target, relation)
            else:
                self.add_relation(source, merged_name, relation)
        
        for source, target, relation in self.get_relations(concept2):
            if source == concept2:
                self.add_relation(merged_name, target, relation)
            else:
                self.add_relation(source, merged_name, relation)
        
        # Remove old concepts (but not if they're the same as merged_name)
        if concept1 != merged_name:
            self.graph.remove_node(concept1)
        if concept2 != merged_name:
            self.graph.remove_node(concept2)
    
    def to_json(self) -> str:
        """
        Export the knowledge graph to JSON format.
        
        Useful for persistence and visualization.
        """
        data = {
            'concepts': {},
            'relations': [],
            'stats': self._stats
        }
        
        # Export concepts
        for concept in self.get_concepts():
            metadata = self.get_concept_metadata(concept)
            data['concepts'][concept] = metadata.to_dict() if metadata else {}
        
        # Convert stats datetime to string
        stats_copy = self._stats.copy()
        stats_copy['last_modified'] = stats_copy['last_modified'].isoformat()
        data['stats'] = stats_copy
        
        # Export relations
        for source, target, edge_data in self.graph.edges(data=True):
            relation_data = {
                'source': source,
                'target': target,
                'relation': edge_data['label']
            }
            if 'metadata' in edge_data:
                relation_data['metadata'] = edge_data['metadata'].to_dict()
            data['relations'].append(relation_data)
        
        # Remove the incorrect stats assignment
        data.pop('stats', None)
        data['stats'] = stats_copy
        
        return json.dumps(data, indent=2)
    
    def from_json(self, json_str: str) -> None:
        """
        Import a knowledge graph from JSON format.
        
        Args:
            json_str: JSON string representation of the graph
        """
        data = json.loads(json_str)
        
        # Clear existing graph
        self.graph.clear()
        
        # Import concepts
        for concept_name, metadata_dict in data['concepts'].items():
            metadata = ConceptMetadata()
            # Populate metadata from dict
            if metadata_dict:
                metadata.discovery_method = metadata_dict.get('discovery_method', '')
                # Handle both old confidence format and new alpha/beta format
                if 'alpha' in metadata_dict and 'beta' in metadata_dict:
                    metadata.alpha = metadata_dict['alpha']
                    metadata.beta = metadata_dict['beta']
                elif 'confidence' in metadata_dict:
                    # Legacy support: convert confidence to alpha/beta
                    conf = metadata_dict['confidence']
                    if conf >= 0.99:
                        metadata.alpha = 99.0
                        metadata.beta = 1.0
                    elif conf <= 0.01:
                        metadata.alpha = 1.0
                        metadata.beta = 99.0
                    else:
                        metadata.alpha = conf / (1 - conf)
                        metadata.beta = 1.0
                metadata.source_functions = metadata_dict.get('source_functions', [])
                metadata.source_files = set(metadata_dict.get('source_files', []))
                metadata.related_behaviors = set(metadata_dict.get('related_behaviors', []))
                metadata.docstring_mentions = metadata_dict.get('docstring_mentions', [])
                metadata.properties = metadata_dict.get('properties', {})
            
            self.add_concept(Concept(concept_name), metadata)
        
        # Import relations
        for relation_dict in data['relations']:
            metadata = None
            if 'metadata' in relation_dict:
                meta_dict = relation_dict['metadata']
                metadata = RelationMetadata(
                    relation_type=meta_dict.get('relation_type', '')
                )
                # Handle both old confidence format and new alpha/beta format
                if 'alpha' in meta_dict and 'beta' in meta_dict:
                    metadata.alpha = meta_dict['alpha']
                    metadata.beta = meta_dict['beta']
                elif 'confidence' in meta_dict:
                    # Legacy support: convert confidence to alpha/beta
                    conf = meta_dict['confidence']
                    if conf >= 0.99:
                        metadata.alpha = 99.0
                        metadata.beta = 1.0
                    elif conf <= 0.01:
                        metadata.alpha = 1.0
                        metadata.beta = 99.0
                    else:
                        metadata.alpha = conf / (1 - conf)
                        metadata.beta = 1.0
                metadata.evidence_functions = meta_dict.get('evidence_functions', [])
                metadata.evidence_patterns = meta_dict.get('evidence_patterns', [])
            
            self.add_relation(
                Concept(relation_dict['source']),
                Concept(relation_dict['target']),
                Relation(relation_dict['relation']),
                metadata
            )
        
        # Restore stats
        if 'stats' in data:
            self._stats = data['stats']
    
    def visualize(self) -> str:
        """
        Generate a simple text visualization of the graph.
        
        Returns:
            String representation suitable for console output
        """
        lines = ["Knowledge Graph Summary:"]
        lines.append(f"  Concepts: {len(self.graph.nodes())}")
        lines.append(f"  Relations: {len(self.graph.edges())}")
        lines.append("")
        
        # Show concepts with their relationships
        for concept in sorted(self.get_concepts()):
            lines.append(f"Concept: {concept}")
            
            # Show metadata
            metadata = self.get_concept_metadata(concept)
            if metadata:
                lines.append(f"  Discovery: {metadata.discovery_method}")
                lines.append(f"  Belief: {metadata.belief:.2f} (α={metadata.alpha:.1f}, β={metadata.beta:.1f})")
                if metadata.source_functions:
                    lines.append(f"  Sources: {', '.join(metadata.source_functions[:3])}...")
            
            # Show relationships
            relations = self.get_relations(concept)
            if relations:
                lines.append("  Relations:")
                for source, target, relation in relations[:5]:  # Limit to 5
                    if source == concept:
                        lines.append(f"    -> {relation} -> {target}")
                    else:
                        lines.append(f"    <- {relation} <- {source}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def __len__(self) -> int:
        """Return the number of concepts in the graph."""
        return len(self.graph.nodes())
    
    def merge_from_subgraph(self, subgraph: 'WorldKnowledgeGraph') -> None:
        """
        Intelligently merge a subgraph (from parallel worker) into this graph.
        
        This method is designed for parallel knowledge graph construction where
        each worker creates a micro-graph for a single function. It handles:
        - Merging concepts with the same ID
        - Combining metadata (source functions, confidence scores)
        - Adding new relationships without duplicates
        
        Args:
            subgraph: A WorldKnowledgeGraph containing discoveries from one function
        """
        # Merge concepts
        for concept in subgraph.get_concepts():
            sub_metadata = subgraph.get_concept_metadata(concept)
            
            if concept in self:
                # Concept already exists - merge metadata
                existing_metadata = self.get_concept_metadata(concept)
                if existing_metadata and sub_metadata:
                    # Extend source functions (avoiding duplicates)
                    existing_sources = set(existing_metadata.source_functions)
                    new_sources = set(sub_metadata.source_functions)
                    existing_metadata.source_functions = list(existing_sources | new_sources)
                    
                    # Merge source files
                    existing_metadata.source_files.update(sub_metadata.source_files)
                    
                    # Merge related behaviors
                    existing_metadata.related_behaviors.update(sub_metadata.related_behaviors)
                    
                    # Update confidence using Bayesian combination
                    # New evidence increases our belief
                    existing_metadata.alpha += sub_metadata.alpha - 1  # Remove prior
                    existing_metadata.beta += sub_metadata.beta - 1
                    
                    # Take highest confidence discovery method
                    if sub_metadata.confidence > existing_metadata.confidence:
                        existing_metadata.discovery_method = sub_metadata.discovery_method
                        existing_metadata.confidence = sub_metadata.confidence
            else:
                # New concept - add it directly
                self.add_concept(concept, sub_metadata)
        
        # Merge relationships
        for source, target, edge_data in subgraph.graph.edges(data=True):
            # Check if relationship already exists
            existing_edges = []
            if source in self and target in self:
                try:
                    existing_edges = self.graph[source][target]
                except KeyError:
                    pass
            
            # Only add if this exact relationship doesn't exist
            relation_exists = False
            for key, data in existing_edges.items():
                if data.get('label') == edge_data.get('label'):
                    # Relationship exists - could update confidence here
                    relation_exists = True
                    break
            
            if not relation_exists:
                # Add the new relationship
                self.add_relation(
                    source, 
                    target, 
                    edge_data.get('label'),
                    metadata=edge_data.get('metadata'),
                    confidence=edge_data.get('confidence', 0.5),
                    evidence=edge_data.get('evidence', '')
                )
    
    def __contains__(self, concept: Concept) -> bool:
        """Check if a concept exists in the graph."""
        return concept in self.graph
    
    def learn_mapping(self, word: str, concept: Concept, probability: float) -> None:
        """
        Learn a new word-to-concept mapping from successful pronoun resolution.
        
        This method is called when a pronoun is successfully resolved to a concept
        with high confidence. It creates or updates a mapping between the word
        (e.g., "they") and the resolved concept (e.g., "Every_Student").
        
        Args:
            word: The word that was resolved (typically a pronoun)
            concept: The concept it was resolved to
            probability: The confidence/probability of this resolution
        """
        # Create a concept representing the word
        word_concept = Concept(f"word:{word}")
        
        # Add the word concept if it doesn't exist
        if word_concept not in self.graph:
            word_metadata = ConceptMetadata(
                discovery_method="pronoun_resolution_learning",
                properties={"word_type": "pronoun", "original_word": word}
            )
            self.add_concept(word_concept, word_metadata)
        
        # Create or update the relationship
        relation_metadata = RelationMetadata(
            relation_type="REFERS_TO",
            evidence_patterns=[f"Resolved '{word}' to '{concept}' with p={probability:.2f}"]
        )
        
        # Convert probability to alpha/beta for the relationship
        if probability >= 0.99:
            relation_metadata.alpha = 99.0
            relation_metadata.beta = 1.0
        elif probability <= 0.01:
            relation_metadata.alpha = 1.0
            relation_metadata.beta = 99.0
        else:
            relation_metadata.alpha = probability / (1 - probability)
            relation_metadata.beta = 1.0
        
        # Add the relationship
        self.add_relation(
            source=word_concept,
            target=concept,
            relation=Relation("REFERS_TO"),
            metadata=relation_metadata,
            confidence=probability,
            evidence=f"Learned from pronoun resolution"
        )
    
    def __str__(self) -> str:
        """String representation of the graph."""
        return f"WorldKnowledgeGraph({len(self.graph.nodes())} concepts, {len(self.graph.edges())} relationships)"


# Backward compatibility alias
KnowledgeGraph = WorldKnowledgeGraph