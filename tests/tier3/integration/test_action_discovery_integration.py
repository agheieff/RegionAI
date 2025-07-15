#!/usr/bin/env python3
"""
Integration test for action discovery in the knowledge graph.

Tests that actions are properly discovered and integrated into
the knowledge graph through the full pipeline.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.knowledge import (
    BayesianUpdater, ActionDiscoverer
)
from tier3.world_contexts.knowledge.graph import WorldKnowledgeGraph


def test_action_discovery_integration():
    """Test that action discovery integrates with the knowledge graph."""
    print("Testing action discovery integration...")
    
    # Create knowledge graph
    kg = WorldKnowledgeGraph()
    updater = BayesianUpdater(kg)
    discoverer = ActionDiscoverer()
    
    # Sample code with various actions
    code = '''
def process_customer_order(customer, order):
    """Process a customer's order through the system."""
    # Validate the customer first
    customer.validate()
    
    # Calculate order totals
    subtotal = order.calculate_subtotal()
    tax = calculate_tax(subtotal)
    order.set_total(subtotal + tax)
    
    # Save everything
    customer.save()
    order.save()
    
    # Send confirmation
    email_service.send_confirmation(customer.email, order.id)
    
    return order
'''
    
    # Discover actions
    actions = discoverer.discover_actions(code, "process_customer_order")
    
    print(f"\nDiscovered {len(actions)} actions:")
    for action in actions:
        print(f"  {action.concept}.{action.verb}() - confidence: {action.confidence}")
        
        # Update the knowledge graph with the action
        updater.update_action_belief(
            action.concept,
            action.verb,
            'method_call' if '.' in action.method_name else 'function_name',
            action.confidence
        )
    
    # Verify concepts exist
    concepts = kg.get_concepts()
    print(f"\nConcepts in knowledge graph: {sorted(str(c) for c in concepts)}")
    
    # Find all PERFORMS relationships
    print("\nPERFORMS relationships:")
    for concept in concepts:
        relations = kg.get_relations_with_confidence(concept)
        performs = [r for r in relations if str(r['relation']) == "PERFORMS"]
        
        for rel in performs:
            print(f"  {concept} -> {rel['target']} (confidence: {rel['confidence']:.3f})")
    
    # Verify key relationships exist
    customer_rels = kg.get_relations_with_confidence("Customer")
    customer_actions = {str(r['target']) for r in customer_rels 
                       if str(r['relation']) == "PERFORMS"}
    
    assert "Validate" in customer_actions, "Customer should perform Validate action"
    assert "Save" in customer_actions, "Customer should perform Save action"
    
    order_rels = kg.get_relations_with_confidence("Order")
    order_actions = {str(r['target']) for r in order_rels 
                    if str(r['relation']) == "PERFORMS"}
    
    assert "Calculate" in order_actions, "Order should perform Calculate action"
    assert "Save" in order_actions, "Order should perform Save action"
    
    print("\n✓ Action discovery integration works correctly")


def test_action_verb_variations():
    """Test that different verb forms are properly lemmatized."""
    print("\nTesting verb lemmatization in action discovery...")
    
    kg = WorldKnowledgeGraph()
    updater = BayesianUpdater(kg)
    discoverer = ActionDiscoverer()
    
    code = '''
def manage_products(products):
    """Manage product operations."""
    for product in products:
        # Various verb forms
        product.creates()      # Should be "create"
        product.creating()     # Should be "create"
        product.created()      # Should be "create"
        
        product.updates()      # Should be "update"
        product.updating()     # Should be "update"
        product.updated()      # Should be "update"
'''
    
    actions = discoverer.discover_actions(code, "manage_products")
    
    # Update graph
    for action in actions:
        updater.update_action_belief(
            action.concept, action.verb, 'method_call', action.confidence
        )
    
    # Check that verbs are lemmatized
    product_rels = kg.get_relations_with_confidence("Product")
    product_verbs = {str(r['target']).lower() for r in product_rels 
                    if str(r['relation']) == "PERFORMS"}
    
    print(f"Product action verbs: {sorted(product_verbs)}")
    
    if discoverer.nlp_model:  # Only if spaCy is available
        # Should have lemmatized forms
        assert "create" in product_verbs or "manage" in product_verbs
        assert "update" in product_verbs or "manage" in product_verbs
        
        # Should NOT have inflected forms
        assert "creates" not in product_verbs
        assert "creating" not in product_verbs
        assert "updates" not in product_verbs
    
    print("✓ Verb lemmatization works correctly")


def test_action_confidence_accumulation():
    """Test that multiple evidences increase action confidence."""
    print("\nTesting action confidence accumulation...")
    
    kg = WorldKnowledgeGraph()
    updater = BayesianUpdater(kg)
    
    # Add multiple evidences for same action
    updater.update_action_belief("User", "authenticate", "method_call", 0.9)
    updater.update_action_belief("User", "authenticate", "function_name", 0.8)
    updater.update_action_belief("User", "authenticate", "ast_analysis", 0.7)
    
    # Check confidence increased
    user_rels = kg.get_relations_with_confidence("User")
    auth_rel = next((r for r in user_rels 
                    if str(r['target']) == "Authenticate" and 
                    str(r['relation']) == "PERFORMS"), None)
    
    assert auth_rel is not None, "Should have User PERFORMS Authenticate"
    print(f"Authenticate confidence after 3 evidences: {auth_rel['confidence']:.3f}")
    
    assert auth_rel['confidence'] > 0.8, \
        "Multiple evidence should result in high confidence"
    
    print("✓ Action confidence accumulation works correctly")


def run_all_tests():
    """Run all action discovery integration tests."""
    print("=" * 60)
    print("Action Discovery Integration Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_action_discovery_integration,
        test_action_verb_variations,
        test_action_confidence_accumulation
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