"""
Pure functions for grammatical pattern extraction.

This module provides functional utilities for extracting grammatical patterns
from natural language text using spaCy, replacing the class-based approach
with more efficient, testable pure functions.
"""
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class GrammaticalPattern:
    """Represents a grammatical pattern extracted from text."""
    subject: Optional[str]      # The entity performing the action
    verb: str                   # The action or relationship
    object: Optional[str]       # The entity being acted upon
    modifiers: List[str]        # Additional modifiers (adjectives, adverbs, etc.)
    raw_sentence: str           # Original sentence for reference
    confidence: float           # Confidence in the extraction (0.0 to 1.0)
    
    def __str__(self):
        """String representation of the pattern."""
        subj = self.subject or "?"
        obj = self.object or "?"
        return f"({subj}, {self.verb}, {obj})"
    
    def to_triple(self) -> Tuple[Optional[str], str, Optional[str]]:
        """Return as a simple (subject, verb, object) triple."""
        return (self.subject, self.verb, self.object)


def extract_patterns(text: str, nlp_model, config: RegionAIConfig = None) -> List[GrammaticalPattern]:
    """
    Extract grammatical patterns from text.
    
    This function processes the input text with spaCy and extracts
    Subject-Verb-Object triples from each sentence.
    
    Args:
        text: The text to analyze
        nlp_model: A loaded spaCy model instance
        
    Returns:
        List of GrammaticalPattern objects
    """
    if not text or not text.strip():
        return []
    
    if nlp_model is None:
        raise ValueError("spaCy model is required for pattern extraction")
    
    config = config or DEFAULT_CONFIG
    
    # Process text with spaCy
    doc = nlp_model(text)
    
    patterns = []
    
    # Process each sentence
    for sent in doc.sents:
        # Try to extract patterns from this sentence
        sent_patterns = _extract_from_sentence(sent, config)
        patterns.extend(sent_patterns)
    
    return patterns


def extract_patterns_with_context(text: str, nlp_model, function_name: str = None, config: RegionAIConfig = None) -> List[GrammaticalPattern]:
    """
    Extract patterns with additional context information.
    
    Args:
        text: The text to analyze
        nlp_model: A loaded spaCy model instance
        function_name: Optional function name for context
        
    Returns:
        List of patterns with enhanced context
    """
    config = config or DEFAULT_CONFIG
    patterns = extract_patterns(text, nlp_model, config)
    
    # If we have a function name, we might boost confidence for patterns
    # that mention concepts related to the function name
    if function_name and patterns:
        function_parts = _split_identifier(function_name)
        
        for pattern in patterns:
            # Boost confidence if subject or object matches function parts
            if pattern.subject in function_parts or pattern.object in function_parts:
                pattern.confidence = min(1.0, pattern.confidence + 0.1)
    
    return patterns


def _extract_from_sentence(sent, config: RegionAIConfig) -> List[GrammaticalPattern]:
    """
    Extract patterns from a single sentence.
    
    Args:
        sent: A spaCy Span object representing a sentence
        
    Returns:
        List of patterns extracted from the sentence
    """
    patterns = []
    
    # Find all verbs in the sentence
    for token in sent:
        if token.pos_ == "VERB":
            pattern = _extract_svo_from_verb(token, sent, config)
            if pattern:
                patterns.append(pattern)
    
    # Also handle copular sentences (e.g., "X is Y")
    copular_patterns = _extract_copular_patterns(sent, config)
    patterns.extend(copular_patterns)
    
    return patterns


def _extract_svo_from_verb(verb, sent, config: RegionAIConfig) -> Optional[GrammaticalPattern]:
    """
    Extract Subject-Verb-Object pattern from a verb token.
    
    Args:
        verb: The verb token
        sent: The full sentence
        
    Returns:
        GrammaticalPattern or None if extraction fails
    """
    # Find subject
    subject = None
    subject_modifiers = []
    
    for child in verb.children:
        if child.dep_ in config.discovery.subject_dependency_labels:  # Nominal subject
            subject = child.lemma_.lower()
            # Collect subject modifiers
            subject_modifiers.extend([mod.text.lower() for mod in child.children 
                                    if mod.dep_ in config.discovery.modifier_dependency_labels])
            break
    
    # Find object
    obj = None
    object_modifiers = []
    
    for child in verb.children:
        if child.dep_ in config.discovery.object_dependency_labels | {"attr", "prep"}:  # Direct object or attribute
            if child.dep_ == "prep":
                # Handle prepositional phrases
                for grandchild in child.children:
                    if grandchild.dep_ == "pobj":
                        obj = grandchild.lemma_.lower()
                        object_modifiers.extend([mod.text.lower() for mod in grandchild.children
                                               if mod.dep_ in config.discovery.modifier_dependency_labels])
                        break
            else:
                obj = child.lemma_.lower()
                object_modifiers.extend([mod.text.lower() for mod in child.children
                                       if mod.dep_ in config.discovery.modifier_dependency_labels])
            break
    
    # Get lemmatized verb
    verb_lemma = verb.lemma_.lower()
    
    # Skip auxiliary verbs as main verbs
    if verb_lemma in config.discovery.auxiliary_verbs:
        return None
    
    # Calculate confidence based on pattern completeness
    confidence = config.discovery.grammar_pattern_base_confidence  # Base confidence
    if subject:
        confidence += config.discovery.grammar_pattern_confidence_increment
    if obj:
        confidence += config.discovery.grammar_pattern_confidence_increment
    
    # Combine modifiers
    all_modifiers = subject_modifiers + object_modifiers
    
    return GrammaticalPattern(
        subject=subject,
        verb=verb_lemma,
        object=obj,
        modifiers=all_modifiers,
        raw_sentence=sent.text.strip(),
        confidence=confidence
    )


def _extract_copular_patterns(sent, config: RegionAIConfig) -> List[GrammaticalPattern]:
    """
    Extract patterns from copular sentences (e.g., "X is Y").
    
    Args:
        sent: The sentence to analyze
        
    Returns:
        List of patterns for copular constructions
    """
    patterns = []
    
    # Find copular verbs (forms of "be")
    for token in sent:
        if token.lemma_ == "be" and token.dep_ == "ROOT":
            # Find subject
            subject = None
            for child in token.children:
                if child.dep_ in config.discovery.subject_dependency_labels:
                    subject = child.lemma_.lower()
                    break
            
            # Find complement (what comes after "is")
            complement = None
            relation_type = None
            
            for child in token.children:
                if child.dep_ == "attr":  # Attribute (e.g., "X is a Y")
                    complement = child.lemma_.lower()
                    # Check if there's a determiner suggesting type
                    for grandchild in child.children:
                        if grandchild.dep_ == "det" and grandchild.text.lower() in config.discovery.type_determiners:
                            relation_type = "is_a"
                            break
                    else:
                        relation_type = "is"
                    break
                elif child.dep_ == "acomp":  # Adjectival complement
                    complement = child.lemma_.lower()
                    relation_type = "has_property"
                    break
            
            if subject and complement and relation_type:
                patterns.append(GrammaticalPattern(
                    subject=subject,
                    verb=relation_type,
                    object=complement,
                    modifiers=[],
                    raw_sentence=sent.text.strip(),
                    confidence=config.discovery.grammar_copular_pattern_confidence
                ))
    
    return patterns


def _split_identifier(identifier: str) -> List[str]:
    """
    Split a code identifier into meaningful parts.
    
    Args:
        identifier: Code identifier (e.g., "get_user_orders")
        
    Returns:
        List of parts in lowercase
    """
    import re
    
    # Handle snake_case
    if '_' in identifier:
        parts = identifier.lower().split('_')
    else:
        # Handle camelCase
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', identifier)
        parts = [p.lower() for p in parts]
    
    # Filter out common prefixes that don't add meaning
    # TODO: Use config.discovery.identifier_skip_words when config is passed to this function
    skip_words = {'get', 'set', 'is', 'has', 'create', 'update', 'delete', 'find'}
    return [p for p in parts if p not in skip_words]