"""
Knowledge Linker service for enriching Knowledge Graphs with natural language evidence.

This module reads documentation and identifies relationships between concepts
described in text, adding them to the Knowledge Graph with confidence scores
and evidence tracking. This is the bridge from deterministic code analysis
to probabilistic belief formation.
"""
from typing import List, Dict
from collections import defaultdict
import logging

from ..domains.code.semantic.db import SemanticDB
from ..domains.code.semantic.fingerprint import DocumentationQuality
from .hub import KnowledgeHub
from .graph import Concept, WorldKnowledgeGraph
from .bayesian_updater import BayesianUpdater
from ..domains.language import nlp_utils
from ..utils.component_loader import get_nlp_model
from ..config import RegionAIConfig, DEFAULT_CONFIG

# Import refactored services
from .services import (
    RelationshipDiscoverer,
    ActionCoordinator,
    GrammarExtractor
)


class KnowledgeLinker:
    """
    Enriches a WorldKnowledgeGraph by finding relationships described in the
    natural language documentation of a SemanticDB.
    
    This refactored version delegates to focused services for better
    separation of concerns and testability.
    """
    
    def __init__(self, semantic_db: SemanticDB, knowledge_hub: KnowledgeHub, config: RegionAIConfig = None):
        """
        Initialize the Knowledge Linker.
        
        Args:
            semantic_db: Database containing analyzed code with documentation
            knowledge_hub: Hub containing both world and reasoning knowledge graphs
            config: Configuration object
        """
        self.db = semantic_db
        self.knowledge_hub = knowledge_hub
        # For backward compatibility, keep reference to world knowledge graph
        self.knowledge_graph = knowledge_hub.wkg
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Initialize Bayesian updater for belief updates
        self.bayesian_updater = BayesianUpdater(self.knowledge_graph, self.config)
        
        # Get the cached NLP model
        self.nlp_model = get_nlp_model()
        if self.nlp_model is None:
            self.logger.warning("spaCy model not found. Using basic extraction.")
        
        # Initialize focused services
        self.relationship_discoverer = RelationshipDiscoverer(
            self.knowledge_graph, self.bayesian_updater, self.config
        )
        self.action_coordinator = ActionCoordinator(self.bayesian_updater, self.config)
        self.grammar_extractor = GrammarExtractor(self.nlp_model, self.config) if self.nlp_model else None
    
    
    def enrich_graph(self) -> WorldKnowledgeGraph:
        """
        Scans all docstrings for sentences that link known concepts and adds
        them to the WorldKnowledgeGraph as new, evidence-based relationships.
        
        Returns:
            The enriched WorldKnowledgeGraph
        """
        # Process all documented entries in the semantic database
        for entry in self.db.find_training_candidates():
            if entry.documented_fingerprint:
                self._process_documentation(entry)
        
        # Log statistics from all services
        rel_count = len(self.relationship_discoverer.get_discovered_relationships())
        action_count = len(self.action_coordinator.get_discovered_actions())
        
        self.logger.info(f"Discovered {rel_count} relationships and {action_count} actions from text")
        return self.knowledge_graph
    
    def _process_documentation(self, entry):
        """Process documentation from a single semantic entry."""
        doc_fingerprint = entry.documented_fingerprint
        nl_context = doc_fingerprint.nl_context
        
        # Calculate base confidence from documentation quality
        quality_score = DocumentationQuality.score_documentation(nl_context)
        
        # Extract concepts from function name
        self._process_function_name(entry.function_name, quality_score)
        
        # Process docstring and comments
        text_content = self._process_text_sources(nl_context, entry.function_name, quality_score)
        
        # Extract grammatical patterns
        self._extract_grammatical_patterns(text_content, entry.function_name, quality_score)
        
        # Discover actions from code
        self._discover_code_actions(entry, quality_score)
    
    def _process_function_name(self, function_name: str, quality_score: float):
        """Extract concepts from the function name."""
        self._extract_concepts_from_identifier(
            function_name,
            'function_name_mention',
            quality_score
        )
    
    def _process_text_sources(self, nl_context, function_name: str, quality_score: float) -> List[str]:
        """Process docstring and comments, returning all text content."""
        text_content = []
        
        # Process docstring
        if nl_context.docstring:
            text_content.append(nl_context.docstring)
            self._process_docstring(nl_context.docstring, function_name, quality_score)
        
        # Process comments
        if nl_context.comments:
            text_content.extend(nl_context.comments)
            self._process_comments(nl_context.comments, function_name, quality_score)
        
        return text_content
    
    def _process_docstring(self, docstring: str, function_name: str, quality_score: float):
        """Process docstring for concepts and relationships."""
        # Extract concepts
        self.relationship_discoverer.extract_concepts_from_text(
            docstring,
            'docstring_mention',
            quality_score
        )
        
        # Discover relationships
        self.relationship_discoverer.discover_from_text(
            docstring,
            function_name,
            quality_score
        )
    
    def _process_comments(self, comments: List[str], function_name: str, quality_score: float):
        """Process comments for concepts and relationships."""
        comment_quality = quality_score * self.config.comment_confidence_multiplier
        
        for comment in comments:
            # Extract concepts
            self.relationship_discoverer.extract_concepts_from_text(
                comment,
                'comment_mention',
                comment_quality
            )
            
            # Discover relationships
            self.relationship_discoverer.discover_from_text(
                comment,
                function_name,
                quality_score
            )
    
    def _extract_grammatical_patterns(self, text_content: List[str], function_name: str, quality_score: float):
        """Extract grammatical patterns from all text content."""
        if self.grammar_extractor and text_content:
            all_text = ' '.join(text_content)
            self.grammar_extractor.extract_patterns_from_text(
                all_text,
                function_name,
                quality_score
            )
    
    def _discover_code_actions(self, entry, quality_score: float):
        """Discover actions from the function's source code."""
        if hasattr(entry, 'source_code') and entry.source_code:
            self.action_coordinator.discover_actions_from_code(
                entry.source_code,
                entry.function_name,
                quality_score
            )
    
    
    def generate_enrichment_report(self) -> str:
        """
        Generate a human-readable report of discovered relationships.
        
        Returns:
            Formatted report string
        """
        lines = ["Knowledge Graph Enrichment Report", "=" * 50, ""]
        
        discovered_relationships = self.relationship_discoverer.get_discovered_relationships()
        
        if not discovered_relationships:
            lines.append("No new relationships discovered from documentation.")
            return "\n".join(lines)
        
        lines.append(f"Discovered {len(discovered_relationships)} relationships from text:")
        lines.append("")
        
        # Group by relationship type
        by_type = defaultdict(list)
        for rel in discovered_relationships:
            by_type[rel['relation']].append(rel)
        
        for rel_type, relationships in sorted(by_type.items()):
            lines.append(f"{rel_type} Relationships ({len(relationships)}):")
            
            for rel in sorted(relationships, key=lambda r: r['confidence'], reverse=True)[:5]:
                lines.append(f"  {rel['source']} -> {rel['target']}")
                lines.append(f"    Confidence: {rel['confidence']:.2f}")
                lines.append(f"    Evidence: \"{rel['evidence'][:80]}...\"")
                lines.append(f"    Source: {rel['source_function']}")
                lines.append("")
            
            if len(relationships) > 5:
                lines.append(f"  ... and {len(relationships) - 5} more")
            lines.append("")
        
        # Add action sequences if any
        sequences = self.action_coordinator.get_discovered_sequences()
        if sequences:
            lines.append(f"Action Sequences ({len(sequences)}):")
            for seq in sequences[:5]:
                lines.append(f"  {seq['action1']} -> {seq['action2']}")
                lines.append(f"    Confidence: {seq['confidence']:.2f}")
                lines.append(f"    Source: {seq['source_function']}")
                lines.append("")
            if len(sequences) > 5:
                lines.append(f"  ... and {len(sequences) - 5} more")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_discovered_relationships(self) -> List[Dict[str, any]]:
        """Get list of all discovered relationships."""
        # Combine relationships from all sources
        relationships = self.relationship_discoverer.get_discovered_relationships()
        
        # Add action sequences as PRECEDES relationships
        for seq in self.action_coordinator.get_discovered_sequences():
            relationships.append({
                'source': seq['action1'].title(),
                'target': seq['action2'].title(),
                'relation': 'PRECEDES',
                'confidence': seq['confidence'],
                'evidence': seq['evidence'],
                'source_function': seq['source_function']
            })
        
        return relationships
    
    def _extract_concepts_from_identifier(self, identifier: str, evidence_type: str, 
                                        source_credibility: float):
        """
        Extract concepts from a code identifier and update beliefs.
        
        Args:
            identifier: The identifier to analyze (e.g., function name)
            evidence_type: Type of evidence for Bayesian update
            source_credibility: Credibility of the source
        """
        extracted_concepts = []
        
        if self.nlp_model:
            # Use NLP to extract nouns
            nouns = nlp_utils.extract_nouns_from_identifier(identifier, self.nlp_model)
            
            for noun in nouns:
                # Create concept if it doesn't exist
                concept = Concept(noun.title())
                extracted_concepts.append(noun.title())
                
                # Update belief using Bayesian updater
                self.bayesian_updater.update_concept_belief(
                    concept,
                    evidence_type,
                    source_credibility
                )
                
                # Update concept set in relationship discoverer if new
                if concept not in self.knowledge_graph.get_concepts():
                    self.relationship_discoverer.update_concept_set(concept)
        
        # Process co-occurrences if multiple concepts found
        if len(extracted_concepts) >= 2:
            self.relationship_discoverer._process_concept_cooccurrences(
                extracted_concepts,
                evidence_type.replace('mention', 'co_occurrence'),
                source_credibility
            )
        
        return extracted_concepts
    
    
    def get_discovered_actions(self) -> List[Dict[str, any]]:
        """Get list of all discovered actions."""
        return self.action_coordinator.get_discovered_actions()
    
    def get_discovered_patterns(self) -> List[Dict[str, any]]:
        """Get list of all discovered grammatical patterns."""
        return self.grammar_extractor.get_discovered_patterns() if self.grammar_extractor else []
