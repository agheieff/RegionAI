#!/usr/bin/env python3
"""
Tests for the heuristic synthesizer.

Verifies that the HeuristicSynthesizer can analyze reasoning traces
and create new composite heuristics from frequently occurring patterns.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.world_contexts.knowledge.hub import KnowledgeHub
from regionai.world_contexts.knowledge.models import ComposedHeuristic, Heuristic, ReasoningType
from regionai.reasoning.trace import ReasoningTrace
from regionai.domains.code.synthesis import HeuristicSynthesizer


def test_synthesizer_creates_composed_heuristic_from_traces():
    """Test that the synthesizer creates a composed heuristic from recurring patterns."""
    print("Testing heuristic synthesis from traces...")
    
    # Create a fresh hub
    hub = KnowledgeHub()
    
    # Add some base heuristics to the RKG for reference
    heuristic_a = Heuristic(
        name="Extract Data",
        description="Extracts data from code",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="extract.data",
        utility_model={"default": 0.7, "database-interaction": 0.8}
    )
    
    heuristic_b = Heuristic(
        name="Validate Structure",
        description="Validates data structure",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="validate.structure",
        utility_model={"default": 0.6, "database-interaction": 0.9}
    )
    
    hub.rkg.graph.add_node(heuristic_a)
    hub.rkg.graph.add_node(heuristic_b)
    
    # Create traces with a recurring pattern
    traces = []
    
    # Pattern appears 4 times in database context
    for i in range(4):
        trace = ReasoningTrace(
            context_tag="database-interaction",
            successful_heuristic_ids=["extract.data", "validate.structure"],
            total_discoveries=2
        )
        traces.append(trace)
    
    # Different pattern appears once (below threshold)
    trace = ReasoningTrace(
        context_tag="database-interaction",
        successful_heuristic_ids=["validate.structure", "extract.data"],
        total_discoveries=1
    )
    traces.append(trace)
    
    # Pattern appears in different context
    trace = ReasoningTrace(
        context_tag="api-design",
        successful_heuristic_ids=["extract.data", "validate.structure"],
        total_discoveries=2
    )
    traces.append(trace)
    
    # Initialize synthesizer
    synthesizer = HeuristicSynthesizer(hub)
    
    # Analyze traces
    patterns = synthesizer.analyze_traces(traces)
    
    # Verify pattern detection
    assert "database-interaction" in patterns, "Should find patterns in database context"
    assert len(patterns["database-interaction"]) >= 1, "Should find at least one pattern"
    assert ("extract.data", "validate.structure") in patterns["database-interaction"], \
        "Should find the frequent pattern"
    
    print("✓ Pattern analysis successful")
    
    # Synthesize heuristic from the pattern
    new_heuristic = synthesizer.synthesize_new_heuristic(
        "database-interaction",
        ["extract.data", "validate.structure"]
    )
    
    # Verify the composed heuristic was created
    assert new_heuristic is not None, "Should create a new heuristic"
    assert isinstance(new_heuristic, ComposedHeuristic), "Should be a ComposedHeuristic"
    assert new_heuristic.component_heuristic_ids == ("extract.data", "validate.structure"), \
        "Should have correct component IDs"
    
    # Verify it was added to the RKG
    assert new_heuristic in hub.rkg.graph, "Should be added to reasoning graph"
    
    # Verify utility model
    assert "database-interaction" in new_heuristic.utility_model, \
        "Should have utility for the context"
    db_utility = new_heuristic.get_utility_for_context("database-interaction")
    assert db_utility > 0.9, f"Should have high utility for database context, got {db_utility}"
    
    print(f"✓ Created composed heuristic: {new_heuristic.name}")
    print(f"  Components: {new_heuristic.component_heuristic_ids}")
    print(f"  Utility: {new_heuristic.utility_model}")
    
    # Try to create the same heuristic again - should return None
    duplicate = synthesizer.synthesize_new_heuristic(
        "database-interaction",
        ["extract.data", "validate.structure"]
    )
    assert duplicate is None, "Should not create duplicate composed heuristic"
    
    print("✓ Correctly avoided creating duplicate")


def test_synthesizer_respects_pattern_threshold():
    """Test that the synthesizer only creates heuristics for patterns above threshold."""
    print("\nTesting pattern threshold...")
    
    hub = KnowledgeHub()
    synthesizer = HeuristicSynthesizer(hub)
    
    # Create traces with pattern appearing only twice (below default threshold of 3)
    traces = [
        ReasoningTrace(
            context_tag="testing",
            successful_heuristic_ids=["test.a", "test.b"],
            total_discoveries=1
        ),
        ReasoningTrace(
            context_tag="testing",
            successful_heuristic_ids=["test.a", "test.b"],
            total_discoveries=1
        )
    ]
    
    patterns = synthesizer.analyze_traces(traces)
    
    # Should not find any patterns since count is below threshold
    assert "testing" not in patterns or len(patterns.get("testing", [])) == 0, \
        "Should not find patterns below threshold"
    
    print("✓ Correctly ignored patterns below threshold")


def test_synthesizer_handles_longer_chains():
    """Test that the synthesizer can handle chains with more than 2 heuristics."""
    print("\nTesting longer reasoning chains...")
    
    hub = KnowledgeHub()
    synthesizer = HeuristicSynthesizer(hub)
    
    # Create traces with 3-heuristic chains
    traces = []
    for i in range(4):
        trace = ReasoningTrace(
            context_tag="workflow-analysis",
            successful_heuristic_ids=["analyze.flow", "extract.steps", "validate.order"],
            total_discoveries=3
        )
        traces.append(trace)
    
    patterns = synthesizer.analyze_traces(traces)
    
    # Should find multiple pairs from the chain
    assert "workflow-analysis" in patterns, "Should find patterns"
    workflow_patterns = patterns["workflow-analysis"]
    
    # Should extract pairs: (analyze.flow, extract.steps) and (extract.steps, validate.order)
    assert ("analyze.flow", "extract.steps") in workflow_patterns, \
        "Should find first pair"
    assert ("extract.steps", "validate.order") in workflow_patterns, \
        "Should find second pair"
    
    print("✓ Successfully extracted pairs from longer chains")


def test_synthesize_from_traces_integration():
    """Test the full synthesis workflow."""
    print("\nTesting full synthesis workflow...")
    
    hub = KnowledgeHub()
    
    # Add base heuristics
    for i, (name, impl_id) in enumerate([
        ("Parse Code", "parse.code"),
        ("Find Patterns", "find.patterns"),
        ("Extract Info", "extract.info")
    ]):
        heuristic = Heuristic(
            name=name,
            description=f"Test heuristic {i}",
            reasoning_type=ReasoningType.HEURISTIC,
            implementation_id=impl_id,
            utility_model={"default": 0.5 + i * 0.1}
        )
        hub.rkg.graph.add_node(heuristic)
    
    synthesizer = HeuristicSynthesizer(hub)
    
    # Create diverse traces
    traces = []
    
    # Pattern 1: parse -> find (appears 3 times)
    for i in range(3):
        traces.append(ReasoningTrace(
            context_tag="code-analysis",
            successful_heuristic_ids=["parse.code", "find.patterns"],
            total_discoveries=2
        ))
    
    # Pattern 2: find -> extract (appears 3 times)
    for i in range(3):
        traces.append(ReasoningTrace(
            context_tag="code-analysis",
            successful_heuristic_ids=["find.patterns", "extract.info"],
            total_discoveries=2
        ))
    
    # Run full synthesis
    synthesized = synthesizer.synthesize_from_traces(traces)
    
    # Should create 2 new heuristics
    assert len(synthesized) == 2, f"Should synthesize 2 heuristics, got {len(synthesized)}"
    
    # Verify they're all ComposedHeuristics
    for h in synthesized:
        assert isinstance(h, ComposedHeuristic), "Should be ComposedHeuristic"
        assert len(h.component_heuristic_ids) == 2, "Should have 2 components"
        assert h in hub.rkg.graph, "Should be in reasoning graph"
    
    print(f"✓ Successfully synthesized {len(synthesized)} new heuristics")
    for h in synthesized:
        print(f"  - {h.name}: {h.component_heuristic_ids}")


def test_trace_validation():
    """Test that ReasoningTrace validates its inputs."""
    print("\nTesting trace validation...")
    
    # Test empty context_tag
    try:
        ReasoningTrace(context_tag="")
        assert False, "Should raise ValueError for empty context_tag"
    except ValueError as e:
        assert "context_tag cannot be empty" in str(e)
        print("✓ Correctly rejected empty context_tag")
    
    # Test is_meaningful
    trace1 = ReasoningTrace(
        context_tag="test",
        successful_heuristic_ids=["a"]
    )
    assert not trace1.is_meaningful(), "Single heuristic should not be meaningful"
    
    trace2 = ReasoningTrace(
        context_tag="test",
        successful_heuristic_ids=["a", "b"]
    )
    assert trace2.is_meaningful(), "Two heuristics should be meaningful"
    
    print("✓ Trace validation works correctly")


def test_composed_heuristic_validation():
    """Test that ComposedHeuristic validates its inputs."""
    print("\nTesting ComposedHeuristic validation...")
    
    # Test with implementation_id (should fail)
    try:
        ComposedHeuristic(
            name="Test",
            description="Test",
            reasoning_type=ReasoningType.HEURISTIC,
            implementation_id="should.not.have",
            component_heuristic_ids=("a", "b")
        )
        assert False, "Should raise ValueError for non-empty implementation_id"
    except ValueError as e:
        assert "should not have an implementation_id" in str(e)
        print("✓ Correctly rejected implementation_id")
    
    # Test with too few components
    try:
        ComposedHeuristic(
            name="Test",
            description="Test",
            reasoning_type=ReasoningType.HEURISTIC,
            implementation_id="",
            component_heuristic_ids=("a",)
        )
        assert False, "Should raise ValueError for single component"
    except ValueError as e:
        assert "at least 2 component heuristics" in str(e)
        print("✓ Correctly rejected single component")
    
    # Test valid creation
    composed = ComposedHeuristic(
        name="Test Composite",
        description="Valid composite",
        reasoning_type=ReasoningType.HEURISTIC,
        implementation_id="",
        component_heuristic_ids=("a", "b", "c")
    )
    assert composed.get_pattern_description() == "Sequential execution of 3 heuristics"
    print("✓ Valid ComposedHeuristic created successfully")


def run_all_tests():
    """Run all synthesizer tests."""
    print("=" * 60)
    print("Heuristic Synthesizer Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_trace_validation,
        test_composed_heuristic_validation,
        test_synthesizer_creates_composed_heuristic_from_traces,
        test_synthesizer_respects_pattern_threshold,
        test_synthesizer_handles_longer_chains,
        test_synthesize_from_traces_integration
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
        print("✓ All synthesizer tests passed!")
        print("RegionAI can now analyze its own reasoning and create new tools!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)