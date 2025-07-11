#!/usr/bin/env python3
"""
Tests for the DocumentationGenerator class.

Verifies that the system can generate human-readable summaries
of functions based on the semantic understanding in the Knowledge Graph.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.knowledge.graph import WorldKnowledgeGraph, Concept, ConceptMetadata
from regionai.language.doc_generator import DocumentationGenerator


def test_basic_summary_generation():
    """Test basic summary generation for a function."""
    print("Testing basic summary generation...")
    
    # Create a test knowledge graph
    kg = WorldKnowledgeGraph()
    
    # Add concepts with varying confidence scores
    concepts = [
        ("Customer", 0.9, "CRUD_PATTERN"),
        ("Order", 0.85, "NOUN_EXTRACTION"),
        ("Product", 0.7, "NOUN_EXTRACTION"),
        ("Database", 0.6, "NOUN_EXTRACTION"),
        ("Query", 0.5, "NOUN_EXTRACTION"),
    ]
    
    for name, confidence, method in concepts:
        # Calculate alpha/beta from confidence
        if confidence >= 0.99:
            alpha = 99.0
            beta = 1.0
        else:
            alpha = confidence / (1 - confidence)
            beta = 1.0
            
        metadata = ConceptMetadata(
            discovery_method=method,
            alpha=alpha,
            beta=beta,
            source_functions=["get_customer_orders"]
        )
        kg.add_concept(Concept(name), metadata)
    
    # Create documentation generator
    doc_gen = DocumentationGenerator(kg)
    
    # Generate summary
    summary = doc_gen.generate_summary("get_customer_orders")
    
    print(f"Generated summary: {summary}")
    
    # Debug: Check what concepts were found
    found_concepts = doc_gen._find_function_concepts("get_customer_orders")
    print(f"Found concepts: {found_concepts}")
    
    # Verify the summary mentions the top concepts found in the function name
    assert "Customer" in summary, "Summary should mention Customer (highest confidence)"
    assert "Order" in summary, "Summary should mention Order (second highest)"
    # Note: Product and Database aren't in the function name, so they won't be found
    # unless we have relationships set up
    
    # Verify proper grammar
    assert summary.startswith("This function appears to be primarily concerned with")
    assert summary.endswith(".")
    
    print("✓ Basic summary generation works correctly")


def test_single_concept_summary():
    """Test summary generation when only one concept is found."""
    print("\nTesting single concept summary...")
    
    kg = WorldKnowledgeGraph()
    
    # Add just one concept
    metadata = ConceptMetadata(
        discovery_method="NOUN_EXTRACTION",
        alpha=4.0,  # confidence = 0.8
        beta=1.0
    )
    kg.add_concept(Concept("User"), metadata)
    
    doc_gen = DocumentationGenerator(kg)
    summary = doc_gen.generate_summary("create_user")
    
    print(f"Generated summary: {summary}")
    
    assert "User" in summary
    assert "confidence: 0.80" in summary  # Should show confidence
    assert "concept of User" in summary  # Singular form
    
    print("✓ Single concept summary works correctly")


def test_no_concepts_summary():
    """Test summary generation when no concepts are found."""
    print("\nTesting no concepts summary...")
    
    # Empty knowledge graph
    kg = WorldKnowledgeGraph()
    
    doc_gen = DocumentationGenerator(kg)
    summary = doc_gen.generate_summary("unknown_function")
    
    print(f"Generated summary: {summary}")
    
    assert "no identified concepts" in summary
    assert "unknown_function" in summary
    
    print("✓ No concepts summary works correctly")


def test_concept_ordering():
    """Test that concepts are ordered by confidence in the summary."""
    print("\nTesting concept ordering by confidence...")
    
    kg = WorldKnowledgeGraph()
    
    # Add concepts with specific confidence scores (more than 5 to test limiting)
    concepts = [
        ("Low", 0.3),
        ("High", 0.95),
        ("Medium", 0.6),
        ("VeryHigh", 0.99),
        ("VeryLow", 0.1),
        ("MediumHigh", 0.75),
        ("MediumLow", 0.45),
    ]
    
    for name, confidence in concepts:
        if confidence >= 0.99:
            alpha = 99.0
        else:
            alpha = confidence / (1 - confidence)
        beta = 1.0
        
        metadata = ConceptMetadata(
            discovery_method="TEST",
            alpha=alpha,
            beta=beta,
            source_functions=["test_function"]
        )
        kg.add_concept(Concept(name), metadata)
    
    doc_gen = DocumentationGenerator(kg)
    summary = doc_gen.generate_summary("test_function")
    
    print(f"Generated summary: {summary}")
    
    # Debug what was found
    found = doc_gen._find_function_concepts("test_function")
    print(f"Found concepts for ordering test: {found}")
    
    # Extract the order of concepts from the summary
    veryhigh_pos = summary.find("VeryHigh")
    high_pos = summary.find("High")
    medium_pos = summary.find("Medium")
    
    # VeryHigh should appear before High
    assert veryhigh_pos < high_pos, "VeryHigh (0.99) should appear before High (0.95)"
    # High should appear before Medium
    assert high_pos < medium_pos, "High (0.95) should appear before Medium (0.6)"
    # Low and VeryLow shouldn't appear (not in top 5 concepts)
    assert "Low" not in summary or summary.find("Low") > summary.find("MediumLow"), \
        "Low (0.3) should not appear in top 5 concepts"
    assert "VeryLow" not in summary, "VeryLow (0.1) should not appear in top concepts"
    
    print("✓ Concepts are correctly ordered by confidence")


def test_function_name_parsing():
    """Test that function names are properly parsed to find concepts."""
    print("\nTesting function name parsing...")
    
    kg = WorldKnowledgeGraph()
    
    # Add concepts that match parts of a function name
    for concept_name in ["Customer", "Order", "Details"]:
        metadata = ConceptMetadata(
            discovery_method="NOUN_EXTRACTION",
            alpha=3.0,  # confidence = 0.75
            beta=1.0
        )
        kg.add_concept(Concept(concept_name), metadata)
    
    doc_gen = DocumentationGenerator(kg)
    
    # Test with camelCase
    summary = doc_gen.generate_summary("getCustomerOrderDetails")
    print(f"CamelCase summary: {summary}")
    assert "Customer" in summary and "Order" in summary and "Details" in summary
    
    # Test with snake_case
    summary = doc_gen.generate_summary("get_customer_order_details")
    print(f"Snake_case summary: {summary}")
    assert "Customer" in summary and "Order" in summary and "Details" in summary
    
    print("✓ Function name parsing works for both camelCase and snake_case")


def test_api_integration():
    """Test the API endpoint for documentation generation."""
    print("\nTesting API integration...")
    
    from regionai.pipeline.api import generate_docs_for_function
    
    # Test with inline code
    code = '''
def calculate_order_total(order_id):
    """Calculate the total price for an order including tax and shipping."""
    order = get_order(order_id)
    subtotal = sum(item.price * item.quantity for item in order.items)
    tax = subtotal * 0.08
    shipping = calculate_shipping(order.weight)
    return subtotal + tax + shipping
'''
    
    summary = generate_docs_for_function('calculate_order_total', code)
    print(f"API generated summary: {summary}")
    
    # Should mention Order and related concepts
    assert "Order" in summary or "order" in summary
    assert "function appears to be primarily concerned with" in summary
    
    # Test error case
    error_summary = generate_docs_for_function('test_func')
    assert "Error:" in error_summary
    
    print("✓ API integration works correctly")


def test_behavioral_summary_generation():
    """Test behavioral summary generation with actions."""
    print("\nTesting behavioral summary generation...")
    
    # Create a test knowledge graph with concepts and actions
    kg = WorldKnowledgeGraph()
    
    # Add concepts
    concepts = [
        ("Customer", 0.9),
        ("Data", 0.8),
        ("Order", 0.7),
    ]
    
    for name, confidence in concepts:
        alpha = confidence / (1 - confidence) if confidence < 0.99 else 99.0
        metadata = ConceptMetadata(
            discovery_method="TEST",
            alpha=alpha,
            beta=1.0,
            source_functions=["manage_customer_data"]
        )
        kg.add_concept(Concept(name), metadata)
    
    # Add action concepts
    actions = ["Load", "Save", "Validate", "Process"]
    for action in actions:
        action_metadata = ConceptMetadata(
            discovery_method="ACTION_VERB",
            alpha=1.0,
            beta=1.0,
            properties={'is_action': True}
        )
        kg.add_concept(Concept(action), action_metadata)
    
    # Add PERFORMS relationships with varying confidence
    from regionai.knowledge.graph import RelationMetadata, Relation
    
    # Customer performs Load (high confidence)
    kg.add_relation(
        Concept("Customer"), Concept("Load"), Relation("PERFORMS"),
        metadata=RelationMetadata(relation_type="PERFORMS", alpha=4.0, beta=1.0),
        confidence=0.8
    )
    
    # Customer performs Save (high confidence)
    kg.add_relation(
        Concept("Customer"), Concept("Save"), Relation("PERFORMS"),
        metadata=RelationMetadata(relation_type="PERFORMS", alpha=3.5, beta=1.0),
        confidence=0.78
    )
    
    # Customer performs Process (lower confidence)
    kg.add_relation(
        Concept("Customer"), Concept("Process"), Relation("PERFORMS"),
        metadata=RelationMetadata(relation_type="PERFORMS", alpha=2.0, beta=1.0),
        confidence=0.67
    )
    
    # Data performs Validate
    kg.add_relation(
        Concept("Data"), Concept("Validate"), Relation("PERFORMS"),
        metadata=RelationMetadata(relation_type="PERFORMS", alpha=3.0, beta=1.0),
        confidence=0.75
    )
    
    # Create doc generator and generate behavioral summary
    doc_gen = DocumentationGenerator(kg)
    summary = doc_gen.generate_behavioral_summary("manage_customer_data")
    
    print(f"Generated behavioral summary: {summary}")
    
    # Verify the summary structure
    assert "This function focuses on" in summary
    assert "customer" in summary.lower()
    assert "load" in summary.lower()
    assert "save" in summary.lower()
    assert "data" in summary.lower()
    assert "validate" in summary.lower()
    
    # Should NOT include low-confidence action
    assert "process" not in summary.lower()
    
    print("✓ Behavioral summary generation works correctly")


def test_behavioral_summary_no_actions():
    """Test behavioral summary when concepts have no actions."""
    print("\nTesting behavioral summary with no actions...")
    
    kg = WorldKnowledgeGraph()
    
    # Add concepts without actions
    metadata = ConceptMetadata(
        discovery_method="TEST",
        alpha=3.0,
        beta=1.0,
        source_functions=["test_function"]
    )
    kg.add_concept(Concept("Widget"), metadata)
    
    doc_gen = DocumentationGenerator(kg)
    summary = doc_gen.generate_behavioral_summary("test_function")
    
    print(f"Summary without actions: {summary}")
    
    # Should still generate a summary mentioning the concept
    assert "widget" in summary.lower()
    assert "This function focuses on" in summary
    
    print("✓ Behavioral summary handles concepts without actions")


def test_behavioral_api_integration():
    """Test the behavioral documentation API."""
    print("\nTesting behavioral API integration...")
    
    from regionai.pipeline.api import generate_behavioral_docs_for_function
    
    # Test with inline code that will trigger action discovery
    code = '''
def manage_customer_data(customer_id):
    """Manage customer data operations."""
    customer = load_customer(customer_id)
    customer.validate()
    customer.update_preferences()
    save_customer(customer)
    
    # Also process related data
    data = get_customer_data(customer_id)
    data.clean()
    return data
'''
    
    summary = generate_behavioral_docs_for_function('manage_customer_data', code)
    print(f"API generated behavioral summary: {summary}")
    
    # Should describe behaviors
    assert "function focuses on" in summary or "function appears to be" in summary
    
    print("✓ Behavioral API integration works correctly")


def run_all_tests():
    """Run all documentation generator tests."""
    print("=" * 60)
    print("Documentation Generator Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_basic_summary_generation,
        test_single_concept_summary,
        test_no_concepts_summary,
        test_concept_ordering,
        test_function_name_parsing,
        test_api_integration,
        test_behavioral_summary_generation,
        test_behavioral_summary_no_actions,
        test_behavioral_api_integration
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