"""
Concept discovery service for inferring real-world entities from code analysis.

This module implements the intelligence that bridges code analysis with
common-sense understanding by discovering concepts like "User", "Product",
or "Invoice" from the functions that manipulate them.
"""
import re
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

from tier2.computer_science.semantic.db import SemanticDB
from tier2.computer_science.semantic.fingerprint import Behavior
from .graph import WorldKnowledgeGraph, Concept, Relation, ConceptMetadata, RelationMetadata
from tier2.linguistics import nlp_utils
from ..utils.component_loader import get_nlp_model
from ..config import RegionAIConfig, DEFAULT_CONFIG
from ..utils.error_handling import PartialResultCollector, safe_execute
from ..utils.memory_manager import get_memory_manager

logger = logging.getLogger(__name__)


@dataclass
class CRUDPattern:
    """Represents a discovered CRUD pattern for a concept."""
    concept_name: str
    create_functions: List[str] = None
    read_functions: List[str] = None
    update_functions: List[str] = None
    delete_functions: List[str] = None
    
    def __post_init__(self):
        if self.create_functions is None:
            self.create_functions = []
        if self.read_functions is None:
            self.read_functions = []
        if self.update_functions is None:
            self.update_functions = []
        if self.delete_functions is None:
            self.delete_functions = []
    
    @property
    def all_functions(self) -> List[str]:
        """Get all functions in this CRUD pattern."""
        return (self.create_functions + self.read_functions + 
                self.update_functions + self.delete_functions)
    
    @property
    def completeness_score(self) -> float:
        """Score how complete this CRUD pattern is (0.0 to 1.0)."""
        operations = [
            bool(self.create_functions),
            bool(self.read_functions),
            bool(self.update_functions),
            bool(self.delete_functions)
        ]
        return sum(operations) / 4.0


class ConceptDiscoverer:
    """
    Infers real-world concepts from a SemanticDB by analyzing function names,
    fingerprints, and other patterns.
    
    This is the bridge between code analysis and common-sense reasoning,
    discovering the entities that exist in the problem domain.
    """
    
    def __init__(self, semantic_db: SemanticDB, config: RegionAIConfig = None, memory_manager=None):
        """
        Initialize the discoverer with a semantic database.
        
        Args:
            semantic_db: The analyzed codebase's semantic information
            config: Configuration (defaults to DEFAULT_CONFIG)
            memory_manager: Optional memory manager for memory monitoring
        """
        self.db = semantic_db
        self.config = config or DEFAULT_CONFIG
        self.memory_manager = memory_manager
        self._discovered_patterns: List[CRUDPattern] = []
        self._noun_frequencies: Dict[str, int] = defaultdict(int)
        self._noun_sources: Dict[str, Set[str]] = defaultdict(set)  # Track which functions mentioned each noun
        
        # Get the cached NLP model
        self.nlp_model = get_nlp_model()
        if self.nlp_model is None:
            print("Warning: spaCy model not found. Using basic extraction.")
    
    def discover_concepts(self) -> WorldKnowledgeGraph:
        """
        Main discovery method that applies multiple heuristics to find concepts.
        
        Returns:
            A populated WorldKnowledgeGraph with discovered concepts and relationships
        """
        kg = WorldKnowledgeGraph()
        collector = PartialResultCollector("concept_discovery")
        
        # Check memory before starting
        if self.memory_manager:
            self.memory_manager.check_memory()
        else:
            # Fallback to global for backward compatibility
            memory_manager = get_memory_manager()
            memory_manager.check_memory()
        
        # Apply different discovery heuristics with error recovery
        crud_concepts = collector.collect(self._discover_crud_patterns) or []
        noun_concepts = collector.collect(self._discover_by_noun_extraction) or {}
        behavior_concepts = collector.collect(self._discover_by_behaviors) or {}
        relationships = collector.collect(self._discover_relationships) or []
        
        # Add discovered concepts to the graph with error handling
        safe_execute(lambda: self._add_crud_concepts(kg, crud_concepts), log_errors=True)
        safe_execute(lambda: self._add_noun_concepts(kg, noun_concepts), log_errors=True)
        safe_execute(lambda: self._add_behavior_concepts(kg, behavior_concepts), log_errors=True)
        safe_execute(lambda: self._add_relationships(kg, relationships), log_errors=True)
        
        # Post-process to merge similar concepts
        safe_execute(lambda: self._merge_similar_concepts(kg), log_errors=True)
        
        # Log summary
        summary = collector.get_summary()
        if summary['failed'] > 0:
            logger.warning(f"Concept discovery completed with errors: {summary}")
        else:
            logger.info(f"Concept discovery completed successfully: {summary}")
        
        return kg
    
    def _discover_crud_patterns(self) -> List[CRUDPattern]:
        """
        Discover concepts by finding CRUD operation patterns.
        
        Looks for sets of functions that create, read, update, and delete
        the same type of entity.
        """
        patterns: Dict[str, CRUDPattern] = {}
        
        for entry in self.db:
            func_name = entry.function_name.lower()
            
            # Try to match CRUD patterns
            for operation, verbs in self.config.discovery.crud_verbs.items():
                for verb in verbs:
                    # Pattern: verb_noun (e.g., create_user)
                    match = re.match(f'{verb}_(\\w+)', func_name)
                    if match:
                        noun = match.group(1)
                        self._add_to_crud_pattern(patterns, noun, operation, entry.function_name)
                        break
                    
                    # Pattern: noun_verb (e.g., user_create)
                    match = re.match(f'(\\w+)_{verb}', func_name)
                    if match:
                        noun = match.group(1)
                        self._add_to_crud_pattern(patterns, noun, operation, entry.function_name)
                        break
        
        # Filter patterns that have at least 2 different operations
        valid_patterns = []
        for concept_name, pattern in patterns.items():
            if pattern.completeness_score >= self.config.discovery.crud_pattern_min_operations:
                valid_patterns.append(pattern)
                self._discovered_patterns.append(pattern)
        
        return valid_patterns
    
    def _add_to_crud_pattern(self, patterns: Dict[str, CRUDPattern], 
                           noun: str, operation: str, function_name: str):
        """Helper to add a function to the appropriate CRUD pattern."""
        # Normalize noun to singular form (simple heuristic)
        if noun.endswith('s') and len(noun) > 2:
            singular = noun[:-1]
            if singular in patterns or noun not in patterns:
                noun = singular
        
        if noun not in patterns:
            patterns[noun] = CRUDPattern(concept_name=noun.title())
        
        pattern = patterns[noun]
        if operation == 'create' and function_name not in pattern.create_functions:
            pattern.create_functions.append(function_name)
        elif operation == 'read' and function_name not in pattern.read_functions:
            pattern.read_functions.append(function_name)
        elif operation == 'update' and function_name not in pattern.update_functions:
            pattern.update_functions.append(function_name)
        elif operation == 'delete' and function_name not in pattern.delete_functions:
            pattern.delete_functions.append(function_name)
    
    def _discover_by_noun_extraction(self) -> Set[str]:
        """
        Extract potential concepts by analyzing nouns in function names and docstrings.
        """
        concepts = set()
        
        for entry in self.db:
            # Extract from function name
            func_name = entry.function_name
            nouns = self._extract_nouns_from_identifier(func_name)
            for noun in nouns:
                self._noun_frequencies[noun] += 1
                self._noun_sources[noun].add(func_name)
            
            # Extract from documentation if available
            if entry.documented_fingerprint:
                nl_context = entry.documented_fingerprint.nl_context
                if nl_context.docstring:
                    doc_nouns = self._extract_nouns_from_text(nl_context.docstring)
                    for noun in doc_nouns:
                        self._noun_frequencies[noun] += 1
                        self._noun_sources[noun].add(func_name)
        
        # Consider nouns that appear frequently as concepts
        threshold = self.config.discovery.concept_frequency_threshold
        
        for noun, frequency in self._noun_frequencies.items():
            if frequency >= threshold:
                # Filter out common programming terms
                if not self._is_programming_term(noun):
                    concepts.add(noun.title())
        
        return concepts
    
    def _extract_nouns_from_identifier(self, identifier: str) -> List[str]:
        """Extract potential nouns from snake_case or camelCase identifiers."""
        # Use the pure function from nlp_utils
        return nlp_utils.extract_nouns_from_identifier(identifier, self.nlp_model)
    
    
    def _extract_nouns_from_text(self, text: str) -> List[str]:
        """Extract nouns from natural language text using NLP."""
        if self.nlp_model:
            # Extract nouns from the text
            # Split into words and process
            words = text.split()
            all_nouns = []
            
            # Process chunks of text
            for i in range(0, len(words), 10):  # Process 10 words at a time
                chunk = " ".join(words[i:i+10])
                nouns = nlp_utils.extract_nouns_from_identifier(chunk, self.nlp_model)
                all_nouns.extend(nouns)
            
            # Filter out programming terms
            filtered_nouns = []
            for noun in all_nouns:
                if not self._is_programming_term(noun):
                    filtered_nouns.append(noun)
            
            return list(set(filtered_nouns))  # Remove duplicates
        else:
            # Fallback to simple extraction
            return self._extract_nouns_simple(text)
    
    def _extract_nouns_simple(self, text: str) -> List[str]:
        """Simple fallback noun extraction without spaCy."""
        # Use common skip words constant
        
        # Look for capitalized words that aren't at sentence start
        words = []
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # Find capitalized words, but skip the first word of sentence
            sentence_words = sentence.split()
            if len(sentence_words) > 1:
                for word in sentence_words[1:]:
                    if word and word[0].isupper() and word.isalpha():
                        words.append(word)
        
        # Also extract words after "a", "an", "the"
        article_pattern = r'\b(?:a|an|the)\s+(\w+)\b'
        article_nouns = re.findall(article_pattern, text, re.IGNORECASE)
        
        all_nouns = [w.lower() for w in words + article_nouns]
        return [n for n in all_nouns if not self._is_programming_term(n)]
    
    def _is_programming_term(self, word: str) -> bool:
        """Check if a word is a common programming term rather than a domain concept."""
        return word.lower() in self.config.discovery.programming_terms
    
    def _discover_by_behaviors(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        Discover concepts based on semantic behavior patterns.
        
        For example, functions with VALIDATOR behavior might validate
        specific types of entities.
        
        Returns:
            Dict mapping behavior type to dict of concept -> source functions
        """
        behavior_concepts = defaultdict(lambda: defaultdict(set))
        
        for entry in self.db:
            fingerprint = entry.fingerprint
            
            # Validators often validate specific entities
            if Behavior.VALIDATOR in fingerprint.behaviors:
                # Look for patterns like "validate_email", "is_valid_user"
                match = re.search(r'(?:validate_|is_valid_|check_)(\w+)', 
                                entry.function_name, re.IGNORECASE)
                if match:
                    concept = match.group(1).title()
                    behavior_concepts['validator'][concept].add(entry.function_name)
            
            # Transformers might transform between entity types
            if Behavior.TRANSFORMER in fingerprint.behaviors:
                # Look for patterns like "user_to_dto", "convert_order_to_invoice"
                match = re.search(r'(\w+)_to_(\w+)', entry.function_name, re.IGNORECASE)
                if match:
                    source = match.group(1).title()
                    target = match.group(2).title()
                    behavior_concepts['transformer'][source].add(entry.function_name)
                    behavior_concepts['transformer'][target].add(entry.function_name)
        
        return behavior_concepts
    
    def _discover_relationships(self) -> List[Tuple[str, str, str]]:
        """
        Discover relationships between concepts based on function patterns.
        
        Returns:
            List of (source_concept, target_concept, relationship_type) tuples
        """
        relationships = []
        
        for entry in self.db:
            func_name = entry.function_name.lower()
            
            # Check for relationship patterns
            for rel_type, patterns in self.config.discovery.relationship_patterns.items():
                for pattern in patterns:
                    match = re.match(pattern, func_name)
                    if match:
                        if len(match.groups()) >= 2:
                            concept1 = match.group(1).title()
                            concept2 = match.group(2).title()
                            
                            # Validate these are known concepts
                            if (self._is_known_concept(concept1) and 
                                self._is_known_concept(concept2)):
                                relationships.append((concept1, concept2, rel_type))
        
        return relationships
    
    def _is_known_concept(self, concept: str) -> bool:
        """Check if a concept has been discovered through other heuristics."""
        concept_lower = concept.lower()
        
        # Check CRUD patterns
        for pattern in self._discovered_patterns:
            if pattern.concept_name.lower() == concept_lower:
                return True
        
        # Check noun frequencies
        if concept_lower in self._noun_frequencies:
            return self._noun_frequencies[concept_lower] >= 2
        
        return False
    
    def _add_crud_concepts(self, kg: WorldKnowledgeGraph, patterns: List[CRUDPattern]):
        """Add concepts discovered through CRUD patterns to the graph."""
        for pattern in patterns:
            # Convert completeness score to alpha/beta
            score = pattern.completeness_score
            if score >= 0.99:
                alpha = 99.0
                beta = 1.0
            elif score <= 0.01:
                alpha = 1.0
                beta = 99.0
            else:
                alpha = score / (1 - score)
                beta = 1.0
                
            metadata = ConceptMetadata(
                discovery_method="CRUD_PATTERN",
                alpha=alpha,
                beta=beta,
                source_functions=pattern.all_functions,
                properties={
                    'has_create': bool(pattern.create_functions),
                    'has_read': bool(pattern.read_functions),
                    'has_update': bool(pattern.update_functions),
                    'has_delete': bool(pattern.delete_functions)
                }
            )
            
            kg.add_concept(Concept(pattern.concept_name), metadata)
    
    def _add_noun_concepts(self, kg: WorldKnowledgeGraph, concepts: Set[str]):
        """Add concepts discovered through noun extraction."""
        for concept in concepts:
            # Don't add if already added by CRUD discovery
            if Concept(concept) not in kg:
                # Convert frequency-based confidence to alpha/beta
                freq_confidence = min(self._noun_frequencies[concept.lower()] / 10.0, 1.0)
                if freq_confidence >= 0.99:
                    alpha = 99.0
                    beta = 1.0
                elif freq_confidence <= 0.01:
                    alpha = 1.0
                    beta = 99.0
                else:
                    alpha = freq_confidence / (1 - freq_confidence)
                    beta = 1.0
                    
                metadata = ConceptMetadata(
                    discovery_method="NOUN_EXTRACTION",
                    alpha=alpha,
                    beta=beta,
                    source_functions=list(self._noun_sources[concept.lower()]),
                    properties={
                        'frequency': self._noun_frequencies[concept.lower()]
                    }
                )
                
                kg.add_concept(Concept(concept), metadata)
    
    def _add_behavior_concepts(self, kg: WorldKnowledgeGraph, 
                             behavior_concepts: Dict[str, Dict[str, Set[str]]]):
        """Add concepts discovered through behavior analysis."""
        for behavior_type, concept_dict in behavior_concepts.items():
            for concept, source_functions in concept_dict.items():
                if Concept(concept) not in kg:
                    metadata = ConceptMetadata(
                        discovery_method=f"BEHAVIOR_ANALYSIS_{behavior_type.upper()}",
                        alpha=2.33,  # Equivalent to confidence=0.7 (0.7/0.3≈2.33)
                        beta=1.0,
                        source_functions=list(source_functions),
                        related_behaviors={behavior_type}
                    )
                    
                    kg.add_concept(Concept(concept), metadata)
    
    def _add_relationships(self, kg: WorldKnowledgeGraph, 
                          relationships: List[Tuple[str, str, str]]):
        """Add discovered relationships to the graph."""
        for source, target, rel_type in relationships:
            metadata = RelationMetadata(
                relation_type=rel_type.upper(),
                alpha=4.0,  # Equivalent to confidence=0.8 (0.8/0.2=4)
                beta=1.0,
                evidence_patterns=[f"{source.lower()}_{rel_type}_{target.lower()}"]
            )
            
            kg.add_relation(Concept(source), Concept(target), 
                          Relation(rel_type.upper()), metadata)
    
    def _merge_similar_concepts(self, kg: WorldKnowledgeGraph):
        """
        Post-process to merge concepts that likely represent the same entity.
        
        For example, "User" and "Users" or "User" and "Account" might be merged.
        """
        concepts = kg.get_concepts()
        
        # Simple heuristic: merge singular/plural forms
        for concept in concepts:
            singular = concept.rstrip('s') if concept.endswith('s') else concept
            concept + 's' if not concept.endswith('s') else concept
            
            if singular != concept and Concept(singular) in kg:
                # Merge plural into singular
                kg.merge_concepts(concept, Concept(singular), Concept(singular))
    
    def generate_discovery_report(self) -> str:
        """
        Generate a human-readable report of the discovery process.
        
        Returns:
            A formatted string describing what was discovered and how
        """
        lines = ["Concept Discovery Report", "=" * 50, ""]
        
        # CRUD Patterns
        lines.append("CRUD Patterns Discovered:")
        if self._discovered_patterns:
            for pattern in sorted(self._discovered_patterns, 
                                key=lambda p: p.completeness_score, reverse=True):
                lines.append(f"  {pattern.concept_name} (completeness: {pattern.completeness_score:.0%})")
                if pattern.create_functions:
                    lines.append(f"    Create: {', '.join(pattern.create_functions)}")
                if pattern.read_functions:
                    lines.append(f"    Read: {', '.join(pattern.read_functions)}")
                if pattern.update_functions:
                    lines.append(f"    Update: {', '.join(pattern.update_functions)}")
                if pattern.delete_functions:
                    lines.append(f"    Delete: {', '.join(pattern.delete_functions)}")
                lines.append("")
        else:
            lines.append("  None found")
            lines.append("")
        
        # Noun Frequencies
        lines.append("Top Nouns by Frequency:")
        sorted_nouns = sorted(self._noun_frequencies.items(), 
                            key=lambda x: x[1], reverse=True)[:10]
        for noun, freq in sorted_nouns:
            if freq >= 2:
                lines.append(f"  {noun}: {freq} occurrences")
        lines.append("")
        
        return "\n".join(lines)