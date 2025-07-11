"""
Text processing utilities for RegionAI.

This module provides robust text processing functions including
pluralization and singularization using the inflect library.
"""
from functools import lru_cache
import inflect

# Create a cached instance of the inflect engine
@lru_cache(maxsize=1)
def _get_inflect_engine():
    """Get a cached instance of the inflect engine."""
    return inflect.engine()


def to_singular(word: str) -> str:
    """
    Convert a word to its singular form.
    
    If the word is already singular, it returns unchanged.
    Handles irregular plurals correctly (e.g., people -> person).
    
    Args:
        word: The word to singularize
        
    Returns:
        The singular form of the word
    """
    if not word:
        return word
        
    p = _get_inflect_engine()
    
    # Check if the word starts with uppercase
    is_capitalized = word[0].isupper() if word else False
    
    # Work with lowercase version
    word_lower = word.lower()
    
    # Special cases that inflect gets wrong
    if word_lower in ["process", "princess", "address", "access", "success"]:
        # These end in 'ss' but are singular
        return word
    
    # Try to get singular form
    singular = p.singular_noun(word_lower)
    
    if singular:
        # Check if the singular is reasonable
        # Sometimes inflect returns weird results like "proces"
        if word_lower.endswith("ss") and singular + "s" == word_lower:
            # This is likely a false positive
            result = word_lower
        else:
            # Word was plural, return the singular
            result = singular
    else:
        # Word is already singular (singular_noun returns False for singular words)
        result = word_lower
    
    # Restore capitalization if needed
    if is_capitalized and result:
        result = result.capitalize()
        
    return result


def to_plural(word: str) -> str:
    """
    Convert a word to its plural form.
    
    Handles regular and irregular plurals correctly:
    - cat -> cats
    - process -> processes  
    - person -> people
    - child -> children
    
    Args:
        word: The word to pluralize
        
    Returns:
        The plural form of the word
    """
    if not word:
        return word
        
    p = _get_inflect_engine()
    
    # Check if the word starts with uppercase
    is_capitalized = word[0].isupper() if word else False
    
    # Convert to lowercase for processing
    plural = p.plural(word.lower())
    
    # Restore capitalization if needed
    if is_capitalized and plural:
        plural = plural.capitalize()
        
    return plural


def is_plural(word: str) -> bool:
    """
    Check if a word is in plural form.
    
    Args:
        word: The word to check
        
    Returns:
        True if the word appears to be plural, False otherwise
    """
    if not word:
        return False
    
    # Special cases that inflect gets wrong
    word_lower = word.lower()
    if word_lower in ["process", "princess", "address", "access", "success"]:
        return False
        
    p = _get_inflect_engine()
    singular = p.singular_noun(word.lower())
    
    # Check for false positives
    if singular and word.lower().endswith("ss") and singular + "s" == word.lower():
        return False
        
    return singular is not False  # inflect returns False if word is already singular


def get_singular_plural_forms(word: str) -> tuple[str, str]:
    """
    Get both singular and plural forms of a word.
    
    Args:
        word: The input word (can be either singular or plural)
        
    Returns:
        A tuple of (singular_form, plural_form)
    """
    if is_plural(word):
        singular = to_singular(word)
        return (singular, word)
    else:
        plural = to_plural(word)
        return (word, plural)