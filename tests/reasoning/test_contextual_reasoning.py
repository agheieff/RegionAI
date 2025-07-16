#!/usr/bin/env python3
"""
Tests for context-aware reasoning in the RegionAI reasoning engine.

Verifies that the engine selects heuristics based on context-specific utility
scores and updates only the relevant context scores based on success/failure.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.world_contexts.knowledge.hub import KnowledgeHub
from regionai.world_contexts.knowledge.graph import Concept
from regionai.world_contexts.knowledge.models import Heuristic, ReasoningType
from regionai.reasoning import ReasoningEngine
from regionai.reasoning.budget import DiscoveryBudget
from regionai.reasoning.context import AnalysisContext
from regionai.config import HEURISTIC_LEARNING_RATE


def test_engine_selects_and_learns_based_on_context():
    """Test that the engine selects heuristics based on context and updates context-specific scores."""
    print("Testing context-aware heuristic selection and learning...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Manually create two heuristics with different context scores
    # Note: We'll add these directly to the RKG for testing
    heuristic_a = Heuristic(
        name="Database Pattern Detector",
        description="Detects database-related patterns",
        reasoning_type=ReasoningType.HEURISTIC,
        utility_model={
            "default": 0.5,
            "database-interaction": 0.99  # Much better for DB contexts (higher than any built-in)
        },
        implementation_id="test.db_pattern_detector"
    )
    
    heuristic_b = Heuristic(
        name="General Pattern Detector",
        description="Detects general patterns",
        reasoning_type=ReasoningType.HEURISTIC,
        utility_model={
            "default": 0.8  # Good for general contexts
        },
        implementation_id="test.general_pattern_detector"
    )
    
    # Add heuristics to the reasoning graph
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    
    # Register mock implementations
    from regionai.reasoning import heuristic_registry
    
    # Heuristic A will always succeed (for testing)
    @heuristic_registry.register("test.db_pattern_detector")
    def db_pattern_detector(hub, context):
        # Always add a new concept to simulate success
        hub.wkg.add_concept(Concept("TestDbConcept"))
        return True
    
    # Heuristic B will always fail (for testing)
    @heuristic_registry.register("test.general_pattern_detector")
    def general_pattern_detector(hub, context):
        # Don't add anything, simulate failure
        return False
    
    # Create engine
    engine = ReasoningEngine(hub)
    
    # Test context
    test_code = 'def test(): pass'
    context = {
        'code': test_code,
        'function_name': 'test',
        'confidence': 0.8
    }
    
    # Run 1: Database context with budget of 1
    print("\n--- Run 1: Database context ---")
    db_context = AnalysisContext("database-interaction")
    budget_1 = DiscoveryBudget(max_heuristics_to_run=1)
    
    results_1 = engine.run_prioritized_discovery_cycle(context, budget_1, db_context)
    
    # Debug: Print what actually ran
    print(f"Results: {results_1}")
    print(f"Heuristics executed: {results_1['heuristics_executed']}")
    print(f"Discoveries: {results_1['discoveries']}")
    print(f"Errors: {results_1.get('errors', [])}")
    
    # Check available heuristics
    available = engine.get_available_heuristics()
    print(f"\nAvailable heuristics:")
    for name, info in available.items():
        if info['has_implementation']:
            print(f"  {name}: utility_model={info['utility_model']}")
    
    # Verify Heuristic A was chosen (0.9 > 0.8 in DB context)
    assert results_1['heuristics_executed'] == 1, "Should execute exactly 1 heuristic"
    
    # Check which heuristic ran by looking at the graph
    if Concept("TestDbConcept") in hub.wkg:
        print("✓ Heuristic A (Database Pattern Detector) was chosen in DB context")
    else:
        raise AssertionError("Expected Heuristic A to run in database context")
    
    # Clear the test concept
    hub.wkg.graph.remove_node(Concept("TestDbConcept"))
    
    # Run 2: General context with budget of 1
    print("\n--- Run 2: General context ---")
    general_context = AnalysisContext("general")
    budget_2 = DiscoveryBudget(max_heuristics_to_run=1)
    
    # For general context, Heuristic A has score 0.5, B has 0.8
    # So B should be chosen
    results_2 = engine.run_prioritized_discovery_cycle(context, budget_2, general_context)
    
    assert results_2['heuristics_executed'] == 1, "Should execute exactly 1 heuristic"
    
    # B doesn't add concepts, so we check that A didn't run
    assert Concept("TestDbConcept") not in hub.wkg, "Heuristic A should not have run"
    print("✓ Heuristic B (General Pattern Detector) was chosen in general context")
    
    # Run 3: Learning test - Run in DB context where A will succeed
    print("\n--- Run 3: Learning in database context ---")
    
    # Get initial DB score for Heuristic A
    initial_db_score = None
    initial_default_score = None
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.name == "Database Pattern Detector":
            initial_db_score = node.get_utility_for_context("database-interaction")
            initial_default_score = node.get_utility_for_context("default")
            break
    
    assert initial_db_score is not None, "Should find Heuristic A"
    print(f"Initial DB score for Heuristic A: {initial_db_score:.3f}")
    print(f"Initial default score for Heuristic A: {initial_default_score:.3f}")
    
    # Run in DB context again
    engine.run_prioritized_discovery_cycle(context, budget_1, db_context)
    
    # Get updated scores
    updated_db_score = None
    updated_default_score = None
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.name == "Database Pattern Detector":
            updated_db_score = node.get_utility_for_context("database-interaction")
            updated_default_score = node.get_utility_for_context("default")
            break
    
    print(f"Updated DB score for Heuristic A: {updated_db_score:.3f}")
    print(f"Updated default score for Heuristic A: {updated_default_score:.3f}")
    
    # Verify only DB score changed
    assert updated_db_score > initial_db_score, \
        f"DB score should increase after success: {initial_db_score:.3f} -> {updated_db_score:.3f}"
    assert updated_default_score == initial_default_score, \
        f"Default score should not change: {initial_default_score:.3f} -> {updated_default_score:.3f}"
    
    # Calculate expected score
    expected_db_score = initial_db_score + HEURISTIC_LEARNING_RATE * (1.0 - initial_db_score)
    assert abs(updated_db_score - expected_db_score) < 0.0001, \
        f"DB score update incorrect: expected {expected_db_score:.3f}, got {updated_db_score:.3f}"
    
    print("✓ Context-specific learning works correctly")
    print("✓ Only the relevant context score was updated")


def test_context_tag_normalization():
    """Test that context tags are normalized to lowercase."""
    print("\nTesting context tag normalization...")
    
    # Test with various case variations
    ctx1 = AnalysisContext("Database-Interaction")
    ctx2 = AnalysisContext("DATABASE-INTERACTION")
    ctx3 = AnalysisContext("database-interaction")
    
    assert ctx1.current_context_tag == "database-interaction"
    assert ctx2.current_context_tag == "database-interaction"
    assert ctx3.current_context_tag == "database-interaction"
    
    print("✓ Context tags are normalized correctly")


def test_default_context_creation():
    """Test default context creation."""
    print("\nTesting default context creation...")
    
    ctx = AnalysisContext.default()
    assert ctx.current_context_tag == "default"
    
    domain_ctx = AnalysisContext.for_domain("API-Design")
    assert domain_ctx.current_context_tag == "api-design"
    
    print("✓ Default and domain contexts created correctly")


def test_automatic_context_detection():
    """Test that the engine automatically detects context and selects appropriate heuristics."""
    print("\nTesting automatic context detection...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Add our test heuristics
    heuristic_a = Heuristic(
        name="Database Pattern Detector",
        description="Detects database-related patterns",
        reasoning_type=ReasoningType.HEURISTIC,
        utility_model={
            "default": 0.5,
            "database-interaction": 0.99  # Much better for DB contexts
        },
        implementation_id="test.db_pattern_detector"
    )
    
    heuristic_b = Heuristic(
        name="General Pattern Detector",
        description="Detects general patterns",
        reasoning_type=ReasoningType.HEURISTIC,
        utility_model={
            "default": 0.85  # Good for general contexts, but lower than Sequential (0.95)
        },
        implementation_id="test.general_pattern_detector"
    )
    
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    
    # Register mock implementations
    from regionai.reasoning import heuristic_registry
    
    @heuristic_registry.register("test.db_pattern_detector")
    def db_pattern_detector(hub, context):
        hub.wkg.add_concept(Concept("TestDbConcept"))
        return True
    
    @heuristic_registry.register("test.general_pattern_detector")
    def general_pattern_detector(hub, context):
        hub.wkg.add_concept(Concept("TestGeneralConcept"))
        return True
    
    # Create engine
    engine = ReasoningEngine(hub)
    
    # Run 1: Database code - should detect database-interaction context
    print("\n--- Run 1: Database code ---")
    db_code = '''
def get_user_data(user_id):
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, user_id)
'''
    
    budget = DiscoveryBudget(max_heuristics_to_run=1)
    trace_1 = engine.run_autonomous_discovery_cycle(db_code, budget)
    
    # Verify we got a trace and database heuristic was chosen
    assert trace_1 is not None, "Should return a trace when discoveries are made"
    assert trace_1.context_tag == "database-interaction", "Should detect database context"
    assert len(trace_1.successful_heuristic_ids) == 1, "Should record one successful heuristic"
    assert trace_1.successful_heuristic_ids[0] == "test.db_pattern_detector", "Should record correct heuristic ID"
    assert Concept("TestDbConcept") in hub.wkg, "Database heuristic should have run"
    print("✓ Automatically detected database context and chose appropriate heuristic")
    print(f"✓ Trace recorded: {trace_1}")
    
    # Clear test concepts
    hub.wkg.graph.remove_node(Concept("TestDbConcept"))
    
    # Run 2: Generic code - should detect default context
    print("\n--- Run 2: Generic code ---")
    generic_code = '''
def calculate_sum(a, b):
    return a + b
'''
    
    trace_2 = engine.run_autonomous_discovery_cycle(generic_code, budget)
    
    # With default context, Sequential (0.95) should run, not our test heuristics
    # Since Sequential won't find sequences in simple code, trace might be None
    # Neither of our test concepts should be created
    assert Concept("TestDbConcept") not in hub.wkg, "Database heuristic should not have run"
    assert Concept("TestGeneralConcept") not in hub.wkg, "General heuristic should not have run"
    print("✓ Automatically detected default context")
    if trace_2:
        print(f"✓ Trace recorded: {trace_2}")
    else:
        print("✓ No discoveries made (as expected for simple code)")
    
    # Run 3: Learning test with database failure
    print("\n--- Run 3: Learning with automatic detection ---")
    
    # Re-register DB heuristic to fail this time
    @heuristic_registry.register("test.db_pattern_detector")
    def db_pattern_detector_fail(hub, context):
        # Don't add anything, simulate failure
        return False
    
    # Get initial score
    initial_db_score = None
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.name == "Database Pattern Detector":
            initial_db_score = node.get_utility_for_context("database-interaction")
            initial_default_score = node.get_utility_for_context("default")
            break
    
    # Run with database code again
    engine.run_autonomous_discovery_cycle(db_code, budget)
    
    # Get updated scores
    updated_db_score = None
    updated_default_score = None
    for node in hub.rkg.graph.nodes():
        if isinstance(node, Heuristic) and node.name == "Database Pattern Detector":
            updated_db_score = node.get_utility_for_context("database-interaction")
            updated_default_score = node.get_utility_for_context("default")
            break
    
    # Verify only database-interaction score decreased
    assert updated_db_score < initial_db_score, \
        f"DB score should decrease after failure: {initial_db_score:.3f} -> {updated_db_score:.3f}"
    assert updated_default_score == initial_default_score, \
        f"Default score should not change: {initial_default_score:.3f} -> {updated_default_score:.3f}"
    
    print("✓ Context-specific learning works with automatic detection")


def run_all_tests():
    """Run all contextual reasoning tests."""
    print("=" * 60)
    print("Contextual Reasoning Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_context_tag_normalization,
        test_default_context_creation,
        test_engine_selects_and_learns_based_on_context,
        test_automatic_context_detection
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
        print("✓ All contextual reasoning tests passed!")
        print("The reasoning engine now makes context-aware decisions!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)