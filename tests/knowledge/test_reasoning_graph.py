#!/usr/bin/env python3
"""
Tests for the Reasoning Knowledge Graph.

Verifies that the ReasoningKnowledgeGraph is properly populated with
initial reasoning concepts and heuristics.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier3.world_contexts.knowledge.hub import KnowledgeHub
from tier3.world_contexts.knowledge.models import ReasoningConcept, Heuristic, ReasoningType


def test_reasoning_graph_initialization():
    """Test that the reasoning graph is populated on initialization."""
    print("Testing reasoning graph initialization...")
    
    # Initialize a KnowledgeHub
    hub = KnowledgeHub()
    
    # Get the reasoning knowledge graph
    rkg = hub.rkg
    
    # Check that it contains nodes
    assert len(rkg) > 0, "Reasoning graph should not be empty"
    print(f"✓ Reasoning graph contains {len(rkg)} nodes")
    
    # Count different types of nodes
    concepts = []
    heuristics = []
    
    for node in rkg.graph.nodes():
        if isinstance(node, Heuristic):
            heuristics.append(node)
        elif isinstance(node, ReasoningConcept):
            concepts.append(node)
    
    print(f"✓ Found {len(concepts)} reasoning concepts")
    print(f"✓ Found {len(heuristics)} heuristics")
    
    assert len(concepts) >= 6, "Should have at least 6 reasoning concepts"
    assert len(heuristics) >= 8, "Should have at least 8 heuristics"


def test_specific_concepts_exist():
    """Test that specific expected concepts exist."""
    print("\nTesting specific concepts...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    expected_concepts = [
        "Concept Co-occurrence",
        "Action Inference",
        "Sequential Analysis",
        "CRUD Pattern Recognition",
        "Semantic Relationship Extraction",
        "Bayesian Belief Update"
    ]
    
    # Get all concept names
    concept_names = []
    for node in rkg.graph.nodes():
        if isinstance(node, ReasoningConcept):
            concept_names.append(node.name)
    
    # Check each expected concept exists
    for expected in expected_concepts:
        assert expected in concept_names, f"Expected concept '{expected}' not found"
        print(f"✓ Found concept: {expected}")


def test_specific_heuristics_exist():
    """Test that specific expected heuristics exist."""
    print("\nTesting specific heuristics...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    expected_heuristics = [
        ("Co-occurrence in function name implies RELATED_TO", 0.75),
        ("Method call implies PERFORMS", 0.85),
        ("Sequential AST nodes imply PRECEDES", 0.95),
        ("CRUD operations identify domain entities", 0.90),
        ("'has many' phrase implies HAS_MANY relationship", 0.80),
        ("'belongs to' phrase implies BELONGS_TO relationship", 0.80),
        ("Multiple evidence sources strengthen belief", 0.85)
    ]
    
    # Get all heuristics
    heuristics = {}
    for node in rkg.graph.nodes():
        if isinstance(node, Heuristic):
            heuristics[node.name] = node
    
    # Check each expected heuristic
    for name, expected_score in expected_heuristics:
        assert name in heuristics, f"Expected heuristic '{name}' not found"
        heuristic = heuristics[name]
        actual_score = heuristic.utility_model.get('default', heuristic.expected_utility)
        assert actual_score == expected_score, \
            f"Heuristic '{name}' has wrong utility: {actual_score} != {expected_score}"
        print(f"✓ Found heuristic: {name} (score: {expected_score})")


def test_heuristic_concept_relationships():
    """Test that heuristics are properly related to their parent concepts."""
    print("\nTesting heuristic-concept relationships...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    # Map of heuristic names to their parent concept names
    expected_relationships = {
        "Co-occurrence in function name implies RELATED_TO": "Concept Co-occurrence",
        "Method call implies PERFORMS": "Action Inference",
        "Sequential AST nodes imply PRECEDES": "Sequential Analysis",
        "CRUD operations identify domain entities": "CRUD Pattern Recognition",
        "'has many' phrase implies HAS_MANY relationship": "Semantic Relationship Extraction",
        "'belongs to' phrase implies BELONGS_TO relationship": "Semantic Relationship Extraction",
        "Multiple evidence sources strengthen belief": "Bayesian Belief Update"
    }
    
    # Get nodes by name for easier lookup
    nodes_by_name = {}
    for node in rkg.graph.nodes():
        nodes_by_name[node.name] = node
    
    # Check each relationship
    for heuristic_name, concept_name in expected_relationships.items():
        heuristic = nodes_by_name.get(heuristic_name)
        concept = nodes_by_name.get(concept_name)
        
        assert heuristic is not None, f"Heuristic '{heuristic_name}' not found"
        assert concept is not None, f"Concept '{concept_name}' not found"
        
        # Check if there's an edge from heuristic to concept
        has_relationship = False
        for source, target, data in rkg.graph.edges(data=True):
            if source == heuristic and target == concept:
                if data.get('label') == "IS_A_TYPE_OF":
                    has_relationship = True
                    break
        
        assert has_relationship, \
            f"Missing IS_A_TYPE_OF relationship from '{heuristic_name}' to '{concept_name}'"
        print(f"✓ {heuristic_name} → IS_A_TYPE_OF → {concept_name}")


def test_metadata_populated():
    """Test that nodes have proper metadata."""
    print("\nTesting metadata...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    # Check that all nodes have metadata
    for node in rkg.graph.nodes():
        node_data = rkg.graph.nodes[node]
        assert 'metadata' in node_data, f"Node '{node.name}' missing metadata"
        metadata = node_data['metadata']
        
        assert metadata.discovery_source == "built-in", \
            f"Node '{node.name}' has wrong discovery_source: {metadata.discovery_source}"
        assert len(metadata.context_tags) > 0, \
            f"Node '{node.name}' has no context tags"
    
    print("✓ All nodes have proper metadata")


def test_inter_concept_relationships():
    """Test relationships between high-level concepts."""
    print("\nTesting inter-concept relationships...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    # Get specific concepts
    nodes_by_name = {}
    for node in rkg.graph.nodes():
        nodes_by_name[node.name] = node
    
    semantic_extraction = nodes_by_name.get("Semantic Relationship Extraction")
    bayesian = nodes_by_name.get("Bayesian Belief Update")
    
    assert semantic_extraction is not None
    assert bayesian is not None
    
    # Check for USES relationship
    has_uses = False
    for source, target, data in rkg.graph.edges(data=True):
        if source == semantic_extraction and target == bayesian:
            if data.get('label') == "USES":
                has_uses = True
                assert data.get('confidence', 0) == 0.9
                break
    
    assert has_uses, "Missing USES relationship from Semantic Extraction to Bayesian Update"
    print("✓ Semantic Relationship Extraction → USES → Bayesian Belief Update")


def test_reasoning_types():
    """Test that concepts have correct reasoning types."""
    print("\nTesting reasoning types...")
    
    hub = KnowledgeHub()
    rkg = hub.rkg
    
    expected_types = {
        "Concept Co-occurrence": ReasoningType.PATTERN,
        "Action Inference": ReasoningType.PATTERN,
        "Sequential Analysis": ReasoningType.PATTERN,
        "CRUD Pattern Recognition": ReasoningType.PATTERN,
        "Semantic Relationship Extraction": ReasoningType.PATTERN,
        "Bayesian Belief Update": ReasoningType.PRINCIPLE
    }
    
    # Check each concept's type
    for node in rkg.graph.nodes():
        if isinstance(node, ReasoningConcept) and not isinstance(node, Heuristic):
            expected_type = expected_types.get(node.name)
            if expected_type:
                assert node.reasoning_type == expected_type, \
                    f"{node.name} has wrong type: {node.reasoning_type} != {expected_type}"
                print(f"✓ {node.name}: {node.reasoning_type.value}")


def run_all_tests():
    """Run all reasoning graph tests."""
    print("=" * 60)
    print("Reasoning Knowledge Graph Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_reasoning_graph_initialization,
        test_specific_concepts_exist,
        test_specific_heuristics_exist,
        test_heuristic_concept_relationships,
        test_metadata_populated,
        test_inter_concept_relationships,
        test_reasoning_types
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
        print("The Reasoning Knowledge Graph is properly initialized!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)