"""
Pure functions for NLP extraction utilities.

This module provides functional utilities for extracting meaningful words
from code identifiers using spaCy, replacing class-based extractors with
more efficient, testable pure functions.
"""
import re
from typing import List, Dict
from collections import defaultdict


def extract_nouns_from_identifier(identifier: str, nlp_model) -> List[str]:
    """
    Extract nouns from a code identifier using POS tagging.
    
    Args:
        identifier: A snake_case or camelCase identifier
        nlp_model: A loaded spaCy model instance
        
    Returns:
        List of nouns found in the identifier
    """
    if nlp_model is None:
        # Fallback to simple extraction if no model available
        return _extract_nouns_fallback(identifier)
    
    # Split the identifier into words
    words = _split_identifier(identifier)
    
    # Filter to meaningful words (length > 2)
    words = [w for w in words if len(w) > 2]
    
    if not words:
        return []
    
    # Join words into a sentence-like string for NLP processing
    text = " ".join(words)
    
    # Process with spaCy
    doc = nlp_model(text)
    
    # Extract nouns based on POS tags
    nouns = []
    for token in doc:
        # Look for nouns: NOUN (common noun) or PROPN (proper noun)
        if token.pos_ in ["NOUN", "PROPN"]:
            # Skip if it's an acronym (all uppercase)
            if not token.text.isupper():
                nouns.append(token.text.lower())
    
    return nouns


def extract_parts_of_speech(identifier: str, nlp_model) -> Dict[str, List[str]]:
    """
    Extract all parts of speech from an identifier.
    
    This function provides more detailed POS information for advanced uses.
    
    Args:
        identifier: A snake_case or camelCase identifier
        nlp_model: A loaded spaCy model instance
        
    Returns:
        Dictionary mapping POS tags to lists of words
    """
    if nlp_model is None:
        # Return basic extraction if no model available
        words = _split_identifier(identifier)
        return {"UNKNOWN": [w for w in words if len(w) > 2]}
    
    # Split the identifier into words
    words = _split_identifier(identifier)
    
    # Filter to meaningful words
    words = [w for w in words if len(w) > 2]
    
    if not words:
        return {}
    
    # Process with spaCy
    text = " ".join(words)
    doc = nlp_model(text)
    
    # Group by POS
    pos_groups = defaultdict(list)
    for token in doc:
        if not token.text.isupper():  # Skip acronyms
            pos_groups[token.pos_].append(token.text.lower())
    
    return dict(pos_groups)


def extract_verbs(identifier: str, nlp_model) -> List[str]:
    """
    Extract verbs from an identifier and return their lemmatized forms.
    
    Args:
        identifier: A snake_case or camelCase identifier
        nlp_model: A loaded spaCy model instance
        
    Returns:
        List of lemmatized verbs found in the identifier
    """
    if nlp_model is None:
        # Fallback to simple extraction
        return _extract_verbs_fallback(identifier)
    
    # Split the identifier into words
    words = _split_identifier(identifier)
    
    # Filter to meaningful words
    words = [w for w in words if len(w) > 2]
    
    if not words:
        return []
    
    # Process with spaCy
    text = " ".join(words)
    doc = nlp_model(text)
    
    # Extract verbs and return lemmatized forms
    verbs = []
    for token in doc:
        if token.pos_ == "VERB":
            # Use lemma for the base form
            verbs.append(token.lemma_.lower())
    
    return verbs


def _split_identifier(identifier: str) -> List[str]:
    """
    Split a code identifier into words.
    
    Handles both snake_case and camelCase identifiers.
    
    Args:
        identifier: The identifier to split
        
    Returns:
        List of words
    """
    # Handle snake_case
    if '_' in identifier:
        return identifier.lower().split('_')
    
    # Handle camelCase
    # This regex finds sequences of:
    # - A capital letter followed by lowercase letters
    # - Multiple capital letters (for acronyms)
    parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', identifier)
    return [p.lower() for p in parts]


def _extract_nouns_fallback(identifier: str) -> List[str]:
    """
    Fallback noun extraction when spaCy is not available.
    
    Uses simple heuristics to identify likely nouns.
    
    Args:
        identifier: The identifier to analyze
        
    Returns:
        List of likely nouns
    """
    words = _split_identifier(identifier)
    
    # Common verb prefixes that indicate the following word is likely a noun
    verb_prefixes = {'get', 'set', 'create', 'update', 'delete', 'find', 'add', 
                     'remove', 'list', 'fetch', 'save', 'load', 'read', 'write'}
    
    nouns = []
    skip_next = False
    
    for i, word in enumerate(words):
        if skip_next:
            skip_next = False
            continue
            
        # Skip if it's a known verb prefix
        if word in verb_prefixes:
            skip_next = False  # Don't skip the next word
            continue
            
        # Skip very short words
        if len(word) <= 2:
            continue
            
        # Likely a noun if it's not a common verb
        if word not in verb_prefixes:
            nouns.append(word)
    
    return nouns


def _extract_verbs_fallback(identifier: str) -> List[str]:
    """
    Fallback verb extraction when spaCy is not available.
    
    Uses a predefined list of common programming verbs.
    
    Args:
        identifier: The identifier to analyze
        
    Returns:
        List of likely verbs
    """
    words = _split_identifier(identifier)
    
    # Common verbs in programming contexts
    common_verbs = {
        'get', 'set', 'create', 'update', 'delete', 'remove', 'add',
        'find', 'search', 'list', 'fetch', 'save', 'load', 'read', 
        'write', 'process', 'handle', 'validate', 'check', 'verify',
        'calculate', 'compute', 'generate', 'build', 'make', 'parse',
        'render', 'display', 'show', 'hide', 'enable', 'disable',
        'start', 'stop', 'run', 'execute', 'initialize', 'setup',
        'cleanup', 'destroy', 'open', 'close', 'connect', 'disconnect'
    }
    
    return [word for word in words if word in common_verbs]