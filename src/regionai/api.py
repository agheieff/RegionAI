"""
High-level API for RegionAI semantic analysis and search.

This module provides user-friendly functions for analyzing code and
discovering semantic relationships between functions.
"""
import ast
from typing import List, Optional, Dict, Tuple

from .analysis.interprocedural import InterproceduralAnalyzer, AnalysisResult
from .semantic.db import SemanticDB, SemanticEntry, FunctionName
from .analysis.semantic_fingerprint import SemanticFingerprint, Behavior


def analyze_code(code: str) -> AnalysisResult:
    """
    Analyze a Python codebase and return comprehensive results.
    
    Args:
        code: Python source code to analyze
        
    Returns:
        AnalysisResult containing summaries, fingerprints, and semantic database
    """
    tree = ast.parse(code)
    analyzer = InterproceduralAnalyzer()
    return analyzer.analyze_program(tree)


def find_similar_functions(code: str, target_function_name: str,
                          similarity_threshold: float = 0.5) -> SemanticDB:
    """
    Analyze a codebase and find functions semantically similar to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find similar matches for
        similarity_threshold: Minimum similarity score (0-1) for matches
        
    Returns:
        SemanticDB containing only similar functions
    """
    # Run full analysis
    result = analyze_code(code)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Find the target function's fingerprint(s)
    target_entries = []
    for entry in result.semantic_db:
        if entry.function_name == target_function_name:
            target_entries.append(entry)
    
    if not target_entries:
        raise ValueError(f"Function '{target_function_name}' not found in code")
    
    # Create new DB for results
    similar_db = SemanticDB()
    
    # For each variant of the target function, find similar functions
    seen = set()
    for target_entry in target_entries:
        similar = result.semantic_db.find_similar(
            target_entry.fingerprint, 
            similarity_threshold
        )
        
        for entry, score in similar:
            # Avoid duplicates
            key = (entry.function_name, frozenset(entry.fingerprint.behaviors))
            if key not in seen:
                seen.add(key)
                similar_db.add(entry)
    
    return similar_db


def find_equivalent_functions(code: str, target_function_name: str) -> SemanticDB:
    """
    Find all functions that are semantically equivalent to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find equivalents for
        
    Returns:
        SemanticDB containing only equivalent functions
    """
    # Run full analysis
    result = analyze_code(code)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Find the target function's fingerprint(s)
    target_entries = []
    for entry in result.semantic_db:
        if entry.function_name == target_function_name:
            target_entries.append(entry)
    
    if not target_entries:
        raise ValueError(f"Function '{target_function_name}' not found in code")
    
    # Create new DB for results
    equivalent_db = SemanticDB()
    
    # Find exact matches for each variant
    seen = set()
    for target_entry in target_entries:
        equivalents = result.semantic_db.find_equivalent(target_entry.fingerprint)
        
        for entry in equivalents:
            # Avoid duplicates
            key = (entry.function_name, frozenset(entry.fingerprint.behaviors))
            if key not in seen:
                seen.add(key)
                equivalent_db.add(entry)
    
    return equivalent_db


def find_functions_by_behavior(code: str, behavior: Behavior) -> SemanticDB:
    """
    Find all functions that exhibit a specific behavior.
    
    Args:
        code: Python source code to analyze
        behavior: The behavior to search for
        
    Returns:
        SemanticDB containing matching functions
    """
    result = analyze_code(code)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Create new DB for results
    behavior_db = SemanticDB()
    
    for entry in result.semantic_db.find_by_behavior(behavior):
        behavior_db.add(entry)
    
    return behavior_db


def find_pure_functions(code: str) -> SemanticDB:
    """Find all pure functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.PURE)


def find_identity_functions(code: str) -> SemanticDB:
    """Find all identity functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.IDENTITY)


def find_nullable_functions(code: str) -> SemanticDB:
    """Find all functions that may return None."""
    return find_functions_by_behavior(code, Behavior.NULLABLE_RETURN)


def compare_functions(code: str, func1_name: str, func2_name: str) -> Dict[str, any]:
    """
    Compare two functions semantically.
    
    Args:
        code: Python source code containing both functions
        func1_name: Name of first function
        func2_name: Name of second function
        
    Returns:
        Dictionary with comparison results including:
        - equivalent: bool indicating if functions are semantically equivalent
        - similarity: float similarity score (0-1)
        - common_behaviors: list of shared behaviors
        - unique_to_first: behaviors only in first function
        - unique_to_second: behaviors only in second function
    """
    result = analyze_code(code)
    
    if not result.semantic_db:
        raise ValueError("Analysis failed")
    
    # Find entries for both functions
    func1_entries = [e for e in result.semantic_db if e.function_name == func1_name]
    func2_entries = [e for e in result.semantic_db if e.function_name == func2_name]
    
    if not func1_entries:
        raise ValueError(f"Function '{func1_name}' not found")
    if not func2_entries:
        raise ValueError(f"Function '{func2_name}' not found")
    
    # For simplicity, compare the first variant of each
    # In a more sophisticated implementation, we might compare all variants
    fp1 = func1_entries[0].fingerprint
    fp2 = func2_entries[0].fingerprint
    
    comparison = {
        'equivalent': fp1.behaviors == fp2.behaviors,
        'similarity': len(fp1.behaviors & fp2.behaviors) / max(len(fp1.behaviors | fp2.behaviors), 1),
        'common_behaviors': sorted([b.name for b in (fp1.behaviors & fp2.behaviors)]),
        'unique_to_first': sorted([b.name for b in (fp1.behaviors - fp2.behaviors)]),
        'unique_to_second': sorted([b.name for b in (fp2.behaviors - fp1.behaviors)])
    }
    
    return comparison


def discover_patterns(code: str) -> Dict[str, List[str]]:
    """
    Discover common patterns in the codebase.
    
    Returns a dictionary mapping pattern names to lists of functions
    that exhibit those patterns.
    """
    result = analyze_code(code)
    
    if not result.semantic_db:
        return {}
    
    patterns = {
        'Pure Functions': [],
        'Identity Functions': [],
        'Constant Functions': [],
        'Nullable Functions': [],
        'Safe Functions': [],
        'Validators': [],
        'Side-Effect Functions': [],
    }
    
    for entry in result.semantic_db:
        fp = entry.fingerprint
        func = entry.function_name
        
        if fp.is_pure():
            patterns['Pure Functions'].append(func)
        if Behavior.IDENTITY in fp.behaviors:
            patterns['Identity Functions'].append(func)
        if Behavior.CONSTANT_RETURN in fp.behaviors:
            patterns['Constant Functions'].append(func)
        if Behavior.NULLABLE_RETURN in fp.behaviors:
            patterns['Nullable Functions'].append(func)
        if fp.is_safe():
            patterns['Safe Functions'].append(func)
        if Behavior.VALIDATOR in fp.behaviors:
            patterns['Validators'].append(func)
        if (Behavior.MODIFIES_GLOBALS in fp.behaviors or 
            Behavior.MODIFIES_PARAMETERS in fp.behaviors or
            Behavior.PERFORMS_IO in fp.behaviors):
            patterns['Side-Effect Functions'].append(func)
    
    # Remove duplicates and sort
    for pattern in patterns:
        patterns[pattern] = sorted(list(set(patterns[pattern])))
    
    # Remove empty patterns
    return {k: v for k, v in patterns.items() if v}


def suggest_refactoring_opportunities(code: str) -> List[Dict[str, any]]:
    """
    Analyze code and suggest refactoring opportunities based on semantic patterns.
    
    Returns a list of suggestions, each containing:
    - type: The type of refactoring opportunity
    - functions: Functions involved
    - description: Explanation of the opportunity
    """
    result = analyze_code(code)
    suggestions = []
    
    if not result.semantic_db:
        return suggestions
    
    # Find duplicate implementations
    seen_fingerprints = {}
    for entry in result.semantic_db:
        fp_key = frozenset(entry.fingerprint.behaviors)
        if fp_key not in seen_fingerprints:
            seen_fingerprints[fp_key] = []
        seen_fingerprints[fp_key].append(entry.function_name)
    
    # Suggest consolidating duplicate implementations
    for fp_key, functions in seen_fingerprints.items():
        if len(functions) > 1:
            suggestions.append({
                'type': 'Duplicate Implementation',
                'functions': sorted(list(set(functions))),
                'description': f"These {len(set(functions))} functions have identical semantic behavior and could potentially be consolidated"
            })
    
    # Find functions that could use library replacements
    for entry in result.semantic_db:
        if (Behavior.IDENTITY in entry.fingerprint.behaviors and 
            entry.function_name not in ['identity', 'id']):
            suggestions.append({
                'type': 'Use Built-in',
                'functions': [entry.function_name],
                'description': "This identity function could potentially be replaced with direct parameter passing"
            })
    
    # Find impure functions that could be made pure
    for entry in result.semantic_db:
        fp = entry.fingerprint
        if (not fp.is_pure() and 
            Behavior.PERFORMS_IO not in fp.behaviors and
            Behavior.MODIFIES_GLOBALS not in fp.behaviors):
            suggestions.append({
                'type': 'Make Pure',
                'functions': [entry.function_name],
                'description': "This function modifies parameters but could potentially be refactored to be pure"
            })
    
    return suggestions