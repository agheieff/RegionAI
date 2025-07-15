#!/usr/bin/env python3
"""
Tests for execution of composed heuristics in the reasoning engine.

Verifies that the ReasoningEngine can properly execute ComposedHeuristics
by running their component heuristics in sequence and handling scoring correctly.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.hub import KnowledgeHub
from tier3.world_contexts.knowledge.graph import Concept
from tier3.world_contexts.knowledge.models import Heuristic, ComposedHeuristic, ReasoningType
from regionai.reasoning import ReasoningEngine
from tier3.reasoning.registry import heuristic_registry
from tier3.reasoning.budget import DiscoveryBudget
from tier3.reasoning.context import AnalysisContext
from tier1.config import HEURISTIC_LEARNING_RATE


def test_engine_executes_composed_heuristic_and_learns():
    """Test that the engine executes composed heuristics and updates scores correctly."""
    print("Testing composed heuristic execution and learning...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Create two component heuristics
    heuristic_a = Heuristic(
        name="Component A",
        description="First component",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.component_a",
        utility_model={"default": 0.6, "test-context": 0.7}
    )
    
    heuristic_b = Heuristic(
        name="Component B",
        description="Second component",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.component_b",
        utility_model={"default": 0.7, "test-context": 0.8}
    )
    
    # Create a composed heuristic with high priority for test-context
    composed_ab = ComposedHeuristic(
        name="Composed AB",
        description="Composition of A and B",
        reasoning_type=ReasoningType.HEURISTIC,
        component_heuristic_ids=("test.component_a", "test.component_b"),
        utility_model={"default": 0.75, "test-context": 0.99},  # Higher than any built-in
        implementation_id=""  # ComposedHeuristics have empty implementation_id
    )
    
    # Add all to the reasoning graph
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    hub.rkg.graph.add_node(composed_ab)
    
    # Mock implementations - A fails, B succeeds
    @heuristic_registry.register("test.component_a")
    def component_a_impl(hub, context):
        # Component A fails - no discovery
        return False
    
    @heuristic_registry.register("test.component_b")
    def component_b_impl(hub, context):
        # Component B succeeds - adds a concept
        hub.wkg.add_concept(Concept("DiscoveredByB"))
        return True
    
    # Create engine
    engine = ReasoningEngine(hub)
    
    # Test context
    context = {
        'code': 'test code',
        'function_name': 'test_func',
        'confidence': 0.8
    }
    
    # Get initial scores
    initial_a_score = heuristic_a.get_utility_for_context("test-context")
    initial_b_score = heuristic_b.get_utility_for_context("test-context")
    initial_composed_score = composed_ab.get_utility_for_context("test-context")
    
    print(f"Initial scores:")
    print(f"  Component A: {initial_a_score:.3f}")
    print(f"  Component B: {initial_b_score:.3f}")
    print(f"  Composed AB: {initial_composed_score:.3f}")
    
    # Check what heuristics are available
    available = engine.get_available_heuristics()
    print(f"\nAvailable heuristics:")
    for name, info in available.items():
        print(f"  {name}: utility={info.get('utility_model', {}).get('test-context', info.get('utility_model', {}).get('default', 0))}")
    
    # Run discovery cycle with only the composed heuristic
    budget = DiscoveryBudget(max_heuristics_to_run=1)
    analysis_context = AnalysisContext("test-context")
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    # Verify execution
    assert results['heuristics_executed'] == 1, "Should execute exactly 1 heuristic"
    assert Concept("DiscoveredByB") in hub.wkg, "Component B should have added its concept"
    
    # Get updated scores
    updated_a_score = None
    updated_b_score = None
    updated_composed_score = None
    
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic):
            if node.name == "Component A":
                updated_a_score = node.get_utility_for_context("test-context")
            elif node.name == "Component B":
                updated_b_score = node.get_utility_for_context("test-context")
            elif node.name == "Composed AB":
                updated_composed_score = node.get_utility_for_context("test-context")
    
    print(f"\nUpdated scores:")
    print(f"  Component A: {updated_a_score:.3f} (change: {updated_a_score - initial_a_score:+.3f})")
    print(f"  Component B: {updated_b_score:.3f} (change: {updated_b_score - initial_b_score:+.3f})")
    print(f"  Composed AB: {updated_composed_score:.3f} (change: {updated_composed_score - initial_composed_score:+.3f})")
    
    # Verify score updates
    assert updated_a_score < initial_a_score, \
        f"Component A score should decrease (failed): {initial_a_score:.3f} -> {updated_a_score:.3f}"
    assert updated_b_score > initial_b_score, \
        f"Component B score should increase (succeeded): {initial_b_score:.3f} -> {updated_b_score:.3f}"
    assert updated_composed_score > initial_composed_score, \
        f"Composed score should increase (overall success): {initial_composed_score:.3f} -> {updated_composed_score:.3f}"
    
    # Verify expected score changes
    expected_a_score = initial_a_score - HEURISTIC_LEARNING_RATE * initial_a_score
    expected_b_score = initial_b_score + HEURISTIC_LEARNING_RATE * (1.0 - initial_b_score)
    expected_composed_score = initial_composed_score + HEURISTIC_LEARNING_RATE * (1.0 - initial_composed_score)
    
    assert abs(updated_a_score - expected_a_score) < 0.0001, \
        f"Component A score incorrect: expected {expected_a_score:.3f}, got {updated_a_score:.3f}"
    assert abs(updated_b_score - expected_b_score) < 0.0001, \
        f"Component B score incorrect: expected {expected_b_score:.3f}, got {updated_b_score:.3f}"
    assert abs(updated_composed_score - expected_composed_score) < 0.0001, \
        f"Composed score incorrect: expected {expected_composed_score:.3f}, got {updated_composed_score:.3f}"
    
    print("\n✓ Composed heuristic executed successfully")
    print("✓ Component and parent scores updated correctly")


def test_engine_avoids_redundant_execution():
    """Test that the engine doesn't execute components twice."""
    print("\nTesting redundant execution prevention...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Track execution counts
    execution_counts = {"a": 0, "b": 0}
    
    # Create component heuristics with high scores
    heuristic_a = Heuristic(
        name="High Priority A",
        description="Component A with high score",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.high_a",
        utility_model={"default": 0.85}  # High but lower than composed
    )
    
    heuristic_b = Heuristic(
        name="Component B",
        description="Component B",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.comp_b",
        utility_model={"default": 0.5}
    )
    
    # Create composed heuristic with highest score
    composed_ab = ComposedHeuristic(
        name="High Priority Composed",
        description="Composed with high score",
        reasoning_type=ReasoningType.HEURISTIC,
        component_heuristic_ids=("test.high_a", "test.comp_b"),
        utility_model={"default": 0.99},  # Highest score, will run first
        implementation_id=""
    )
    
    # Add all to graph
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    hub.rkg.graph.add_node(composed_ab)
    
    # Mock implementations that track calls
    @heuristic_registry.register("test.high_a")
    def high_a_impl(hub, context):
        execution_counts["a"] += 1
        hub.wkg.add_concept(Concept(f"ConceptA_{execution_counts['a']}"))
        return True
    
    @heuristic_registry.register("test.comp_b")
    def comp_b_impl(hub, context):
        execution_counts["b"] += 1
        hub.wkg.add_concept(Concept(f"ConceptB_{execution_counts['b']}"))
        return True
    
    # Create engine
    engine = ReasoningEngine(hub)
    
    # Test context
    context = {
        'code': 'test code',
        'function_name': 'test_func',
        'confidence': 0.8
    }
    
    # Run with budget of 2 - should execute composed (which runs A and B) and then skip standalone A
    budget = DiscoveryBudget(max_heuristics_to_run=2)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    print(f"Execution counts: A={execution_counts['a']}, B={execution_counts['b']}")
    print(f"Heuristics executed: {results['heuristics_executed']}")
    
    # Verify execution counts
    assert execution_counts["a"] == 1, f"Component A should execute only once, but executed {execution_counts['a']} times"
    assert execution_counts["b"] == 1, f"Component B should execute only once, but executed {execution_counts['b']} times"
    
    # Verify that 2 heuristics were counted as executed (composed + skipped standalone)
    assert results['heuristics_executed'] == 2, f"Should count 2 heuristics executed, got {results['heuristics_executed']}"
    
    # Verify concepts were created
    assert Concept("ConceptA_1") in hub.wkg, "Component A should have created its concept"
    assert Concept("ConceptB_1") in hub.wkg, "Component B should have created its concept"
    
    print("✓ Successfully prevented redundant execution")
    print("✓ Components executed exactly once despite being in multiple heuristics")


def test_composed_partial_execution():
    """Test composed heuristic when some components are already executed."""
    print("\nTesting partial execution of composed heuristic...")
    
    # Create hub and clear built-in heuristics for controlled testing
    hub = KnowledgeHub()
    # Remove all built-in heuristics for this test
    nodes_to_remove = [n for n in hub.rkg.graph.nodes() if isinstance(n, Heuristic)]
    for node in nodes_to_remove:
        hub.rkg.graph.remove_node(node)
    
    # Create three components
    heuristic_a = Heuristic(
        name="Component A",
        description="First component",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.part_a",
        utility_model={"default": 0.9}  # High priority
    )
    
    heuristic_b = Heuristic(
        name="Component B",
        description="Second component",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.part_b",
        utility_model={"default": 0.4}
    )
    
    heuristic_c = Heuristic(
        name="Component C",
        description="Third component",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="test.part_c",
        utility_model={"default": 0.3}
    )
    
    # Composed heuristic uses all three
    composed_abc = ComposedHeuristic(
        name="Composed ABC",
        description="Uses A, B, and C",
        reasoning_type=ReasoningType.HEURISTIC,
        component_heuristic_ids=("test.part_a", "test.part_b", "test.part_c"),
        utility_model={"default": 0.89},  # Just below A (0.9) but will run second
        implementation_id=""
    )
    
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    hub.rkg.graph.add_node(heuristic_c)
    hub.rkg.graph.add_node(composed_abc)
    
    # Track executions
    executed = []
    
    @heuristic_registry.register("test.part_a")
    def part_a_impl(hub, context):
        executed.append("A")
        return True
    
    @heuristic_registry.register("test.part_b")
    def part_b_impl(hub, context):
        executed.append("B")
        return False
    
    @heuristic_registry.register("test.part_c")
    def part_c_impl(hub, context):
        executed.append("C")
        return True
    
    engine = ReasoningEngine(hub)
    context = {'code': 'test', 'function_name': 'test', 'confidence': 0.8}
    
    # Check what heuristics are available and their order
    available = engine.get_available_heuristics()
    print("\nAvailable heuristics (by priority):")
    sorted_heuristics = sorted(
        [(name, info) for name, info in available.items() if info['has_implementation']],
        key=lambda x: x[1]['utility_model'].get('default', 0),
        reverse=True
    )
    for name, info in sorted_heuristics[:5]:
        print(f"  {name}: {info['utility_model'].get('default', 0)}")
    
    # Run with budget of 2 - should run A first, then composed (which skips A, runs B and C)
    budget = DiscoveryBudget(max_heuristics_to_run=2)
    analysis_context = AnalysisContext.default()
    results = engine.run_prioritized_discovery_cycle(context, budget, analysis_context)
    
    print(f"\nExecution order: {executed}")
    print(f"Heuristics executed: {results['heuristics_executed']}")
    
    # Verify execution order and no duplicates
    assert executed == ["A", "B", "C"], f"Expected execution order [A, B, C], got {executed}"
    assert results['heuristics_executed'] == 2, "Should execute 2 heuristics (standalone A + composed)"
    
    print("✓ Partial execution handled correctly")
    print("✓ Already-executed components skipped in composition")


def run_all_tests():
    """Run all composed execution tests."""
    print("=" * 60)
    print("Composed Heuristic Execution Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_engine_executes_composed_heuristic_and_learns,
        test_engine_avoids_redundant_execution,
        test_composed_partial_execution
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
        print("✓ All composed execution tests passed!")
        print("The reasoning engine can now execute synthesized heuristics!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)