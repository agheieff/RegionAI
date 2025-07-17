"""
Text processing utilities for RegionAI.

This module provides simple text processing functions including
basic pluralization and singularization.
"""


def to_singular(word: str) -> str:
    """
    Convert a word to its singular form using simple rules.
    
    If the word is already singular, it returns unchanged.
    Handles common cases but not all irregular forms.
    
    Args:
        word: The word to singularize
        
    Returns:
        The singular form of the word
    """
    if not word or len(word) < 2:
        return word
    
    # Check if the word starts with uppercase
    is_capitalized = word[0].isupper()
    
    # Work with lowercase version
    word_lower = word.lower()
    
    # Common irregular plurals
    irregular_plurals = {
        'people': 'person',
        'children': 'child',
        'men': 'man',
        'women': 'woman',
        'teeth': 'tooth',
        'feet': 'foot',
        'mice': 'mouse',
        'geese': 'goose',
    }
    
    if word_lower in irregular_plurals:
        result = irregular_plurals[word_lower]
    elif word_lower.endswith('ies') and len(word_lower) > 3:
        # flies -> fly, cities -> city
        result = word_lower[:-3] + 'y'
    elif word_lower.endswith('ves'):
        # leaves -> leaf, wives -> wife
        result = word_lower[:-3] + 'f'
    elif word_lower.endswith('es'):
        # Check for special cases
        if word_lower.endswith(('ses', 'sses', 'shes', 'ches', 'xes', 'zes')):
            # processes -> process, classes -> class, dishes -> dish
            result = word_lower[:-2]
        else:
            # Simple es -> e (like "games" -> "game")
            result = word_lower[:-1]
    elif word_lower.endswith('s') and not word_lower.endswith('ss'):
        # cats -> cat, but not process -> proces
        result = word_lower[:-1]
    else:
        # Assume it's already singular
        result = word_lower
    
    # Restore capitalization if needed
    if is_capitalized and result:
        result = result.capitalize()
        
    return result


def to_plural(word: str) -> str:
    """
    Convert a word to its plural form using simple rules.
    
    Handles common pluralization patterns:
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
    
    # Check if the word starts with uppercase
    is_capitalized = word[0].isupper()
    
    # Work with lowercase version
    word_lower = word.lower()
    
    # Common irregular singulars to plurals
    irregular_singulars = {
        'person': 'people',
        'child': 'children',
        'man': 'men',
        'woman': 'women',
        'tooth': 'teeth',
        'foot': 'feet',
        'mouse': 'mice',
        'goose': 'geese',
        'a': 'some',  # Article to quantifier
        # Unchanged plurals
        'sheep': 'sheep',
        'deer': 'deer',
        'fish': 'fish',
        'series': 'series',
    }
    
    if word_lower in irregular_singulars:
        result = irregular_singulars[word_lower]
    elif word_lower.endswith('y') and len(word_lower) > 1 and word_lower[-2] not in 'aeiou':
        # fly -> flies, city -> cities (but not day -> days)
        result = word_lower[:-1] + 'ies'
    elif word_lower.endswith(('s', 'ss', 'sh', 'ch', 'x', 'z')):
        # process -> processes, class -> classes, dish -> dishes
        result = word_lower + 'es'
    elif word_lower.endswith('f'):
        # leaf -> leaves
        result = word_lower[:-1] + 'ves'
    elif word_lower.endswith('fe'):
        # wife -> wives
        result = word_lower[:-2] + 'ves'
    else:
        # Default: just add 's'
        result = word_lower + 's'
    
    # Restore capitalization if needed
    if is_capitalized and result:
        result = result.capitalize()
        
    return result


def is_plural(word: str) -> bool:
    """
    Check if a word is in plural form using simple heuristics.
    
    Args:
        word: The word to check
        
    Returns:
        True if the word appears to be plural, False otherwise
    """
    if not word:
        return False
    
    word_lower = word.lower()
    
    # Known plurals
    known_plurals = {
        'people', 'children', 'men', 'women', 'teeth', 'feet', 'mice', 'geese'
    }
    if word_lower in known_plurals:
        return True
    
    # Special singular cases that look plural
    singular_endings = ["process", "princess", "address", "access", "success", "ness", "less"]
    for ending in singular_endings:
        if word_lower.endswith(ending):
            return False
    
    # Check if converting to singular and back gives the same word
    singular = to_singular(word)
    if singular != word:
        # Word changed when singularized, so it was likely plural
        return True
        
    return False


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


# For backward compatibility, provide a simple pluralize function
def pluralize(word: str) -> str:
    """
    Simple pluralization function for backward compatibility.
    
    Args:
        word: The word to pluralize
        
    Returns:
        The plural form of the word
    """
    return to_plural(word)