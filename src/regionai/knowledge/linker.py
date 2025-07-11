"""
Knowledge Linker service for enriching Knowledge Graphs with natural language evidence.

This module reads documentation and identifies relationships between concepts
described in text, adding them to the Knowledge Graph with confidence scores
and evidence tracking. This is the bridge from deterministic code analysis
to probabilistic belief formation.
"""
import re
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
import logging

from ..semantic.db import SemanticDB
from ..semantic.fingerprint import DocumentationQuality
from .graph import KnowledgeGraph, Concept, Relation, RelationMetadata


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
        self.kg = knowledge_graph
        self.concepts = set(self.kg.get_concepts())
        self.logger = logging.getLogger(__name__)
        
        # Track discovered relationships for reporting
        self._discovered_relationships: List[Dict[str, any]] = []
        
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
                variations[concept_str[:-1].lower()] = concept
            else:
                variations[(concept_str + 's').lower()] = concept
            
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
        return self.kg
    
    def _process_documentation(self, entry):
        """Process documentation from a single semantic entry."""
        doc_fingerprint = entry.documented_fingerprint
        nl_context = doc_fingerprint.nl_context
        
        # Get all text content
        text_content = []
        
        if nl_context.docstring:
            text_content.append(nl_context.docstring)
        
        if nl_context.comments:
            text_content.extend(nl_context.comments)
        
        # Calculate base confidence from documentation quality
        quality_score = DocumentationQuality.score_documentation(nl_context)
        
        # Process each piece of text
        for text in text_content:
            self._extract_relationships_from_text(
                text, 
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
        # Build pattern with actual concept names
        source_variations = self._get_concept_name_variations(source_concept)
        target_variations = self._get_concept_name_variations(target_concept)
        
        for source_var in source_variations:
            for target_var in target_variations:
                pattern = pattern_template.format(
                    source=re.escape(source_var),
                    target=re.escape(target_var)
                )
                
                if re.search(pattern, sentence, re.IGNORECASE):
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
        
        # Create metadata
        metadata = RelationMetadata(
            relation_type=rel_type,
            confidence=final_confidence,
            evidence_functions=[source_function],
            evidence_patterns=[evidence_cleaned]
        )
        
        # Add to graph (the graph's add_relation method handles its own duplicate checking)
        self.kg.add_relation(
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