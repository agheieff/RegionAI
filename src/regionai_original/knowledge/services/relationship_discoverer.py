"""
Relationship discovery service.

This module orchestrates the discovery of relationships from natural language text,
coordinating pattern matching and evidence tracking.
"""
import re
from typing import List, Dict
from dataclasses import dataclass
import logging

from ..graph import KnowledgeGraph, Concept, Relation, RelationMetadata
from ..bayesian_updater import BayesianUpdater
from .pattern_matcher import RelationshipPatternMatcher, RelationshipMatch
from .concept_variations import ConceptVariationBuilder
from ...config import RegionAIConfig, DEFAULT_CONFIG


@dataclass
class DiscoveredRelationship:
    """Tracks a discovered relationship with its evidence."""
    source: Concept
    target: Concept
    relation: str
    confidence: float
    evidence: str
    source_function: str
    metadata: RelationMetadata


class RelationshipDiscoverer:
    """
    Service for discovering relationships from text.
    
    This class extracts the relationship discovery logic from KnowledgeLinker,
    focusing on finding and tracking relationships between concepts.
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph, bayesian_updater: BayesianUpdater,
                 config: RegionAIConfig = None):
        """
        Initialize the relationship discoverer.
        
        Args:
            knowledge_graph: The knowledge graph to update
            bayesian_updater: Service for updating beliefs
            config: Configuration object
        """
        self.knowledge_graph = knowledge_graph
        self.bayesian_updater = bayesian_updater
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Build concept variations
        self.variation_builder = ConceptVariationBuilder()
        self.concept_variations = self.variation_builder.build_variations(
            set(self.knowledge_graph.get_concepts())
        )
        
        # Initialize pattern matcher
        self.pattern_matcher = RelationshipPatternMatcher(self.concept_variations, self.config)
        
        # Track discovered relationships for reporting
        self._discovered_relationships: List[DiscoveredRelationship] = []
    
    def discover_from_text(self, text: str, source_function: str, base_confidence: float):
        """
        Discover relationships from a piece of text.
        
        Args:
            text: The text to analyze
            source_function: Function where this text was found
            base_confidence: Base confidence score from documentation quality
        """
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # Find all concepts mentioned in this sentence
            concepts_in_sentence = self.variation_builder.find_concepts_in_sentence(
                sentence, self.concept_variations
            )
            
            if len(concepts_in_sentence) >= 2:
                # Try to identify relationships between the concepts
                matches = self.pattern_matcher.find_relationships(
                    sentence, concepts_in_sentence, source_function, base_confidence
                )
                
                # Add each match to the knowledge graph
                for match in matches:
                    self._add_relationship(match)
    
    def extract_concepts_from_text(self, text: str, evidence_type: str, source_credibility: float):
        """
        Extract concepts from natural language text and update beliefs.
        
        Args:
            text: The text to analyze
            evidence_type: Type of evidence for Bayesian update
            source_credibility: Credibility of the source
        """
        all_extracted_concepts = []
        
        # Split text into sentences for better processing
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            sentence_concepts = []
            
            # Find concepts in the sentence using variations
            concepts_found = self.variation_builder.find_concepts_in_sentence(
                sentence, self.concept_variations
            )
            
            for concept, _, _ in concepts_found:
                # Update belief for existing concept
                self.bayesian_updater.update_concept_belief(
                    concept,
                    evidence_type,
                    source_credibility
                )
                sentence_concepts.append(str(concept))
            
            # Process co-occurrences within each sentence
            if len(sentence_concepts) >= 2:
                self._process_concept_cooccurrences(
                    sentence_concepts,
                    evidence_type.replace('mention', 'co_occurrence'),
                    source_credibility
                )
            
            all_extracted_concepts.extend(sentence_concepts)
        
        return all_extracted_concepts
    
    def update_concept_set(self, new_concept: Concept):
        """
        Update the concept set when a new concept is discovered.
        
        Args:
            new_concept: The newly discovered concept
        """
        current_concepts = set(self.knowledge_graph.get_concepts())
        current_concepts.add(new_concept)
        self.concept_variations = self.variation_builder.build_variations(current_concepts)
        self.pattern_matcher.concept_variations = self.concept_variations
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for analysis."""
        # Simple sentence splitting - preserve sentence endings for evidence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Normalize whitespace in each sentence
        return [' '.join(s.strip().split()) for s in sentences if s.strip()]
    
    def _add_relationship(self, match: RelationshipMatch):
        """Add a discovered relationship to the knowledge graph."""
        # Create metadata with Bayesian belief parameters
        # Convert confidence to alpha/beta: for beta=1, alpha = confidence/(1-confidence)
        if match.confidence >= 0.99:
            alpha = 99.0
            beta = 1.0
        elif match.confidence <= 0.01:
            alpha = 1.0
            beta = 99.0
        else:
            alpha = match.confidence / (1 - match.confidence)
            beta = 1.0
        
        metadata = RelationMetadata(
            relation_type=match.relationship_type,
            alpha=alpha,
            beta=beta,
            evidence_functions=[match.source_function],
            evidence_patterns=[match.evidence]
        )
        
        # Add to graph
        self.knowledge_graph.add_relation(
            match.source_concept,
            match.target_concept,
            Relation(match.relationship_type),
            metadata=metadata,
            confidence=match.confidence,
            evidence=match.evidence
        )
        
        # Track for reporting
        self._discovered_relationships.append(DiscoveredRelationship(
            source=match.source_concept,
            target=match.target_concept,
            relation=match.relationship_type,
            confidence=match.confidence,
            evidence=match.evidence,
            source_function=match.source_function,
            metadata=metadata
        ))
    
    def _process_concept_cooccurrences(self, concepts: List[str], evidence_type: str,
                                     source_credibility: float):
        """
        Process co-occurrences between concepts found in the same context.
        
        Args:
            concepts: List of concept names found together
            evidence_type: Type of co-occurrence evidence
            source_credibility: Credibility of the source
        """
        # Generate all unique pairs of concepts
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Skip if same concept
                if concept1.lower() == concept2.lower():
                    continue
                
                # Update relationship belief
                self.bayesian_updater.update_relationship_belief(
                    concept1,
                    concept2,
                    evidence_type,
                    source_credibility
                )
    
    def get_discovered_relationships(self) -> List[Dict[str, any]]:
        """Get list of all discovered relationships for reporting."""
        return [
            {
                'source': rel.source,
                'target': rel.target,
                'relation': rel.relation,
                'confidence': rel.confidence,
                'evidence': rel.evidence,
                'source_function': rel.source_function
            }
            for rel in self._discovered_relationships
        ]