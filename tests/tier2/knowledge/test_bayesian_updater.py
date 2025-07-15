"""
Tests for the BayesianUpdater service.
"""
import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tier3.world_contexts.knowledge.graph import WorldKnowledgeGraph, Concept, Relation
from tier3.world_contexts.knowledge.bayesian_updater import BayesianUpdater


@pytest.fixture
def base_graph():
    """Creates a simple WorldKnowledgeGraph for testing."""
    kg = WorldKnowledgeGraph()
    kg.add_concept(Concept("User"))
    kg.add_concept(Concept("Order"))
    kg.add_relation(
        Concept("User"),
        Concept("Order"),
        Relation("HAS_MANY")
        # Starts with alpha=1.0, beta=1.0 (belief=0.5)
    )
    return kg


def test_positive_evidence_increases_belief(base_graph):
    """Test that positive evidence correctly increases the belief score."""
    updater = BayesianUpdater(base_graph)
    
    # Get initial belief
    edge_data = list(base_graph.graph.edges(data=True))[0][2]
    initial_belief = edge_data['metadata'].belief
    assert initial_belief == pytest.approx(0.5)

    # Update with strong positive evidence
    updater.update_belief(
        Concept("User"),
        Concept("Order"),
        Relation("HAS_MANY"),
        evidence_is_positive=True,
        source_credibility=0.9
    )

    # Verify belief has increased
    edge_data = list(base_graph.graph.edges(data=True))[0][2]
    new_belief = edge_data['metadata'].belief
    assert new_belief > initial_belief
    assert new_belief > 0.6  # With 0.9 credibility from (1,1) we get ~0.655


def test_negative_evidence_decreases_belief(base_graph):
    """Test that negative evidence correctly decreases the belief score."""
    updater = BayesianUpdater(base_graph)

    # Update with strong negative evidence
    updater.update_belief(
        Concept("User"),
        Concept("Order"),
        Relation("HAS_MANY"),
        evidence_is_positive=False,
        source_credibility=0.9
    )

    # Verify belief has decreased
    edge_data = list(base_graph.graph.edges(data=True))[0][2]
    new_belief = edge_data['metadata'].belief
    assert new_belief < 0.5
    assert new_belief < 0.4  # With 0.9 credibility from (1,1) we get ~0.345


def test_conflicting_evidence_leads_to_uncertainty(base_graph):
    """Test that conflicting evidence moves belief towards 0.5."""
    updater = BayesianUpdater(base_graph)

    # Add strong positive evidence
    updater.update_belief(Concept("User"), Concept("Order"), Relation("HAS_MANY"), True, 1.0)
    # Add equally strong negative evidence
    updater.update_belief(Concept("User"), Concept("Order"), Relation("HAS_MANY"), False, 1.0)
    
    # Verify belief is back near 0.5 (max uncertainty)
    edge_data = list(base_graph.graph.edges(data=True))[0][2]
    final_belief = edge_data['metadata'].belief
    assert final_belief == pytest.approx(0.5)