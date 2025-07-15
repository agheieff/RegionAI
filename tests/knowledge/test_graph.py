#!/usr/bin/env python3
"""
Test suite for the Knowledge Graph data structure.

Tests the core functionality of concept and relationship management.
"""
import sys
import os
import json
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.graph import (
    WorldKnowledgeGraph, Concept, Relation, 
    ConceptMetadata, RelationMetadata
)


def test_empty_graph():
    """Test creating and querying an empty graph."""
    print("Testing empty graph...")
    kg = WorldKnowledgeGraph()
    
    assert len(kg) == 0
    assert kg.get_concepts() == []
    assert str(kg) == "WorldKnowledgeGraph(0 concepts, 0 relationships)"
    print("✓ Empty graph works correctly")


def test_add_concept():
    """Test adding concepts to the graph."""
    print("\nTesting concept addition...")
    kg = WorldKnowledgeGraph()
    
    # Add concept without metadata
    kg.add_concept(Concept("User"))
    assert len(kg) == 1
    assert Concept("User") in kg
    assert Concept("Product") not in kg
    
    # Add concept with metadata
    metadata = ConceptMetadata(
        discovery_method="CRUD_PATTERN",
        alpha=9.0,  # Equivalent to confidence=0.9 (9/(9+1)=0.9)
        beta=1.0,
        source_functions=["create_user", "get_user", "update_user"]
    )
    kg.add_concept(Concept("Product"), metadata)
    
    assert len(kg) == 2
    assert Concept("Product") in kg
    
    # Verify metadata
    product_meta = kg.get_concept_metadata(Concept("Product"))
    assert product_meta is not None
    assert product_meta.discovery_method == "CRUD_PATTERN"
    assert product_meta.belief == pytest.approx(0.9, abs=0.05)  # Check belief is approximately 0.9
    assert len(product_meta.source_functions) == 3
    
    print("✓ Concept addition works correctly")


def test_add_relation():
    """Test adding relationships between concepts."""
    print("\nTesting relationship addition...")
    kg = WorldKnowledgeGraph()
    
    # Add relation (should auto-create concepts)
    kg.add_relation(Concept("User"), Concept("Order"), Relation("HAS_MANY"))
    
    assert len(kg) == 2
    assert Concept("User") in kg
    assert Concept("Order") in kg
    
    # Check relations
    user_relations = kg.get_relations(Concept("User"))
    assert len(user_relations) == 1
    source, target, relation = user_relations[0]
    assert source == Concept("User")
    assert target == Concept("Order")
    assert relation == Relation("HAS_MANY")
    
    # Add relation with metadata
    rel_metadata = RelationMetadata(
        relation_type="BELONGS_TO",
        alpha=5.67,  # Equivalent to confidence=0.85 (0.85/0.15≈5.67)
        beta=1.0,
        evidence_functions=["get_order_user", "find_user_by_order"]
    )
    kg.add_relation(Concept("Order"), Concept("User"), 
                   Relation("BELONGS_TO"), rel_metadata)
    
    # Check bidirectional relations
    order_relations = kg.get_relations(Concept("Order"))
    assert len(order_relations) == 2  # One incoming, one outgoing
    
    print("✓ Relationship addition works correctly")


def test_find_related_concepts():
    """Test finding related concepts."""
    print("\nTesting related concept discovery...")
    kg = WorldKnowledgeGraph()
    
    # Build a small graph
    kg.add_relation(Concept("User"), Concept("Order"), Relation("HAS_MANY"))
    kg.add_relation(Concept("User"), Concept("Address"), Relation("HAS_ONE"))
    kg.add_relation(Concept("Order"), Concept("Product"), Relation("CONTAINS"))
    kg.add_relation(Concept("Product"), Concept("Category"), Relation("BELONGS_TO"))
    
    # Find concepts related to User
    user_related = kg.find_related_concepts(Concept("User"))
    assert len(user_related) == 2
    assert Concept("Order") in user_related
    assert Concept("Address") in user_related
    
    # Find concepts with specific relation type
    has_many_related = kg.find_related_concepts(Concept("User"), "HAS_MANY")
    assert len(has_many_related) == 1
    assert Concept("Order") in has_many_related
    
    print("✓ Related concept discovery works correctly")


def test_concept_hierarchy():
    """Test hierarchical concept relationships."""
    print("\nTesting concept hierarchy...")
    kg = WorldKnowledgeGraph()
    
    # Build inheritance hierarchy
    kg.add_relation(Concept("Animal"), Concept("Mammal"), Relation("IS_A"))
    kg.add_relation(Concept("Animal"), Concept("Bird"), Relation("IS_A"))
    kg.add_relation(Concept("Mammal"), Concept("Dog"), Relation("IS_A"))
    kg.add_relation(Concept("Mammal"), Concept("Cat"), Relation("IS_A"))
    
    # Get hierarchy
    hierarchy = kg.get_concept_hierarchy(Concept("Animal"))
    assert Concept("Animal") in hierarchy
    assert len(hierarchy[Concept("Animal")]) == 2
    assert Concept("Mammal") in hierarchy
    assert len(hierarchy[Concept("Mammal")]) == 2
    
    print("✓ Concept hierarchy works correctly")


def test_merge_concepts():
    """Test merging similar concepts."""
    print("\nTesting concept merging...")
    kg = WorldKnowledgeGraph()
    
    # Create two similar concepts with different metadata
    meta1 = ConceptMetadata(
        discovery_method="CRUD_PATTERN",
        alpha=4.0,  # Equivalent to confidence=0.8 (0.8/0.2=4)
        beta=1.0,
        source_functions=["create_user", "get_user"]
    )
    meta2 = ConceptMetadata(
        discovery_method="NOUN_EXTRACTION",
        alpha=1.5,  # Equivalent to confidence=0.6 (0.6/0.4=1.5)
        beta=1.0,
        source_functions=["update_account", "delete_account"]
    )
    
    kg.add_concept(Concept("User"), meta1)
    kg.add_concept(Concept("Account"), meta2)
    
    # Add relations to both
    kg.add_relation(Concept("User"), Concept("Order"), Relation("HAS_MANY"))
    kg.add_relation(Concept("Account"), Concept("Profile"), Relation("HAS_ONE"))
    
    # Merge Account into User
    kg.merge_concepts(Concept("User"), Concept("Account"), Concept("User"))
    
    assert len(kg) == 3  # User, Order, Profile
    assert Concept("User") in kg
    assert Concept("Account") not in kg
    
    # Check merged metadata
    merged_meta = kg.get_concept_metadata(Concept("User"))
    assert len(merged_meta.source_functions) == 4
    assert merged_meta.belief == pytest.approx(0.82, abs=0.02)  # Combined belief (4.5/5.5≈0.82)
    
    # Check relations were transferred
    user_relations = kg.get_relations(Concept("User"))
    print(f"User relations after merge: {user_relations}")
    # Should have both HAS_MANY to Order and HAS_ONE to Profile
    assert len(user_relations) >= 2  # At least both relations
    
    print("✓ Concept merging works correctly")


def test_json_serialization():
    """Test JSON export and import."""
    print("\nTesting JSON serialization...")
    kg1 = WorldKnowledgeGraph()
    
    # Build a graph
    meta = ConceptMetadata(
        discovery_method="CRUD_PATTERN",
        alpha=9.0,  # Equivalent to confidence=0.9 (9/(9+1)=0.9)
        beta=1.0,
        source_functions=["create_product", "get_product"],
        related_behaviors={"PURE", "VALIDATOR"}
    )
    kg1.add_concept(Concept("Product"), meta)
    kg1.add_relation(Concept("Product"), Concept("Category"), 
                    Relation("BELONGS_TO"))
    
    # Export to JSON
    json_str = kg1.to_json()
    data = json.loads(json_str)
    
    assert "Product" in data["concepts"]
    assert len(data["relations"]) == 1
    assert data["relations"][0]["source"] == "Product"
    assert data["relations"][0]["target"] == "Category"
    
    # Import from JSON
    kg2 = WorldKnowledgeGraph()
    kg2.from_json(json_str)
    
    assert len(kg2) == len(kg1)
    assert Concept("Product") in kg2
    assert Concept("Category") in kg2
    
    # Check metadata was preserved
    imported_meta = kg2.get_concept_metadata(Concept("Product"))
    assert imported_meta.discovery_method == "CRUD_PATTERN"
    assert imported_meta.belief == pytest.approx(0.9, abs=0.01)
    
    print("✓ JSON serialization works correctly")


def test_visualization():
    """Test text visualization of the graph."""
    print("\nTesting visualization...")
    kg = WorldKnowledgeGraph()
    
    # Build a simple graph
    meta = ConceptMetadata(
        discovery_method="CRUD_PATTERN",
        alpha=19.0,  # Equivalent to confidence=0.95 (0.95/0.05=19)
        beta=1.0,
        source_functions=["create_user", "get_user", "update_user"]
    )
    kg.add_concept(Concept("User"), meta)
    kg.add_relation(Concept("User"), Concept("Order"), Relation("HAS_MANY"))
    
    # Get visualization
    viz = kg.visualize()
    
    assert "Knowledge Graph Summary:" in viz
    assert "Concepts: 2" in viz
    assert "Relations: 1" in viz
    assert "User" in viz
    assert "CRUD_PATTERN" in viz
    assert "0.95" in viz or "Belief: 0.95" in viz
    assert "-> HAS_MANY -> Order" in viz
    
    print("✓ Visualization works correctly")
    print("\nSample visualization:")
    print(viz)


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Knowledge Graph Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_empty_graph,
        test_add_concept,
        test_add_relation,
        test_find_related_concepts,
        test_concept_hierarchy,
        test_merge_concepts,
        test_json_serialization,
        test_visualization
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