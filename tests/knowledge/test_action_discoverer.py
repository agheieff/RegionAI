#!/usr/bin/env python3
"""
Tests for the ActionDiscoverer class.

Verifies that the system can identify actions (verbs) performed in code
and link them to the concepts they operate on.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.world_contexts.knowledge.action_discoverer import ActionDiscoverer
from regionai.world_contexts.knowledge.graph import WorldKnowledgeGraph, Concept
from regionai.world_contexts.knowledge.bayesian_updater import BayesianUpdater


def test_basic_action_discovery():
    """Test basic action discovery from simple method calls."""
    print("Testing basic action discovery...")
    
    discoverer = ActionDiscoverer()
    
    # Simple function with clear actions
    code = '''
def save_user(user):
    """Save a user to the database."""
    user.validate()
    user.save_to_db()
    log.write("User saved")
'''
    
    actions = discoverer.discover_actions(code, "save_user")
    
    print(f"Discovered {len(actions)} actions:")
    for action in actions:
        print(f"  {action}")
    
    # Should find save action from function name
    save_actions = [a for a in actions if a.verb == "save"]
    assert len(save_actions) >= 1, "Should find 'save' action from function name"
    
    # Should find validate action from method call
    validate_actions = [a for a in actions if a.verb == "validate" and a.concept == "user"]
    assert len(validate_actions) == 1, "Should find user.validate() action"
    
    # Should find write action from log
    write_actions = [a for a in actions if a.verb == "write" and a.concept == "log"]
    assert len(write_actions) == 1, "Should find log.write() action"
    
    print("✓ Basic action discovery works correctly")


def test_action_discovery_from_function_names():
    """Test action discovery from function names alone."""
    print("\nTesting action discovery from function names...")
    
    discoverer = ActionDiscoverer()
    
    # Function with actions in the name
    code = '''
def update_customer_address(customer_id, new_address):
    pass
'''
    
    actions = discoverer.discover_actions(code, "update_customer_address")
    
    print(f"Actions from function name: {[str(a) for a in actions]}")
    
    # Should find update action on customer and address
    update_actions = [a for a in actions if a.verb == "update"]
    assert len(update_actions) >= 1, "Should find 'update' action"
    
    # Check concepts
    concepts = {a.concept for a in actions}
    assert "customer" in concepts or "address" in concepts, \
        "Should identify customer or address as concepts"
    
    print("✓ Function name action discovery works correctly")


def test_complex_action_discovery():
    """Test action discovery from complex code patterns."""
    print("\nTesting complex action discovery...")
    
    discoverer = ActionDiscoverer()
    
    code = '''
def process_order(order):
    """Process an order through the system."""
    # Validate the order first
    if not order.validate():
        raise ValueError("Invalid order")
    
    # Calculate totals
    subtotal = order.calculate_subtotal()
    tax = calculate_tax(subtotal)
    order.set_total(subtotal + tax)
    
    # Update inventory
    for item in order.items:
        item.product.decrease_stock(item.quantity)
    
    # Send confirmation
    email_service.send(order.customer.email, "Order confirmed")
    
    # Save to database
    db.save(order)
    return order
'''
    
    actions = discoverer.discover_actions(code, "process_order")
    
    print(f"Discovered {len(actions)} actions from complex code:")
    unique_verbs = {a.verb for a in actions}
    print(f"  Unique verbs: {sorted(unique_verbs)}")
    
    # Should find various actions
    assert "process" in unique_verbs, "Should find 'process' from function name"
    assert "validate" in unique_verbs, "Should find 'validate' action"
    assert "calculate" in unique_verbs, "Should find 'calculate' action"
    assert "send" in unique_verbs, "Should find 'send' action"
    assert "save" in unique_verbs, "Should find 'save' action"
    
    # Check specific action-concept pairs
    validate_order = any(a.verb == "validate" and a.concept == "order" for a in actions)
    assert validate_order, "Should find order.validate()"
    
    send_email = any(a.verb == "send" and "email" in a.concept for a in actions)
    assert send_email, "Should find email_service.send()"
    
    print("✓ Complex action discovery works correctly")


def test_action_confidence_scoring():
    """Test that action confidence scores are reasonable."""
    print("\nTesting action confidence scoring...")
    
    discoverer = ActionDiscoverer()
    
    code = '''
def create_invoice(order):
    """Create an invoice for an order."""
    invoice = Invoice()
    invoice.generate_from_order(order)
    maybe_send_email()  # Less clear action
    return invoice
'''
    
    actions = discoverer.discover_actions(code, "create_invoice")
    
    print("Action confidence scores:")
    for action in actions:
        print(f"  {action} - confidence: {action.confidence}")
    
    # Method calls should have high confidence
    generate_action = next((a for a in actions if a.verb == "generate"), None)
    if generate_action:
        assert generate_action.confidence >= 0.8, \
            "Direct method calls should have high confidence"
    
    # Function name actions should have good confidence
    create_action = next((a for a in actions if a.verb == "create"), None)
    if create_action:
        assert create_action.confidence >= 0.7, \
            "Function name actions should have good confidence"
    
    print("✓ Action confidence scoring works correctly")


def test_bayesian_action_updates():
    """Test integration with Bayesian updater for action beliefs."""
    print("\nTesting Bayesian action belief updates...")
    
    # Create knowledge graph
    kg = WorldKnowledgeGraph()
    updater = BayesianUpdater(kg)
    
    # Update action beliefs
    updater.update_action_belief("Customer", "save", "method_call", 0.9)
    updater.update_action_belief("Customer", "save", "function_name", 0.8)
    updater.update_action_belief("Customer", "delete", "method_call", 0.9)
    
    # Check that concepts exist
    assert Concept("Customer") in kg, "Customer concept should exist"
    assert Concept("Save") in kg, "Save action should exist as concept"
    assert Concept("Delete") in kg, "Delete action should exist as concept"
    
    # Check relationships
    customer_rels = kg.get_relations_with_confidence("Customer")
    performs_rels = [r for r in customer_rels if str(r['relation']) == "PERFORMS"]
    
    print(f"Found {len(performs_rels)} PERFORMS relationships:")
    for rel in performs_rels:
        print(f"  Customer -> {rel['target']} (confidence: {rel['confidence']:.3f})")
    
    assert len(performs_rels) >= 2, "Should have at least 2 PERFORMS relationships"
    
    # Check confidence increased with multiple evidence
    save_rel = next((r for r in performs_rels if str(r['target']) == "Save"), None)
    assert save_rel is not None, "Should have Customer PERFORMS Save relationship"
    assert save_rel['confidence'] > 0.7, \
        "Multiple evidence should increase confidence above initial 0.5"
    
    print("✓ Bayesian action updates work correctly")


def test_verb_lemmatization():
    """Test that verbs are properly lemmatized."""
    print("\nTesting verb lemmatization...")
    
    discoverer = ActionDiscoverer()
    
    code = '''
def update_records(records):
    """Updates multiple records."""
    for record in records:
        record.updating()     # Should become "update"
        record.validated()    # Should become "validate"
        record.saves()        # Should become "save"
'''
    
    actions = discoverer.discover_actions(code, "update_records")
    
    verbs = {a.verb for a in actions}
    print(f"Lemmatized verbs: {sorted(verbs)}")
    
    # All forms should be lemmatized to base form
    if discoverer.nlp_model:  # Only if spaCy is available
        assert "update" in verbs, "Should lemmatize 'updating' to 'update'"
        assert "validate" in verbs, "Should lemmatize 'validated' to 'validate'"
        assert "save" in verbs, "Should lemmatize 'saves' to 'save'"
        
        # Should not have inflected forms
        assert "updating" not in verbs
        assert "validated" not in verbs
        assert "saves" not in verbs
    
    print("✓ Verb lemmatization works correctly")


def run_all_tests():
    """Run all action discovery tests."""
    print("=" * 60)
    print("Action Discovery Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_basic_action_discovery,
        test_action_discovery_from_function_names,
        test_complex_action_discovery,
        test_action_confidence_scoring,
        test_bayesian_action_updates,
        test_verb_lemmatization
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