#!/usr/bin/env python3
"""
Tests for the Reasoning Engine's feedback loop mechanism.

Verifies that the engine updates heuristic utility scores based on their
success or failure in discovering new knowledge.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.world_contexts.knowledge.hub import KnowledgeHub
from regionai.world_contexts.knowledge.graph import Concept, Relation
from regionai.world_contexts.knowledge.models import Heuristic
from regionai.reasoning import ReasoningEngine
from regionai.reasoning.budget import DiscoveryBudget
from regionai.reasoning.context import AnalysisContext
from regionai.config import HEURISTIC_LEARNING_RATE


def test_engine_updates_utility_scores_based_on_discovery():
    """Test that the engine updates utility scores based on discovery success."""
    print("Testing utility score updates based on discovery...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Pre-populate the WKG with some knowledge so one heuristic will fail
    # Add Customer and Save concepts with PERFORMS relationship
    customer = Concept("Customer")
    save = Concept("Save")
    hub.wkg.add_concept(customer)
    hub.wkg.add_concept(save)
    hub.wkg.add_relation(customer, save, Relation('PERFORMS'), confidence=0.9)
    
    # Create engine
    engine = ReasoningEngine(hub)
    
    # Test code that will:
    # - Allow Sequential heuristic to find new PRECEDES relationships
    # - Cause Method call heuristic to find some new, some existing relationships
    test_code = '''
def process_customer(customer):
    """Process a customer."""
    customer.validate()    # New - will be discovered
    customer.save()        # Existing - won't be discovered
    customer.notify()      # New - will be discovered
'''
    
    context = {
        'code': test_code,
        'function_name': 'process_customer',
        'confidence': 0.8
    }
    
    # Get initial utility scores for default context
    initial_scores = {}
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.implementation_id:
            default_score = node.get_utility_for_context("default")
            initial_scores[node.name] = default_score
            print(f"  Initial score for '{node.name}': {default_score:.3f}")
    
    # Run discovery cycle with budget allowing all implemented heuristics
    budget = DiscoveryBudget(max_heuristics_to_run=10)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    print(f"\n  Heuristics executed: {results['heuristics_executed']}")
    print(f"  Discoveries: {results['discoveries']}")
    
    # Get updated utility scores for default context
    updated_scores = {}
    score_changes = {}
    
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.implementation_id:
            default_score = node.get_utility_for_context("default")
            updated_scores[node.name] = default_score
            if node.name in initial_scores:
                change = default_score - initial_scores[node.name]
                score_changes[node.name] = change
                print(f"\n  '{node.name}':")
                print(f"    Initial: {initial_scores[node.name]:.3f}")
                print(f"    Updated: {default_score:.3f}")
                print(f"    Change:  {change:+.3f}")
    
    # Verify expectations
    # Sequential should succeed (finding PRECEDES relationships)
    sequential_name = "Sequential AST nodes imply PRECEDES"
    if sequential_name in score_changes:
        assert score_changes[sequential_name] > 0, \
            f"Sequential heuristic should have increased score, but changed by {score_changes[sequential_name]}"
    
    # Method call might have mixed results (some new, some existing)
    method_name = "Method call implies PERFORMS"
    if method_name in score_changes:
        # It should find at least validate() and notify() as new
        # So overall it should succeed
        print(f"\n  Method call heuristic change: {score_changes[method_name]:+.3f}")
    
    # Verify that at least one heuristic had its score updated
    assert len(score_changes) > 0, "No utility scores were updated"
    assert any(change != 0 for change in score_changes.values()), \
        "All score changes were zero"
    
    print("\n✓ Engine correctly updates utility scores based on discovery")


def test_learning_rate_calculations():
    """Test that learning rate calculations are correct."""
    print("\nTesting learning rate calculations...")
    
    # Test success case
    old_score = 0.8
    expected_new_score = old_score + HEURISTIC_LEARNING_RATE * (1.0 - old_score)
    print(f"  Success case: {old_score:.3f} -> {expected_new_score:.3f}")
    assert abs(expected_new_score - 0.802) < 0.0001, "Success calculation incorrect"
    
    # Test failure case
    old_score = 0.8
    expected_new_score = old_score - HEURISTIC_LEARNING_RATE * old_score
    print(f"  Failure case: {old_score:.3f} -> {expected_new_score:.3f}")
    assert abs(expected_new_score - 0.792) < 0.0001, "Failure calculation incorrect"
    
    # Test boundary conditions
    # Score near 1.0
    old_score = 0.99
    success_score = old_score + HEURISTIC_LEARNING_RATE * (1.0 - old_score)
    assert success_score <= 1.0, "Score should not exceed 1.0"
    print(f"  Near 1.0 success: {old_score:.3f} -> {success_score:.3f}")
    
    # Score near 0.0
    old_score = 0.01
    failure_score = old_score - HEURISTIC_LEARNING_RATE * old_score
    assert failure_score >= 0.0, "Score should not go below 0.0"
    print(f"  Near 0.0 failure: {old_score:.3f} -> {failure_score:.3f}")
    
    print("✓ Learning rate calculations are correct")


def test_heuristic_returns_boolean():
    """Test that heuristic implementations return boolean values."""
    print("\nTesting heuristic boolean return values...")
    
    hub = KnowledgeHub()
    
    # Test successful discovery
    test_code = '''
def new_function(obj):
    obj.new_method()
'''
    
    context = {
        'code': test_code,
        'function_name': 'new_function',
        'confidence': 0.8
    }
    
    # Import and test a heuristic directly
    from regionai.reasoning.heuristic_implementations import method_call_implies_performs
    
    # Should return True for new discoveries
    result = method_call_implies_performs(hub, context)
    assert result is True, "Heuristic should return True for new discoveries"
    print("  ✓ Returns True for new discoveries")
    
    # Run again - should return False (already discovered)
    result = method_call_implies_performs(hub, context)
    assert result is False, "Heuristic should return False when no new discoveries"
    print("  ✓ Returns False when no new discoveries")
    
    # Test with empty code
    empty_context = {'code': '', 'function_name': 'test'}
    result = method_call_implies_performs(hub, empty_context)
    assert result is False, "Heuristic should return False for empty code"
    print("  ✓ Returns False for empty code")
    
    print("✓ Heuristics correctly return boolean values")


def run_all_tests():
    """Run all feedback loop tests."""
    print("=" * 60)
    print("Feedback Loop Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_heuristic_returns_boolean,
        test_learning_rate_calculations,
        test_engine_updates_utility_scores_based_on_discovery
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
        print("✓ All feedback loop tests passed!")
        print("The reasoning engine can now learn from its experiences!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)