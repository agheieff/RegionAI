#!/usr/bin/env python3
"""
Test suite for the Concept Discovery service.

Tests the heuristics for discovering real-world concepts from code.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.discovery import ConceptDiscoverer
from tier3.world_contexts.knowledge.graph import Concept
from tier2.computer_science.semantic.db import SemanticDB, SemanticEntry
from tier2.domains.code.semantic.fingerprint import SemanticFingerprint, Behavior
from tier1.analysis.summary import CallContext


def create_test_semantic_db() -> SemanticDB:
    """Create a test SemanticDB with sample functions."""
    db = SemanticDB()
    
    # User CRUD functions
    user_functions = [
        ("create_user", {Behavior.MODIFIES_GLOBALS}),
        ("get_user", {Behavior.PURE}),
        ("update_user", {Behavior.MODIFIES_PARAMETERS}),
        ("delete_user", {Behavior.MODIFIES_GLOBALS}),
        ("get_user_by_email", {Behavior.PURE}),
        ("list_users", {Behavior.PURE}),
    ]
    
    # Product CRUD functions
    product_functions = [
        ("add_product", {Behavior.MODIFIES_GLOBALS}),
        ("fetch_product", {Behavior.PURE}),
        ("product_update", {Behavior.MODIFIES_PARAMETERS}),
        ("remove_product", {Behavior.MODIFIES_GLOBALS}),
        ("search_products", {Behavior.PURE}),
    ]
    
    # Order functions (partial CRUD)
    order_functions = [
        ("create_order", {Behavior.MODIFIES_GLOBALS}),
        ("get_order", {Behavior.PURE}),
        ("get_order_items", {Behavior.PURE}),
    ]
    
    # Validation functions
    validation_functions = [
        ("validate_email", {Behavior.VALIDATOR, Behavior.PURE}),
        ("is_valid_user", {Behavior.VALIDATOR, Behavior.PURE}),
        ("check_product_availability", {Behavior.VALIDATOR}),
    ]
    
    # Relationship functions
    relationship_functions = [
        ("get_user_orders", {Behavior.PURE}),
        ("get_order_user", {Behavior.PURE}),
        ("list_product_categories", {Behavior.PURE}),
    ]
    
    # Add all functions to the DB
    all_functions = (
        user_functions + product_functions + order_functions +
        validation_functions + relationship_functions
    )
    
    for func_name, behaviors in all_functions:
        context = CallContext(function_name=func_name, parameter_states=())
        fingerprint = SemanticFingerprint(behaviors=behaviors)
        entry = SemanticEntry(
            function_name=func_name,
            context=context,
            fingerprint=fingerprint
        )
        db.add(entry)
    
    return db


def test_crud_pattern_discovery():
    """Test discovering concepts through CRUD patterns."""
    print("Testing CRUD pattern discovery...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Discover CRUD patterns
    patterns = discoverer._discover_crud_patterns()
    
    # Should find User and Product as complete CRUD patterns
    assert len(patterns) >= 2
    
    # Find User pattern
    user_pattern = next((p for p in patterns if p.concept_name == "User"), None)
    assert user_pattern is not None
    assert "create_user" in user_pattern.create_functions
    assert "get_user" in user_pattern.read_functions
    assert "update_user" in user_pattern.update_functions
    assert "delete_user" in user_pattern.delete_functions
    assert user_pattern.completeness_score == 1.0  # All 4 CRUD operations
    
    # Find Product pattern
    product_pattern = next((p for p in patterns if p.concept_name == "Product"), None)
    assert product_pattern is not None
    assert "add_product" in product_pattern.create_functions
    assert "fetch_product" in product_pattern.read_functions
    assert product_pattern.completeness_score == 1.0
    
    # Order should have partial CRUD
    order_pattern = next((p for p in patterns if p.concept_name == "Order"), None)
    if order_pattern:
        assert order_pattern.completeness_score == 0.5  # Only create and read
    
    print("✓ CRUD pattern discovery works correctly")


def test_noun_extraction():
    """Test discovering concepts through noun extraction."""
    print("\nTesting noun extraction...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Discover by noun extraction
    concepts = discoverer._discover_by_noun_extraction()
    
    # Should find frequently mentioned nouns
    assert "User" in concepts or "user" in concepts
    assert "Product" in concepts or "product" in concepts
    assert "Order" in concepts or "order" in concepts
    
    # Check noun frequencies were tracked
    assert discoverer._noun_frequencies["user"] >= 5  # Appears in many functions
    assert discoverer._noun_frequencies["product"] >= 4
    assert discoverer._noun_frequencies["order"] >= 3
    
    print("✓ Noun extraction works correctly")


def test_behavior_based_discovery():
    """Test discovering concepts through behavior analysis."""
    print("\nTesting behavior-based discovery...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Discover by behaviors
    behavior_concepts = discoverer._discover_by_behaviors()
    
    # Should find concepts from validator functions
    assert "validator" in behavior_concepts
    validator_concepts = behavior_concepts["validator"]
    
    # Email and User should be discovered from validation functions
    assert any("Email" in c or "email" in c for c in validator_concepts)
    assert any("User" in c or "user" in c for c in validator_concepts)
    
    print("✓ Behavior-based discovery works correctly")


def test_relationship_discovery():
    """Test discovering relationships between concepts."""
    print("\nTesting relationship discovery...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Need to run full discovery to populate internal state
    discoverer.discover_concepts()
    
    # Discover relationships
    relationships = discoverer._discover_relationships()
    
    # Should find User-Order relationship
    user_order_rel = next(
        (r for r in relationships if 
         ("User" in r[0] and "Order" in r[1]) or 
         ("Order" in r[0] and "User" in r[1])),
        None
    )
    assert user_order_rel is not None
    
    print("✓ Relationship discovery works correctly")


def test_full_discovery_pipeline():
    """Test the complete discovery pipeline."""
    print("\nTesting full discovery pipeline...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Run full discovery
    kg = discoverer.discover_concepts()
    
    # Check discovered concepts
    concepts = kg.get_concepts()
    assert len(concepts) >= 3  # At least User, Product, Order
    
    # Verify User concept
    assert Concept("User") in kg
    user_meta = kg.get_concept_metadata(Concept("User"))
    assert user_meta is not None
    assert user_meta.belief > 0.5
    assert len(user_meta.source_functions) > 0
    
    # Verify Product concept
    assert Concept("Product") in kg
    product_meta = kg.get_concept_metadata(Concept("Product"))
    assert product_meta is not None
    
    # Check that relationships were discovered
    assert len(kg.graph.edges()) > 0
    
    print("✓ Full discovery pipeline works correctly")
    
    # Print the discovered graph
    print("\nDiscovered Knowledge Graph:")
    print(kg.visualize())


def test_discovery_report():
    """Test generating discovery reports."""
    print("\nTesting discovery report generation...")
    
    db = create_test_semantic_db()
    discoverer = ConceptDiscoverer(db)
    
    # Run discovery and generate report
    discoverer.discover_concepts()
    report = discoverer.generate_discovery_report()
    
    assert "Concept Discovery Report" in report
    assert "CRUD Patterns Discovered:" in report
    assert "User" in report
    assert "Product" in report
    assert "completeness:" in report
    assert "Top Nouns by Frequency:" in report
    
    print("✓ Discovery report generation works correctly")
    print("\nSample Discovery Report:")
    print(report)


def test_similar_concept_merging():
    """Test merging of similar concepts."""
    print("\nTesting similar concept merging...")
    
    # Create DB with potential duplicates
    db = SemanticDB()
    
    # Add both singular and plural forms
    for func_name in ["create_user", "create_users", "get_user", "get_users"]:
        context = CallContext(function_name=func_name, parameter_states=())
        fingerprint = SemanticFingerprint(behaviors={Behavior.PURE})
        entry = SemanticEntry(
            function_name=func_name,
            context=context,
            fingerprint=fingerprint
        )
        db.add(entry)
    
    discoverer = ConceptDiscoverer(db)
    kg = discoverer.discover_concepts()
    
    # Should merge Users into User
    concepts = kg.get_concepts()
    assert Concept("User") in concepts
    # Users should have been merged
    assert Concept("Users") not in concepts
    
    print("✓ Similar concept merging works correctly")


def test_empty_database():
    """Test discovery with empty database."""
    print("\nTesting empty database handling...")
    
    db = SemanticDB()
    discoverer = ConceptDiscoverer(db)
    
    kg = discoverer.discover_concepts()
    
    assert len(kg) == 0
    assert len(kg.graph.edges()) == 0
    
    report = discoverer.generate_discovery_report()
    assert "None found" in report
    
    print("✓ Empty database handling works correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Concept Discovery Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_crud_pattern_discovery,
        test_noun_extraction,
        test_behavior_based_discovery,
        test_relationship_discovery,
        test_full_discovery_pipeline,
        test_discovery_report,
        test_similar_concept_merging,
        test_empty_database
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print(f"\n✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)