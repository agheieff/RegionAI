"""
Core Knowledge Graph data structures for representing real-world concepts.

This module provides the foundation for RegionAI's Common Sense Engine,
enabling it to build and reason about a structured model of reality
based on the code it analyzes.
"""
from typing import Any, Dict, List, Optional, Set, Tuple, NewType
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
    confidence: float = 1.0  # 0.0 to 1.0
    
    # Source information
    source_functions: List[str] = field(default_factory=list)
    source_files: Set[str] = field(default_factory=set)
    
    # Semantic information
    related_behaviors: Set[str] = field(default_factory=set)  # Behavior names
    docstring_mentions: List[str] = field(default_factory=list)
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'discovered_at': self.discovered_at.isoformat(),
            'discovery_method': self.discovery_method,
            'confidence': self.confidence,
            'source_functions': self.source_functions,
            'source_files': list(self.source_files),
            'related_behaviors': list(self.related_behaviors),
            'docstring_mentions': self.docstring_mentions,
            'properties': self.properties
        }


@dataclass
class RelationMetadata:
    """
    Metadata for relationships between concepts.
    
    Captures not just that two concepts are related, but how we know
    they're related based on code analysis.
    """
    relation_type: str  # e.g., "HAS_ONE", "HAS_MANY", "BELONGS_TO"
    discovered_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    
    # Evidence for this relationship
    evidence_functions: List[str] = field(default_factory=list)
    evidence_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'relation_type': self.relation_type,
            'discovered_at': self.discovered_at.isoformat(),
            'confidence': self.confidence,
            'evidence_functions': self.evidence_functions,
            'evidence_patterns': self.evidence_patterns
        }


class KnowledgeGraph:
    """
    A graph representing real-world concepts and their relationships.
    
    This is the core data structure of RegionAI's Common Sense Engine.
    It builds a model of reality by analyzing how code manipulates
    real-world entities.
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
        if metadata is None:
            metadata = ConceptMetadata()
        
        self.graph.add_node(concept, metadata=metadata)
        self._stats['concepts_added'] += 1
        self._stats['last_modified'] = datetime.now()
    
    def add_relation(self, source: Concept, target: Concept, 
                    relation: Relation,
                    metadata: Optional[RelationMetadata] = None) -> None:
        """
        Add a directed relationship between two concepts.
        
        Args:
            source: The source concept
            target: The target concept
            relation: The type of relationship
            metadata: Optional metadata about this relationship
        """
        if metadata is None:
            metadata = RelationMetadata(relation_type=relation)
        
        # Ensure both concepts exist
        if source not in self.graph:
            self.add_concept(source)
        if target not in self.graph:
            self.add_concept(target)
        
        self.graph.add_edge(source, target, 
                           label=relation,
                           metadata=metadata)
        self._stats['relations_added'] += 1
        self._stats['last_modified'] = datetime.now()
    
    def get_concepts(self) -> List[Concept]:
        """Get all concepts in the graph."""
        return [Concept(node) for node in self.graph.nodes()]
    
    def get_concept_metadata(self, concept: Concept) -> Optional[ConceptMetadata]:
        """Get metadata for a specific concept."""
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
            merged_metadata.confidence = max(metadata1.confidence, metadata2.confidence)
        
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
                metadata.confidence = metadata_dict.get('confidence', 1.0)
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
                    relation_type=meta_dict.get('relation_type', ''),
                    confidence=meta_dict.get('confidence', 1.0)
                )
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
                lines.append(f"  Confidence: {metadata.confidence:.2f}")
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
    
    def __contains__(self, concept: Concept) -> bool:
        """Check if a concept exists in the graph."""
        return concept in self.graph
    
    def __str__(self) -> str:
        """String representation of the graph."""
        return f"KnowledgeGraph({len(self.graph.nodes())} concepts, {len(self.graph.edges())} relationships)"