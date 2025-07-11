"""
Knowledge Linker service for enriching Knowledge Graphs with natural language evidence.

This module reads documentation and identifies relationships between concepts
described in text, adding them to the Knowledge Graph with confidence scores
and evidence tracking. This is the bridge from deterministic code analysis
to probabilistic belief formation.
"""
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging

from ..semantic.db import SemanticDB
from ..semantic.fingerprint import DocumentationQuality
from .graph import KnowledgeGraph, Concept, Relation, RelationMetadata
from .bayesian_updater import BayesianUpdater
from ..language.nlp_extractor import NLPExtractor
from .action_discoverer import ActionDiscoverer


class RelationshipPattern:
    """Common patterns for identifying relationships in text."""
    
    # Patterns that indicate specific relationship types
    PATTERNS = {
        'HAS_ONE': [
            r'{source}\s+has\s+(?:a|an)\s+{target}',
            r'{source}\s+contains\s+(?:a|an)\s+{target}',
            r'{source}\s+includes\s+(?:a|an)\s+{target}',
            r'{source}\s+owns\s+(?:a|an)\s+{target}',
            r'each\s+{source}\s+has\s+(?:a|an)\s+{target}',
            r'{source}\s+has\s+one\s+{target}',
            r'each\s+{source}\s+has\s+one\s+{target}',
            r'{source}\s+has\s+exactly\s+one\s+{target}',
            r'each\s+{source}\s+has\s+exactly\s+one\s+{target}',
        ],
        'HAS_MANY': [
            r'{source}\s+has\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+contains?\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+contain\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}s?\s+contain\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+can\s+have\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+manages\s+{target}s?',
            r'{source}\s+tracks\s+{target}s?',
        ],
        'BELONGS_TO': [
            r'{source}s?\s+belong(?:s)?\s+to\s+(?:a|an|one)?\s*{target}s?',
            r'{source}\s+belongs\s+to\s+(?:a|an|exactly\s+one)?\s*{target}',
            r'{source}\s+is\s+owned\s+by\s+(?:a|an)?\s*{target}',
            r'{source}\s+is\s+part\s+of\s+(?:a|an)?\s*{target}',
            r'{source}\s+is\s+associated\s+with\s+(?:a|an)?\s*{target}',
            r'{target}\s+owns\s+(?:the\s+)?{source}',
            r'each\s+{source}\s+belongs\s+to\s+(?:a|an|exactly\s+one)?\s*{target}',
        ],
        'IS_A': [
            r'{source}\s+is\s+(?:a|an)\s+{target}',
            r'{source}\s+extends\s+{target}',
            r'{source}\s+inherits\s+from\s+{target}',
            r'{source}\s+is\s+a\s+type\s+of\s+{target}',
            r'{source}\s+is\s+a\s+kind\s+of\s+{target}',
        ],
        'USES': [
            r'{source}\s+uses\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+requires\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+depends\s+on\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+needs\s+(?:a|an|the)?\s*{target}',
        ],
        'CREATES': [
            r'{source}\s+creates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+generates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+produces?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+builds?\s+(?:a|an|the)?\s*{target}',
        ],
        'VALIDATES': [
            r'{source}\s+validates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+verifies?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+checks?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+ensures?\s+(?:a|an|the)?\s*{target}\s+is\s+valid',
        ]
    }


class KnowledgeLinker:
    """
    Enriches a KnowledgeGraph by finding relationships described in the
    natural language documentation of a SemanticDB.
    
    This is where RegionAI begins to form beliefs based on textual evidence,
    moving beyond deterministic code patterns to probabilistic understanding.
    """
    
    def __init__(self, semantic_db: SemanticDB, knowledge_graph: KnowledgeGraph):
        """
        Initialize the Knowledge Linker.
        
        Args:
            semantic_db: Database containing analyzed code with documentation
            knowledge_graph: Graph to enrich with discovered relationships
        """
        self.db = semantic_db
        self.knowledge_graph = knowledge_graph
        self.concepts = set(self.knowledge_graph.get_concepts())
        self.logger = logging.getLogger(__name__)
        
        # Initialize Bayesian updater for belief updates
        self.bayesian_updater = BayesianUpdater(knowledge_graph)
        
        # Initialize NLP extractor for intelligent concept extraction
        try:
            self.nlp_extractor = NLPExtractor()
        except OSError:
            self.logger.warning("spaCy model not found. Using basic extraction.")
            self.nlp_extractor = None
        
        # Initialize action discoverer for behavior understanding
        self.action_discoverer = ActionDiscoverer()
        
        # Track discovered relationships for reporting
        self._discovered_relationships: List[Dict[str, any]] = []
        
        # Track discovered actions for reporting
        self._discovered_actions: List[Dict[str, any]] = []
        
        # Build concept name variations for better matching
        self._concept_variations = self._build_concept_variations()
    
    def _build_concept_variations(self) -> Dict[str, Concept]:
        """
        Build a mapping of concept name variations to canonical concepts.
        
        Handles plurals, case variations, and common synonyms.
        """
        variations = {}
        
        for concept in self.concepts:
            concept_str = str(concept)
            
            # Original
            variations[concept_str.lower()] = concept
            
            # Plural/singular  
            if concept_str.endswith('y'):
                # Handle words ending in 'y' -> 'ies' (e.g., Category -> Categories)
                plural = concept_str[:-1] + 'ies'
                variations[plural.lower()] = concept
                # Also add capitalized version
                variations[plural] = concept
            elif concept_str.endswith('s'):
                # Already plural, add singular
                variations[concept_str[:-1].lower()] = concept
            else:
                # Add plural
                variations[(concept_str + 's').lower()] = concept
                # Also handle common pluralizations
                if concept_str.endswith('x') or concept_str.endswith('ch') or concept_str.endswith('sh'):
                    variations[(concept_str + 'es').lower()] = concept
            
            # With articles
            variations[f"a {concept_str.lower()}"] = concept
            variations[f"an {concept_str.lower()}"] = concept
            variations[f"the {concept_str.lower()}"] = concept
            
        return variations
    
    def enrich_graph(self) -> KnowledgeGraph:
        """
        Scans all docstrings for sentences that link known concepts and adds
        them to the KnowledgeGraph as new, evidence-based relationships.
        
        Returns:
            The enriched KnowledgeGraph
        """
        # Process all documented entries in the semantic database
        for entry in self.db.find_training_candidates():
            if entry.documented_fingerprint:
                self._process_documentation(entry)
        
        self.logger.info(f"Discovered {len(self._discovered_relationships)} relationships from text")
        return self.knowledge_graph
    
    def _process_documentation(self, entry):
        """Process documentation from a single semantic entry."""
        doc_fingerprint = entry.documented_fingerprint
        nl_context = doc_fingerprint.nl_context
        
        # Calculate base confidence from documentation quality
        quality_score = DocumentationQuality.score_documentation(nl_context)
        
        # Extract concepts from function name
        self._extract_concepts_from_identifier(
            entry.function_name,
            'function_name_mention',
            quality_score
        )
        
        # Get all text content
        text_content = []
        
        if nl_context.docstring:
            text_content.append(nl_context.docstring)
            # Extract concepts from docstring
            self._extract_concepts_from_text(
                nl_context.docstring,
                'docstring_mention',
                quality_score
            )
        
        if nl_context.comments:
            text_content.extend(nl_context.comments)
            # Extract concepts from comments
            for comment in nl_context.comments:
                self._extract_concepts_from_text(
                    comment,
                    'comment_mention',
                    quality_score * 0.8  # Comments slightly less reliable
                )
        
        # Process each piece of text for relationships
        for text in text_content:
            self._extract_relationships_from_text(
                text, 
                entry.function_name,
                quality_score
            )
        
        # NEW: Discover actions from function body
        if hasattr(entry, 'source_code') and entry.source_code:
            self._discover_actions_from_code(
                entry.source_code,
                entry.function_name,
                quality_score
            )
    
    def _extract_relationships_from_text(self, text: str, source_function: str, 
                                       base_confidence: float):
        """
        Extract relationships between concepts from a piece of text.
        
        Args:
            text: The text to analyze
            source_function: Function where this text was found
            base_confidence: Base confidence score from documentation quality
        """
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # Find all concepts mentioned in this sentence
            mentioned_concepts = self._find_concepts_in_sentence(sentence)
            
            if len(mentioned_concepts) >= 2:
                # Try to identify relationships between the concepts
                self._identify_relationships(
                    sentence, 
                    mentioned_concepts,
                    source_function,
                    base_confidence
                )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for analysis."""
        # Simple sentence splitting - preserve sentence endings for evidence
        # Split on sentence endings but keep them for better evidence tracking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Normalize whitespace in each sentence
        return [' '.join(s.strip().split()) for s in sentences if s.strip()]
    
    def _find_concepts_in_sentence(self, sentence: str) -> List[Tuple[Concept, int, int]]:
        """
        Find all known concepts mentioned in a sentence.
        
        Returns:
            List of (concept, start_pos, end_pos) tuples
        """
        sentence_lower = sentence.lower()
        found_concepts = []
        
        # Look for each concept variation
        for variation, concept in self._concept_variations.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variation) + r'\b'
            for match in re.finditer(pattern, sentence_lower):
                found_concepts.append((concept, match.start(), match.end()))
        
        # Remove overlapping matches, keeping the longest
        found_concepts = self._remove_overlapping_matches(found_concepts)
        
        return found_concepts
    
    def _remove_overlapping_matches(self, matches: List[Tuple[Concept, int, int]]) -> List[Tuple[Concept, int, int]]:
        """Remove overlapping concept matches, keeping the longest."""
        if not matches:
            return []
        
        # Sort by start position, then by length (descending)
        sorted_matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1])))
        
        result = []
        last_end = -1
        
        for concept, start, end in sorted_matches:
            if start >= last_end:
                result.append((concept, start, end))
                last_end = end
        
        return result
    
    def _identify_relationships(self, sentence: str, concepts: List[Tuple[Concept, int, int]],
                              source_function: str, base_confidence: float):
        """
        Identify relationships between concepts in a sentence.
        
        Args:
            sentence: The sentence containing the concepts
            concepts: List of (concept, start_pos, end_pos) tuples
            source_function: Function where this was found
            base_confidence: Base confidence from documentation quality
        """
        # Try each pair of concepts
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                concept1, _, _ = concepts[i]
                concept2, _, _ = concepts[j]
                
                # Try to match relationship patterns
                for rel_type, patterns in RelationshipPattern.PATTERNS.items():
                    for pattern_template in patterns:
                        # Try both directions
                        if self._match_relationship_pattern(
                            sentence, concept1, concept2, pattern_template
                        ):
                            self._add_discovered_relationship(
                                concept1, concept2, rel_type,
                                sentence, source_function, base_confidence
                            )
                            break
                        
                        # Try reverse direction for asymmetric relationships
                        if rel_type not in ['IS_A', 'BELONGS_TO']:
                            if self._match_relationship_pattern(
                                sentence, concept2, concept1, pattern_template
                            ):
                                self._add_discovered_relationship(
                                    concept2, concept1, rel_type,
                                    sentence, source_function, base_confidence
                                )
                                break
    
    def _match_relationship_pattern(self, sentence: str, source_concept: Concept, 
                                  target_concept: Concept, pattern_template: str) -> bool:
        """
        Check if a sentence matches a relationship pattern.
        
        Args:
            sentence: The sentence to check
            source_concept: The source concept
            target_concept: The target concept
            pattern_template: Pattern template with {source} and {target} placeholders
            
        Returns:
            True if the pattern matches
        """
        # Instead of trying to modify the pattern template, we'll check if the
        # actual words found in the sentence match the pattern
        sentence_lower = sentence.lower()
        
        # Find all occurrences of the concepts in the sentence
        source_occurrences = []
        target_occurrences = []
        
        # Check all variations of source concept
        for variation, concept in self._concept_variations.items():
            if concept == source_concept:
                # Use word boundaries to find exact matches
                pattern = r'\b' + re.escape(variation) + r'\b'
                for match in re.finditer(pattern, sentence_lower):
                    source_occurrences.append((match.group(), match.start(), match.end()))
                    
            elif concept == target_concept:
                pattern = r'\b' + re.escape(variation) + r'\b'
                for match in re.finditer(pattern, sentence_lower):
                    target_occurrences.append((match.group(), match.start(), match.end()))
        
        # Now check if any combination of source and target occurrences
        # matches the relationship pattern
        for source_word, s_start, s_end in source_occurrences:
            for target_word, t_start, t_end in target_occurrences:
                # Build a pattern using the actual words found
                # Replace {source} and {target} with the actual words
                # But we need to handle the regex parts of the pattern template
                
                # Split the pattern template to handle {source} and {target} separately
                # This is a more robust approach
                test_pattern = pattern_template
                
                # Replace {source}s? with a pattern that matches the actual source word
                # Since we found the actual word, we don't need the s? part
                test_pattern = test_pattern.replace('{source}s?', re.escape(source_word))
                test_pattern = test_pattern.replace('{source}', re.escape(source_word))
                
                # Same for target
                test_pattern = test_pattern.replace('{target}s?', re.escape(target_word))
                test_pattern = test_pattern.replace('{target}', re.escape(target_word))
                
                # Now test if this pattern matches the sentence
                if re.search(test_pattern, sentence_lower):
                    return True
        
        return False
    
    def _get_concept_name_variations(self, concept: Concept) -> List[str]:
        """Get name variations for a concept (singular, plural, etc.)."""
        concept_str = str(concept)
        variations = [concept_str]
        
        # Add lowercase
        variations.append(concept_str.lower())
        
        # Add plural/singular
        if concept_str.endswith('s'):
            variations.append(concept_str[:-1])
            variations.append(concept_str[:-1].lower())
        else:
            variations.append(concept_str + 's')
            variations.append(concept_str.lower() + 's')
        
        return list(set(variations))
    
    def _add_discovered_relationship(self, source: Concept, target: Concept,
                                   rel_type: str, evidence: str, 
                                   source_function: str, base_confidence: float):
        """Add a discovered relationship to the graph."""
        # Calculate final confidence
        # Higher confidence if the relationship type is explicit
        pattern_confidence = 0.8 if rel_type in ['HAS_ONE', 'HAS_MANY', 'BELONGS_TO'] else 0.7
        final_confidence = base_confidence * pattern_confidence
        
        # Strip and normalize evidence - ensure consistent whitespace
        evidence_cleaned = ' '.join(evidence.strip().split())
        
        # Check if this relationship already exists to prevent duplicates in our tracking
        relationship_exists = False
        for existing_rel in self._discovered_relationships:
            if (existing_rel['source'] == source and 
                existing_rel['target'] == target and 
                existing_rel['relation'] == rel_type):
                relationship_exists = True
                break
        
        # Create metadata with Bayesian belief parameters
        # Convert confidence to alpha/beta: for beta=1, alpha = confidence/(1-confidence)
        if final_confidence >= 0.99:
            alpha = 99.0
            beta = 1.0
        elif final_confidence <= 0.01:
            alpha = 1.0
            beta = 99.0
        else:
            alpha = final_confidence / (1 - final_confidence)
            beta = 1.0
            
        metadata = RelationMetadata(
            relation_type=rel_type,
            alpha=alpha,
            beta=beta,
            evidence_functions=[source_function],
            evidence_patterns=[evidence_cleaned]
        )
        
        # Add to graph (the graph's add_relation method handles its own duplicate checking)
        self.knowledge_graph.add_relation(
            source, target, 
            Relation(rel_type),
            metadata=metadata,
            confidence=final_confidence,
            evidence=evidence_cleaned
        )
        
        # Track for reporting only if not already tracked
        if not relationship_exists:
            self._discovered_relationships.append({
                'source': source,
                'target': target,
                'relation': rel_type,
                'confidence': final_confidence,
                'evidence': evidence_cleaned,
                'source_function': source_function
            })
    
    def generate_enrichment_report(self) -> str:
        """
        Generate a human-readable report of discovered relationships.
        
        Returns:
            Formatted report string
        """
        lines = ["Knowledge Graph Enrichment Report", "=" * 50, ""]
        
        if not self._discovered_relationships:
            lines.append("No new relationships discovered from documentation.")
            return "\n".join(lines)
        
        lines.append(f"Discovered {len(self._discovered_relationships)} relationships from text:")
        lines.append("")
        
        # Group by relationship type
        by_type = defaultdict(list)
        for rel in self._discovered_relationships:
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
        
        return "\n".join(lines)
    
    def get_discovered_relationships(self) -> List[Dict[str, any]]:
        """Get list of all discovered relationships."""
        return self._discovered_relationships.copy()
    
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
        
        if self.nlp_extractor:
            # Use NLP to extract nouns
            nouns = self.nlp_extractor.extract_nouns_from_identifier(identifier)
            
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
                
                # Add to our concept set if new
                if concept not in self.concepts:
                    self.concepts.add(concept)
                    # Rebuild variations for the new concept
                    self._concept_variations = self._build_concept_variations()
        
        # Process co-occurrences if multiple concepts found
        if len(extracted_concepts) >= 2:
            self._process_concept_cooccurrences(
                extracted_concepts,
                evidence_type.replace('mention', 'co_occurrence'),
                source_credibility
            )
        
        return extracted_concepts
    
    def _extract_concepts_from_text(self, text: str, evidence_type: str,
                                  source_credibility: float):
        """
        Extract concepts from natural language text and update beliefs.
        
        Args:
            text: The text to analyze
            evidence_type: Type of evidence for Bayesian update
            source_credibility: Credibility of the source
        """
        all_extracted_concepts = []
        
        if self.nlp_extractor:
            # Split text into sentences for better processing
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                sentence_concepts = []
                # Extract nouns from the sentence
                nouns = self.nlp_extractor.extract_nouns_from_identifier(sentence)
                
                for noun in nouns:
                    # Check if this noun matches any known concept
                    concept_match = self._find_matching_concept(noun)
                    
                    if concept_match:
                        # Update belief for existing concept
                        self.bayesian_updater.update_concept_belief(
                            concept_match,
                            evidence_type,
                            source_credibility
                        )
                        sentence_concepts.append(str(concept_match))
                    else:
                        # Create new concept
                        concept = Concept(noun.title())
                        self.bayesian_updater.update_concept_belief(
                            concept,
                            evidence_type,
                            source_credibility * 0.7  # Lower confidence for new concepts from text
                        )
                        sentence_concepts.append(noun.title())
                        
                        # Add to our concept set
                        if concept not in self.concepts:
                            self.concepts.add(concept)
                            self._concept_variations = self._build_concept_variations()
                
                # Process co-occurrences within each sentence
                if len(sentence_concepts) >= 2:
                    self._process_concept_cooccurrences(
                        sentence_concepts,
                        evidence_type.replace('mention', 'co_occurrence'),
                        source_credibility
                    )
                
                all_extracted_concepts.extend(sentence_concepts)
        
        return all_extracted_concepts
    
    def _find_matching_concept(self, noun: str) -> Optional[Concept]:
        """Find if a noun matches any existing concept."""
        noun_lower = noun.lower()
        
        # Check direct match in variations
        if noun_lower in self._concept_variations:
            return self._concept_variations[noun_lower]
        
        # Check if it's a plural/singular form of existing concept
        for concept in self.concepts:
            concept_str = str(concept).lower()
            if (noun_lower == concept_str or
                noun_lower == concept_str + 's' or
                noun_lower + 's' == concept_str):
                return concept
                
        return None
    
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
        from itertools import combinations
        
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
    
    def _discover_actions_from_code(self, source_code: str, function_name: str,
                                  base_confidence: float):
        """
        Discover actions performed in the function code.
        
        Args:
            source_code: The source code of the function
            function_name: Name of the function
            base_confidence: Base confidence from documentation quality
        """
        # Use ActionDiscoverer to find actions
        discovered_actions = self.action_discoverer.discover_actions(
            source_code, function_name
        )
        
        for action in discovered_actions:
            # Update belief in the action relationship
            self.bayesian_updater.update_action_belief(
                action.concept,
                action.verb,
                'method_call' if '.' in action.method_name else 'function_name',
                base_confidence * action.confidence
            )
            
            # Track for reporting
            self._discovered_actions.append({
                'concept': action.concept,
                'action': action.verb,
                'method': action.method_name,
                'confidence': action.confidence * base_confidence,
                'source_function': function_name
            })
    
    def get_discovered_actions(self) -> List[Dict[str, any]]:
        """Get list of all discovered actions."""
        return self._discovered_actions.copy()