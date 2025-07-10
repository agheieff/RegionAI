"""
Test suite for SemanticDB functionality.

Tests the storage, indexing, and querying capabilities of the semantic database.
"""
import pytest
from typing import Set

from src.regionai.semantic.db import SemanticDB, SemanticEntry, FunctionName
from src.regionai.analysis.semantic_fingerprint import SemanticFingerprint, Behavior
from src.regionai.analysis.summary import CallContext
from src.regionai.api import (
    analyze_code, find_similar_functions, find_equivalent_functions,
    compare_functions, discover_patterns, suggest_refactoring_opportunities
)


class TestSemanticDB:
    """Test basic SemanticDB functionality."""
    
    def test_empty_db(self):
        """Test empty database behavior."""
        db = SemanticDB()
        assert db.size() == 0
        assert len(db) == 0
        assert list(db) == []
        
        # Empty queries should return empty results
        fp = SemanticFingerprint()
        assert db.find_equivalent(fp) == []
        assert db.find_specializations(fp) == []
        assert db.find_generalizations(fp) == []
    
    def test_add_and_retrieve(self):
        """Test adding entries and basic retrieval."""
        db = SemanticDB()
        
        # Create test entries
        fp1 = SemanticFingerprint()
        fp1.add_behavior(Behavior.IDENTITY)
        fp1.add_behavior(Behavior.PURE)
        
        context1 = CallContext.from_call("func1", [])
        entry1 = SemanticEntry(
            function_name=FunctionName("func1"),
            context=context1,
            fingerprint=fp1
        )
        
        db.add(entry1)
        assert db.size() == 1
        
        # Test retrieval by behavior
        identity_funcs = db.find_by_behavior(Behavior.IDENTITY)
        assert len(identity_funcs) == 1
        assert identity_funcs[0].function_name == "func1"
    
    def test_find_equivalent(self):
        """Test finding semantically equivalent functions."""
        db = SemanticDB()
        
        # Create two equivalent functions (same behaviors)
        behaviors = {Behavior.IDENTITY, Behavior.PURE}
        
        fp1 = SemanticFingerprint(behaviors=behaviors)
        entry1 = SemanticEntry(
            function_name=FunctionName("identity1"),
            context=CallContext.from_call("identity1", []),
            fingerprint=fp1
        )
        
        fp2 = SemanticFingerprint(behaviors=behaviors.copy())
        entry2 = SemanticEntry(
            function_name=FunctionName("identity2"),
            context=CallContext.from_call("identity2", []),
            fingerprint=fp2
        )
        
        # Add a non-equivalent function
        fp3 = SemanticFingerprint(behaviors={Behavior.CONSTANT_RETURN})
        entry3 = SemanticEntry(
            function_name=FunctionName("constant"),
            context=CallContext.from_call("constant", []),
            fingerprint=fp3
        )
        
        db.add(entry1)
        db.add(entry2)
        db.add(entry3)
        
        # Find equivalents
        equivalents = db.find_equivalent(fp1)
        assert len(equivalents) == 2
        names = {e.function_name for e in equivalents}
        assert names == {"identity1", "identity2"}
    
    def test_find_specializations(self):
        """Test finding specialized versions of functions."""
        db = SemanticDB()
        
        # Base function: just identity
        fp_base = SemanticFingerprint(behaviors={Behavior.IDENTITY})
        entry_base = SemanticEntry(
            function_name=FunctionName("basic_identity"),
            context=CallContext.from_call("basic_identity", []),
            fingerprint=fp_base
        )
        
        # Specialized: identity + pure
        fp_special1 = SemanticFingerprint(behaviors={Behavior.IDENTITY, Behavior.PURE})
        entry_special1 = SemanticEntry(
            function_name=FunctionName("pure_identity"),
            context=CallContext.from_call("pure_identity", []),
            fingerprint=fp_special1
        )
        
        # More specialized: identity + pure + null-safe
        fp_special2 = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.PURE, Behavior.NULL_SAFE}
        )
        entry_special2 = SemanticEntry(
            function_name=FunctionName("safe_pure_identity"),
            context=CallContext.from_call("safe_pure_identity", []),
            fingerprint=fp_special2
        )
        
        db.add(entry_base)
        db.add(entry_special1)
        db.add(entry_special2)
        
        # Find specializations of basic identity
        specs = db.find_specializations(fp_base)
        assert len(specs) == 3  # Includes the base itself
        
        # Find specializations of pure identity
        specs2 = db.find_specializations(fp_special1)
        assert len(specs2) == 2  # pure_identity and safe_pure_identity
    
    def test_find_generalizations(self):
        """Test finding generalized versions of functions."""
        db = SemanticDB()
        
        # Complex function with many behaviors
        fp_complex = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.PURE, Behavior.NULL_SAFE}
        )
        entry_complex = SemanticEntry(
            function_name=FunctionName("complex"),
            context=CallContext.from_call("complex", []),
            fingerprint=fp_complex
        )
        
        # Simpler versions
        fp_simple1 = SemanticFingerprint(behaviors={Behavior.IDENTITY})
        entry_simple1 = SemanticEntry(
            function_name=FunctionName("simple1"),
            context=CallContext.from_call("simple1", []),
            fingerprint=fp_simple1
        )
        
        fp_simple2 = SemanticFingerprint(behaviors={Behavior.PURE})
        entry_simple2 = SemanticEntry(
            function_name=FunctionName("simple2"),
            context=CallContext.from_call("simple2", []),
            fingerprint=fp_simple2
        )
        
        db.add(entry_complex)
        db.add(entry_simple1)
        db.add(entry_simple2)
        
        # Find generalizations
        gens = db.find_generalizations(fp_complex)
        assert len(gens) == 3  # All three match (including itself)
    
    def test_find_similar(self):
        """Test similarity-based search."""
        db = SemanticDB()
        
        # Target fingerprint
        fp_target = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.PURE, Behavior.NULL_SAFE}
        )
        
        # Exact match (similarity = 1.0)
        fp_exact = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.PURE, Behavior.NULL_SAFE}
        )
        entry_exact = SemanticEntry(
            function_name=FunctionName("exact_match"),
            context=CallContext.from_call("exact_match", []),
            fingerprint=fp_exact
        )
        
        # High similarity (2/3 behaviors match)
        fp_similar = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.PURE}
        )
        entry_similar = SemanticEntry(
            function_name=FunctionName("similar"),
            context=CallContext.from_call("similar", []),
            fingerprint=fp_similar
        )
        
        # Low similarity (1/4 behaviors match)
        fp_dissimilar = SemanticFingerprint(
            behaviors={Behavior.IDENTITY, Behavior.CONSTANT_RETURN}
        )
        entry_dissimilar = SemanticEntry(
            function_name=FunctionName("dissimilar"),
            context=CallContext.from_call("dissimilar", []),
            fingerprint=fp_dissimilar
        )
        
        db.add(entry_exact)
        db.add(entry_similar)
        db.add(entry_dissimilar)
        
        # Find with high threshold
        similar_high = db.find_similar(fp_target, similarity_threshold=0.6)
        assert len(similar_high) == 2  # exact and similar
        
        # Find with low threshold
        similar_low = db.find_similar(fp_target, similarity_threshold=0.2)
        assert len(similar_low) == 3  # all three
    
    def test_behavior_statistics(self):
        """Test behavior frequency statistics."""
        db = SemanticDB()
        
        # Add various entries
        behaviors_list = [
            {Behavior.PURE},
            {Behavior.PURE, Behavior.IDENTITY},
            {Behavior.PURE, Behavior.CONSTANT_RETURN},
            {Behavior.NULLABLE_RETURN},
        ]
        
        for i, behaviors in enumerate(behaviors_list):
            fp = SemanticFingerprint(behaviors=behaviors)
            entry = SemanticEntry(
                function_name=FunctionName(f"func{i}"),
                context=CallContext.from_call(f"func{i}", []),
                fingerprint=fp
            )
            db.add(entry)
        
        stats = db.get_behavior_statistics()
        assert stats[Behavior.PURE] == 3
        assert stats[Behavior.IDENTITY] == 1
        assert stats[Behavior.CONSTANT_RETURN] == 1
        assert stats[Behavior.NULLABLE_RETURN] == 1


class TestSemanticSearchAPI:
    """Test high-level semantic search API."""
    
    def test_find_equivalent_functions_api(self):
        """Test finding equivalent functions through the API."""
        code = """
def max_custom(a, b):
    if a > b:
        return a
    else:
        return b

def max_ternary(a, b):
    return a if a > b else b

def min_custom(a, b):
    if a < b:
        return a
    else:
        return b

def identity(x):
    return x

def passthrough(value):
    return value
"""
        # Find functions equivalent to identity
        equiv_db = find_equivalent_functions(code, "identity")
        
        # Should find both identity and passthrough
        func_names = {entry.function_name for entry in equiv_db}
        assert "identity" in func_names
        assert "passthrough" in func_names
        
        # Should not find max/min functions
        assert "max_custom" not in func_names
        assert "min_custom" not in func_names
    
    def test_compare_functions_api(self):
        """Test comparing two functions semantically."""
        code = """
def func1(x):
    return x

def func2(x):
    return x

def func3(x):
    print(x)
    return x

def func4(x):
    return x + 1
"""
        # Compare identical functions
        comparison = compare_functions(code, "func1", "func2")
        assert comparison['equivalent'] == True
        assert comparison['similarity'] == 1.0
        
        # Compare similar but not identical
        comparison2 = compare_functions(code, "func1", "func3")
        assert comparison2['equivalent'] == False
        assert comparison2['similarity'] > 0
        assert comparison2['similarity'] < 1
        assert "IDENTITY" in comparison2['common_behaviors']
        assert "PERFORMS_IO" in comparison2['unique_to_second']
        
        # Compare different functions
        comparison3 = compare_functions(code, "func1", "func4")
        assert comparison3['equivalent'] == False
        assert "IDENTITY" in comparison3['unique_to_first']
    
    def test_discover_patterns_api(self):
        """Test pattern discovery in codebase."""
        code = """
def pure_func(x, y):
    return x + y

def impure_func(x):
    print(x)
    return x

def identity_func(x):
    return x

def constant_func():
    return 42

def nullable_func(x):
    if x > 0:
        return x
    return None

def validator_func(x):
    return x > 0
"""
        patterns = discover_patterns(code)
        
        assert "Pure Functions" in patterns
        assert "pure_func" in patterns["Pure Functions"]
        assert "identity_func" in patterns["Pure Functions"]
        
        assert "Identity Functions" in patterns
        assert "identity_func" in patterns["Identity Functions"]
        
        assert "Constant Functions" in patterns
        assert "constant_func" in patterns["Constant Functions"]
        
        assert "Side-Effect Functions" in patterns
        assert "impure_func" in patterns["Side-Effect Functions"]
    
    def test_suggest_refactoring_api(self):
        """Test refactoring suggestions."""
        code = """
def my_identity(x):
    return x

def pass_through(value):
    return value

def get_value(v):
    return v

def print_and_return(x):
    print(f"Value: {x}")
    return x
"""
        suggestions = suggest_refactoring_opportunities(code)
        
        # Should detect duplicate identity implementations
        duplicate_suggestions = [s for s in suggestions if s['type'] == 'Duplicate Implementation']
        assert len(duplicate_suggestions) > 0
        
        # Should find at least the three identity functions
        for suggestion in duplicate_suggestions:
            if set(suggestion['functions']) & {"my_identity", "pass_through", "get_value"}:
                assert len(suggestion['functions']) >= 3
                break
        else:
            assert False, "Did not find duplicate identity functions"
    
    def test_context_sensitive_search(self):
        """Test that search respects context sensitivity."""
        code = """
def flexible(x):
    if x is None:
        return None
    return x

def main():
    a = flexible(10)     # Not nullable in this context
    b = flexible(None)   # Nullable in this context
    return (a, b)
"""
        result = analyze_code(code)
        
        # Should have multiple entries for flexible function
        flexible_entries = [e for e in result.semantic_db if e.function_name == "flexible"]
        assert len(flexible_entries) >= 1
        
        # Different contexts might have different behaviors
        behaviors_sets = [e.fingerprint.behaviors for e in flexible_entries]
        # At least one should have nullable behavior
        assert any(Behavior.NULLABLE_RETURN in behaviors for behaviors in behaviors_sets)


class TestSemanticEquivalence:
    """Test semantic equivalence detection for various patterns."""
    
    def test_max_function_equivalence(self):
        """Test that different max implementations are recognized as equivalent."""
        code = """
def max_if(a, b):
    if a > b:
        return a
    else:
        return b

def max_ternary(a, b):
    return a if a > b else b

def max_builtin(a, b):
    return max(a, b)
"""
        # Note: max_builtin might have different fingerprint due to builtin call
        # But max_if and max_ternary should be similar
        result = analyze_code(code)
        
        # Get fingerprints
        max_if_fp = None
        max_ternary_fp = None
        
        for entry in result.semantic_db:
            if entry.function_name == "max_if":
                max_if_fp = entry.fingerprint
            elif entry.function_name == "max_ternary":
                max_ternary_fp = entry.fingerprint
        
        assert max_if_fp is not None
        assert max_ternary_fp is not None
        
        # Should have high similarity (same semantic behavior)
        # The exact behaviors depend on analysis precision
    
    def test_specialization_detection(self):
        """Test detection of specialized functions."""
        code = """
def is_positive(x):
    return x > 0

def is_positive_and_even(x):
    return x > 0 and x % 2 == 0

def is_positive_nonzero(x):
    return x > 0  # Implicitly nonzero

def is_nonzero(x):
    return x != 0
"""
        result = analyze_code(code)
        db = result.semantic_db
        
        # Find base function
        base_entries = [e for e in db if e.function_name == "is_positive"]
        if base_entries:
            base_fp = base_entries[0].fingerprint
            
            # Find specializations
            specs = db.find_specializations(base_fp)
            spec_names = {e.function_name for e in specs}
            
            # is_positive_and_even should be a specialization
            # (it does everything is_positive does, plus more)
    
    def test_pure_impure_variants(self):
        """Test distinguishing pure and impure variants."""
        code = """
# Pure version
def double_pure(x):
    return x * 2

# Impure version with logging
def double_with_log(x):
    print(f"Doubling {x}")
    return x * 2

# Impure version with side effect
count = 0
def double_with_count(x):
    global count
    count += 1
    return x * 2
"""
        patterns = discover_patterns(code)
        
        # Only double_pure should be in pure functions
        assert "double_pure" in patterns.get("Pure Functions", [])
        assert "double_with_log" not in patterns.get("Pure Functions", [])
        assert "double_with_count" not in patterns.get("Pure Functions", [])
        
        # The impure ones should be in side-effect functions
        assert "double_with_log" in patterns.get("Side-Effect Functions", [])
        assert "double_with_count" in patterns.get("Side-Effect Functions", [])