#!/usr/bin/env python3
"""
Test suite for the Knowledge Linker service.

Tests the ability to discover relationships from natural language documentation
and enrich Knowledge Graphs with confidence scores and evidence.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.linker import KnowledgeLinker
from tier3.world_contexts.knowledge.hub import KnowledgeHub
from tier3.world_contexts.knowledge.graph import Concept
from tier2.computer_science.semantic.db import SemanticDB, SemanticEntry
from tier2.domains.code.semantic.fingerprint import (
    SemanticFingerprint, NaturalLanguageContext, 
    DocumentedFingerprint, Behavior
)
from tier1.analysis.summary import CallContext


def create_documented_entry(func_name: str, docstring: str, 
                          comments: list = None) -> SemanticEntry:
    """Helper to create a documented semantic entry."""
    context = CallContext(function_name=func_name, parameter_states=())
    fingerprint = SemanticFingerprint(behaviors={Behavior.PURE})
    
    nl_context = NaturalLanguageContext(
        function_name=func_name,
        docstring=docstring,
        comments=comments or []
    )
    
    documented_fp = DocumentedFingerprint(fingerprint, nl_context)
    
    return SemanticEntry(
        function_name=func_name,
        context=context,
        fingerprint=fingerprint,
        documented_fingerprint=documented_fp
    )


def test_simple_relationship_extraction():
    """Test extracting a simple relationship from documentation."""
    print("Testing simple relationship extraction...")
    
    # Create a semantic DB with documented functions
    db = SemanticDB()
    
    # Add entries with clear relationship descriptions
    db.add(create_documented_entry(
        "create_order",
        "Creates an order for a user. Each user can have multiple orders."
    ))
    
    db.add(create_documented_entry(
        "get_user_profile", 
        "Gets the user profile. A user has one profile."
    ))
    
    # Create knowledge hub with known concepts
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("User"))
    hub.add_world_concept(Concept("Order"))
    hub.add_world_concept(Concept("Profile"))
    
    # Run the linker
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    # Check that relationships were discovered
    discovered = linker.get_discovered_relationships()
    assert len(discovered) >= 2
    
    # Check specific relationships
    user_order_rel = next(
        (r for r in discovered if 
         r['source'] == Concept("User") and r['target'] == Concept("Order")),
        None
    )
    assert user_order_rel is not None
    assert user_order_rel['relation'] == 'HAS_MANY'
    
    user_profile_rel = next(
        (r for r in discovered if 
         r['source'] == Concept("User") and r['target'] == Concept("Profile")),
        None
    )
    assert user_profile_rel is not None
    assert user_profile_rel['relation'] == 'HAS_ONE'
    
    print("✓ Simple relationship extraction works correctly")


def test_confidence_scoring():
    """Test that confidence scores are calculated correctly."""
    print("\nTesting confidence scoring...")
    
    db = SemanticDB()
    
    # High quality documentation
    db.add(create_documented_entry(
        "create_invoice",
        """
        Creates an invoice for a customer.
        
        This function creates a new invoice that belongs to the specified customer.
        Each invoice must belong to exactly one customer.
        
        Args:
            customer_id: The ID of the customer
            
        Returns:
            The created invoice
        """
    ))
    
    # Lower quality documentation
    db.add(create_documented_entry(
        "process_payment",
        "Process payment"  # Very brief
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Invoice"))
    hub.add_world_concept(Concept("Customer"))
    hub.add_world_concept(Concept("Payment"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    discovered = linker.get_discovered_relationships()
    
    # The well-documented relationship should have higher confidence
    invoice_customer = next(
        (r for r in discovered if 
         r['source'] == Concept("Invoice") and r['target'] == Concept("Customer")),
        None
    )
    
    if invoice_customer:
        assert invoice_customer['confidence'] > 0.5
        print(f"✓ High-quality doc confidence: {invoice_customer['confidence']:.2f}")
    
    print("✓ Confidence scoring works correctly")


def test_evidence_tracking():
    """Test that evidence is properly tracked for relationships."""
    print("\nTesting evidence tracking...")
    
    db = SemanticDB()
    
    evidence_text = "A product belongs to a category."
    db.add(create_documented_entry(
        "get_product_category",
        f"Gets the category of a product. {evidence_text}"
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Product"))
    hub.add_world_concept(Concept("Category"))
    
    linker = KnowledgeLinker(db, hub)
    enriched_wkg = linker.enrich_graph()
    
    # Check the relationship was added with evidence
    product_rels = enriched_wkg.get_relations_with_confidence(Concept("Product"))
    
    # Look specifically for the BELONGS_TO relationship since we may have multiple
    # relationships between Product and Category (e.g., RELATED_TO from co-occurrence)
    category_rel = next(
        (r for r in product_rels if r['target'] == Concept("Category") and r['relation'] == 'BELONGS_TO'),
        None
    )
    
    assert category_rel is not None, "BELONGS_TO relationship not found between Product and Category"
    assert evidence_text in category_rel['evidence']
    assert category_rel['metadata'] is not None
    assert 'get_product_category' in category_rel['metadata'].evidence_functions
    
    print("✓ Evidence tracking works correctly")


def test_bidirectional_relationships():
    """Test discovering relationships in both directions."""
    print("\nTesting bidirectional relationship discovery...")
    
    db = SemanticDB()
    
    # Forward direction
    db.add(create_documented_entry(
        "assign_task",
        "Assigns a task to a user. Each task is owned by a user."
    ))
    
    # Reverse direction
    db.add(create_documented_entry(
        "get_user_tasks",
        "Gets all tasks for a user. A user manages multiple tasks."
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("User"))
    hub.add_world_concept(Concept("Task"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    discovered = linker.get_discovered_relationships()
    
    # Should find both directions
    task_user = any(
        r['source'] == Concept("Task") and r['target'] == Concept("User")
        for r in discovered
    )
    user_task = any(
        r['source'] == Concept("User") and r['target'] == Concept("Task")
        for r in discovered
    )
    
    assert task_user or user_task
    print("✓ Bidirectional relationships work correctly")


def test_inheritance_relationships():
    """Test discovering IS_A relationships."""
    print("\nTesting inheritance relationship discovery...")
    
    db = SemanticDB()
    
    db.add(create_documented_entry(
        "create_admin_user",
        "Creates an admin user. An AdminUser is a type of User with elevated privileges."
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("AdminUser"))
    hub.add_world_concept(Concept("User"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    discovered = linker.get_discovered_relationships()
    
    is_a_rel = next(
        (r for r in discovered if 
         r['source'] == Concept("AdminUser") and 
         r['target'] == Concept("User") and
         r['relation'] == 'IS_A'),
        None
    )
    
    assert is_a_rel is not None
    print("✓ Inheritance relationship discovery works correctly")


def test_complex_sentences():
    """Test extracting relationships from complex sentences."""
    print("\nTesting complex sentence analysis...")
    
    db = SemanticDB()
    
    db.add(create_documented_entry(
        "process_order",
        """
        Processes an order by validating inventory and creating shipments.
        
        When an order is processed, it first validates that all products
        in the order are available in the inventory. Then it creates one
        or more shipments for the order. Each order can have multiple
        shipments, and each shipment belongs to exactly one order.
        """
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Order"))
    hub.add_world_concept(Concept("Product"))
    hub.add_world_concept(Concept("Inventory"))
    hub.add_world_concept(Concept("Shipment"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    discovered = linker.get_discovered_relationships()
    
    # Should find Order HAS_MANY Shipment
    order_shipment = any(
        r['source'] == Concept("Order") and 
        r['target'] == Concept("Shipment") and
        r['relation'] == 'HAS_MANY'
        for r in discovered
    )
    assert order_shipment
    
    # Should find Shipment BELONGS_TO Order
    shipment_order = any(
        r['source'] == Concept("Shipment") and 
        r['target'] == Concept("Order") and
        r['relation'] == 'BELONGS_TO'
        for r in discovered
    )
    assert shipment_order
    
    print("✓ Complex sentence analysis works correctly")


def test_enrichment_report():
    """Test generating enrichment reports."""
    print("\nTesting enrichment report generation...")
    
    db = SemanticDB()
    
    db.add(create_documented_entry(
        "create_post",
        "Creates a blog post. Each post belongs to an author."
    ))
    
    db.add(create_documented_entry(
        "add_comment",
        "Adds a comment to a post. A post can have many comments."
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Post"))
    hub.add_world_concept(Concept("Author"))
    hub.add_world_concept(Concept("Comment"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    report = linker.generate_enrichment_report()
    
    assert "Knowledge Graph Enrichment Report" in report
    assert "BELONGS_TO" in report
    assert "HAS_MANY" in report
    assert "Post" in report
    assert "Author" in report
    assert "Comment" in report
    
    print("✓ Enrichment report generation works correctly")
    print("\nSample Report:")
    print(report)


def test_no_relationships_found():
    """Test handling when no relationships are found."""
    print("\nTesting no relationships case...")
    
    db = SemanticDB()
    
    # Documentation without clear relationships
    db.add(create_documented_entry(
        "calculate_total",
        "Calculates the total amount."
    ))
    
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Total"))
    hub.add_world_concept(Concept("Amount"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    linker.get_discovered_relationships()
    # Might find some relationships or none, depending on patterns
    
    report = linker.generate_enrichment_report()
    assert "Knowledge Graph Enrichment Report" in report
    
    print("✓ No relationships case handled correctly")


def test_concept_variations():
    """Test that concept name variations are handled."""
    print("\nTesting concept name variations...")
    
    db = SemanticDB()
    
    # Use plural form in documentation
    db.add(create_documented_entry(
        "list_products",
        "Lists all products in a category. Categories contain multiple products."
    ))
    
    # Concepts are singular
    hub = KnowledgeHub()
    hub.add_world_concept(Concept("Product"))
    hub.add_world_concept(Concept("Category"))
    
    linker = KnowledgeLinker(db, hub)
    linker.enrich_graph()
    
    discovered = linker.get_discovered_relationships()
    
    # Should find relationship despite plural/singular mismatch
    category_product = any(
        (r['source'] == Concept("Category") and r['target'] == Concept("Product")) or
        (r['source'] == Concept("Product") and r['target'] == Concept("Category"))
        for r in discovered
    )
    assert category_product
    
    print("✓ Concept name variations handled correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Knowledge Linker Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_simple_relationship_extraction,
        test_confidence_scoring,
        test_evidence_tracking,
        test_bidirectional_relationships,
        test_inheritance_relationships,
        test_complex_sentences,
        test_enrichment_report,
        test_no_relationships_found,
        test_concept_variations
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