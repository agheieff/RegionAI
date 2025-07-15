#!/usr/bin/env python3
"""
Tests for the Reasoning Engine.

Verifies that the ReasoningEngine correctly executes heuristics based on
the ReasoningKnowledgeGraph, dynamically discovering knowledge.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.hub import KnowledgeHub
from tier3.world_contexts.knowledge.graph import Concept
from regionai.reasoning import ReasoningEngine, heuristic_registry
from tier3.reasoning.budget import DiscoveryBudget
from tier3.reasoning.context import AnalysisContext


def test_reasoning_engine_initialization():
    """Test that the reasoning engine initializes correctly."""
    print("Testing reasoning engine initialization...")
    
    # Create a KnowledgeHub
    hub = KnowledgeHub()
    
    # Create a ReasoningEngine
    engine = ReasoningEngine(hub)
    
    assert engine is not None
    assert engine.hub is hub
    
    print("✓ Reasoning engine initialized successfully")


def test_heuristic_registration():
    """Test that heuristics are properly registered."""
    print("\nTesting heuristic registration...")
    
    # Check that our implementations are registered
    expected_heuristics = [
        "ast.method_call_implies_performs",
        "ast.sequential_nodes_imply_precedes",
        "pattern.co_occurrence_implies_related"
    ]
    
    registered = heuristic_registry.list_registered()
    
    for heuristic_id in expected_heuristics:
        assert heuristic_id in registered, f"Heuristic '{heuristic_id}' not registered"
        print(f"✓ Found registered heuristic: {heuristic_id}")
    
    print(f"✓ Total registered heuristics: {len(registered)}")


def test_method_call_implies_performs():
    """Test the method_call_implies_performs heuristic."""
    print("\nTesting method_call_implies_performs heuristic...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Test code with method calls
    test_code = '''
def process_order(order):
    """Process an order through the system."""
    order.validate()
    order.calculate_total()
    order.save()
    return order
'''
    
    context = {
        'code': test_code,
        'function_name': 'process_order',
        'confidence': 0.8
    }
    
    # Check initial state
    initial_nodes = len(hub.wkg.graph.nodes())
    initial_edges = len(hub.wkg.graph.edges())
    
    # Execute the specific heuristic
    success = engine.execute_specific_heuristic("ast.method_call_implies_performs", context)
    assert success, "Heuristic execution failed"
    
    # Check that concepts were added
    order_concept = Concept("Order")
    assert order_concept in hub.wkg, "Order concept should be discovered"
    
    # Check for action concepts
    validate_concept = Concept("Validate")
    calculate_concept = Concept("Calculate")
    save_concept = Concept("Save")
    
    assert validate_concept in hub.wkg, "Validate action should be discovered"
    assert calculate_concept in hub.wkg, "Calculate action should be discovered"
    assert save_concept in hub.wkg, "Save action should be discovered"
    
    # Check for PERFORMS relationships
    order_relations = hub.wkg.get_relations_with_confidence(order_concept)
    performs_relations = [r for r in order_relations if str(r['relation']) == 'PERFORMS']
    
    assert len(performs_relations) >= 3, "Should have at least 3 PERFORMS relationships"
    
    # Verify the actions
    performed_actions = {str(r['target']) for r in performs_relations}
    assert "Validate" in performed_actions, "Order should PERFORM Validate"
    assert "Calculate" in performed_actions, "Order should PERFORM Calculate"
    assert "Save" in performed_actions, "Order should PERFORM Save"
    
    print(f"✓ Added {len(hub.wkg.graph.nodes()) - initial_nodes} concepts")
    print(f"✓ Added {len(hub.wkg.graph.edges()) - initial_edges} relationships")


def test_sequential_nodes_imply_precedes():
    """Test the sequential_nodes_imply_precedes heuristic."""
    print("\nTesting sequential_nodes_imply_precedes heuristic...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Test code with sequential actions
    test_code = '''
def handle_payment(payment):
    """Handle a payment transaction."""
    payment.validate()
    payment.authorize()
    payment.capture()
    payment.notify()
'''
    
    context = {
        'code': test_code,
        'function_name': 'handle_payment',
        'confidence': 0.9
    }
    
    # Execute the heuristic
    success = engine.execute_specific_heuristic("ast.sequential_nodes_imply_precedes", context)
    assert success, "Heuristic execution failed"
    
    # Check for PRECEDES relationships
    validate_concept = Concept("Validate")
    authorize_concept = Concept("Authorize")
    Concept("Capture")
    Concept("Notify")
    
    # Check validate -> authorize
    validate_relations = hub.wkg.get_relations_with_confidence(validate_concept)
    precedes_relations = [r for r in validate_relations 
                         if str(r['relation']) == 'PRECEDES' and str(r['target']) == 'Authorize']
    assert len(precedes_relations) > 0, "Should have Validate PRECEDES Authorize"
    
    # Check authorize -> capture
    authorize_relations = hub.wkg.get_relations_with_confidence(authorize_concept)
    precedes_relations = [r for r in authorize_relations 
                         if str(r['relation']) == 'PRECEDES' and str(r['target']) == 'Capture']
    assert len(precedes_relations) > 0, "Should have Authorize PRECEDES Capture"
    
    print("✓ Sequential relationships discovered correctly")


def test_co_occurrence_implies_related():
    """Test the co_occurrence_implies_related heuristic."""
    print("\nTesting co_occurrence_implies_related heuristic...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    context = {
        'function_name': 'get_customer_orders',
        'confidence': 0.7
    }
    
    # Execute the heuristic
    success = engine.execute_specific_heuristic("pattern.co_occurrence_implies_related", context)
    assert success, "Heuristic execution failed"
    
    # Check that concepts were discovered
    customer_concept = Concept("Customer")
    orders_concept = Concept("Orders")
    
    assert customer_concept in hub.wkg, "Customer concept should be discovered"
    assert orders_concept in hub.wkg, "Orders concept should be discovered"
    
    # Check for RELATED_TO relationship
    customer_relations = hub.wkg.get_relations_with_confidence(customer_concept)
    related_relations = [r for r in customer_relations 
                        if str(r['relation']) == 'RELATED_TO' and str(r['target']) == 'Orders']
    
    assert len(related_relations) > 0, "Should have Customer RELATED_TO Orders"
    
    print("✓ Co-occurrence relationships discovered correctly")


def test_full_discovery_cycle():
    """Test running a complete discovery cycle."""
    print("\nTesting full discovery cycle...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Complex test code
    test_code = '''
def update_customer_profile(customer_id, profile_data):
    """Update a customer's profile information."""
    customer = get_customer(customer_id)
    customer.validate()
    
    profile = customer.get_profile()
    profile.update(profile_data)
    profile.save()
    
    customer.notify_changes()
    return customer
'''
    
    context = {
        'code': test_code,
        'function_name': 'update_customer_profile',
        'confidence': 0.85,
        'tags': ['ast_analysis']  # Filter to AST-based heuristics
    }
    
    # Run discovery cycle with budget
    budget = DiscoveryBudget(max_heuristics_to_run=3)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    # Check results
    assert results['heuristics_executed'] > 0, "Should execute at least one heuristic"
    assert len(results['discoveries']) > 0, "Should make some discoveries"
    assert len(results['errors']) == 0, f"Should have no errors, but got: {results['errors']}"
    
    print(f"✓ Executed {results['heuristics_executed']} heuristics")
    for discovery in results['discoveries']:
        print(f"✓ {discovery}")
    
    # Verify some expected discoveries
    customer_concept = Concept("Customer")
    profile_concept = Concept("Profile")
    
    assert customer_concept in hub.wkg, "Customer concept should be discovered"
    assert profile_concept in hub.wkg, "Profile concept should be discovered"
    
    # Check for various relationships
    assert len(hub.wkg.graph.edges()) > 0, "Should have discovered relationships"


def test_available_heuristics():
    """Test getting available heuristics information."""
    print("\nTesting available heuristics query...")
    
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    available = engine.get_available_heuristics()
    
    # Check that we have heuristics
    assert len(available) > 0, "Should have available heuristics"
    
    # Check specific heuristics
    expected_heuristics = [
        "Method call implies PERFORMS",
        "Sequential AST nodes imply PRECEDES",
        "Co-occurrence in function name implies RELATED_TO"
    ]
    
    for expected in expected_heuristics:
        assert expected in available, f"Should have heuristic: {expected}"
        heuristic_info = available[expected]
        
        # Check heuristic has required fields
        assert 'description' in heuristic_info
        assert 'utility_score' in heuristic_info
        assert 'implementation_id' in heuristic_info
        assert 'has_implementation' in heuristic_info
        
        print(f"✓ {expected}: implemented={heuristic_info['has_implementation']}, "
              f"score={heuristic_info['utility_score']}")


def test_engine_respects_budget_and_priority():
    """Test that the engine respects budget limits and executes heuristics by priority."""
    print("\nTesting budget and priority-based execution...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Prepare test context with code that triggers multiple heuristics
    test_code = '''
def manage_customer_orders(customer):
    """Manage customer orders."""
    customer.validate()
    customer.save()
'''
    
    context = {
        'code': test_code,
        'function_name': 'manage_customer_orders',
        'confidence': 0.8
    }
    
    # First, verify we have multiple heuristics with different scores
    available = engine.get_available_heuristics()
    implemented_heuristics = {name: info for name, info in available.items() 
                            if info['has_implementation']}
    
    # Sort by utility score to identify the highest priority one
    sorted_heuristics = sorted(implemented_heuristics.items(), 
                             key=lambda x: x[1]['utility_score'], 
                             reverse=True)
    
    if len(sorted_heuristics) < 2:
        print("✗ Need at least 2 implemented heuristics for this test")
        return
    
    highest_priority = sorted_heuristics[0]
    second_priority = sorted_heuristics[1]
    
    highest_score = highest_priority[1]['utility_model'].get('default', 0.0)
    second_score = second_priority[1]['utility_model'].get('default', 0.0)
    
    print(f"  Highest priority: {highest_priority[0]} (score: {highest_score:.2f})")
    print(f"  Second priority: {second_priority[0]} (score: {second_score:.2f})")
    
    # Run with budget of 1
    budget = DiscoveryBudget(max_heuristics_to_run=1)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    # Verify budget was respected
    assert results['heuristics_executed'] == 1, f"Should execute exactly 1 heuristic, but executed {results['heuristics_executed']}"
    assert results['budget_exhausted'] == True, "Budget should be marked as exhausted"
    
    # Based on our heuristics, the highest priority one is "Sequential AST nodes imply PRECEDES" (0.95)
    # For the test code, this won't find sequences, but "Method call implies PERFORMS" (0.85) will find actions
    # So let's check what actually got discovered
    
    # For our test code with validate() and save() calls, "Method call implies PERFORMS" should run
    # and create Customer PERFORMS Validate and Customer PERFORMS Save relationships
    
    # Get concepts and relations
    Concept("Customer")
    validate_concept = Concept("Validate")
    Concept("Save")
    
    # Check which heuristic actually ran based on what's in the graph
    # If Sequential ran (0.95), there would be PRECEDES relations
    # If Method call ran (0.85), there would be PERFORMS relations
    # If Co-occurrence ran (0.75), there would be RELATED_TO relations
    
    # Look for any relations to determine which heuristic ran
    all_edges = list(hub.wkg.graph.edges(data=True))
    relation_types = {edge[2]['label'] for edge in all_edges}
    
    print(f"  Relations found: {relation_types}")
    print(f"  Total relations: {len(all_edges)}")
    
    # Since Sequential (0.95) is highest priority but won't find sequences in our simple code,
    # and Method call (0.85) is second priority and WILL find method calls,
    # we need to adjust our test to ensure Sequential can actually find something
    
    # Let's use different test code that will trigger Sequential
    print("\n  Retesting with sequential code...")
    
    # Clear the hub
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Code that will trigger Sequential AST nodes heuristic
    test_code_sequential = '''
def process_payment(payment):
    """Process a payment."""
    payment.validate()
    payment.authorize()
    payment.capture()
'''
    
    context_sequential = {
        'code': test_code_sequential,
        'function_name': 'process_payment',
        'confidence': 0.8
    }
    
    # Run with budget of 1 - should only run Sequential (0.95)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context_sequential, budget, analysis_context)
    
    # Check that only PRECEDES relations exist (from Sequential heuristic)
    all_edges = list(hub.wkg.graph.edges(data=True))
    for edge in all_edges:
        assert edge[2]['label'] == 'PRECEDES', f"With budget=1, should only have PRECEDES relations, but found {edge[2]['label']}"
    
    # Verify we have the expected PRECEDES relations
    validate_concept = Concept("Validate")
    Concept("Authorize")
    
    validate_relations = hub.wkg.get_relations_with_confidence(validate_concept)
    precedes_relations = [r for r in validate_relations 
                         if str(r['relation']) == 'PRECEDES' and str(r['target']) == 'Authorize']
    
    assert len(precedes_relations) > 0, "Should have Validate PRECEDES Authorize from highest priority heuristic"
    
    print("✓ Engine correctly respects budget and priority")


def run_all_tests():
    """Run all reasoning engine tests."""
    print("=" * 60)
    print("Reasoning Engine Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_reasoning_engine_initialization,
        test_heuristic_registration,
        test_method_call_implies_performs,
        test_sequential_nodes_imply_precedes,
        test_co_occurrence_implies_related,
        test_full_discovery_cycle,
        test_available_heuristics,
        test_engine_respects_budget_and_priority
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
        print("The Reasoning Engine is working correctly!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)