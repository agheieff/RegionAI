#!/usr/bin/env python3
"""
Test the UtilityUpdater service for adaptive learning.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tier3.scenarios.utility_updater import UtilityUpdater
from tier3.world_contexts.knowledge.models import Heuristic, ReasoningType


def test_utility_updater_initialization():
    """Test creating a UtilityUpdater."""
    updater = UtilityUpdater()
    
    assert updater.success_rate == 0.1
    assert updater.failure_rate == 0.95
    assert len(updater.context_utilities) == 0


def test_successful_update():
    """Test updating utility after successful execution."""
    updater = UtilityUpdater()
    
    heuristic = Heuristic(
        name="TEST_HEURISTIC",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Test heuristic",
        expected_utility=0.5
    )
    
    # Update after success
    new_utility = updater.update_heuristic_utility(
        heuristic, "test-context", successful=True
    )
    
    # Should increase: 0.5 + (1.0 - 0.5) * 0.1 = 0.55
    assert new_utility == pytest.approx(0.55, rel=1e-3)
    
    # Verify it's stored
    assert updater.get_context_utility(heuristic, "test-context") == pytest.approx(0.55, rel=1e-3)


def test_failed_update():
    """Test updating utility after failed execution."""
    updater = UtilityUpdater()
    
    heuristic = Heuristic(
        name="TEST_HEURISTIC",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Test heuristic",
        expected_utility=0.8
    )
    
    # Update after failure
    new_utility = updater.update_heuristic_utility(
        heuristic, "test-context", successful=False
    )
    
    # Should decrease: 0.8 * 0.95 = 0.76
    assert new_utility == pytest.approx(0.76, rel=1e-3)


def test_multiple_contexts():
    """Test that utilities are tracked separately per context."""
    updater = UtilityUpdater()
    
    heuristic = Heuristic(
        name="MULTI_CONTEXT",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Multi-context heuristic",
        expected_utility=0.6
    )
    
    # Update in different contexts
    updater.update_heuristic_utility(heuristic, "database", successful=True)
    updater.update_heuristic_utility(heuristic, "authentication", successful=False)
    updater.update_heuristic_utility(heuristic, "general", successful=True)
    
    # Check each context has different utility
    db_utility = updater.get_context_utility(heuristic, "database")
    auth_utility = updater.get_context_utility(heuristic, "authentication")
    general_utility = updater.get_context_utility(heuristic, "general")
    
    assert db_utility > 0.6  # Increased from success
    assert auth_utility < 0.6  # Decreased from failure
    assert general_utility > 0.6  # Increased from success
    assert db_utility != auth_utility != general_utility


def test_utility_bounds():
    """Test that utilities stay within valid bounds."""
    updater = UtilityUpdater()
    
    # Test upper bound
    high_heuristic = Heuristic(
        name="HIGH_UTILITY",
        reasoning_type=ReasoningType.HEURISTIC,
        description="High utility heuristic",
        expected_utility=0.99
    )
    
    # Multiple successes shouldn't exceed 1.0
    for _ in range(10):
        new_utility = updater.update_heuristic_utility(
            high_heuristic, "context", successful=True
        )
        assert new_utility <= 1.0
    
    # Test lower bound
    low_heuristic = Heuristic(
        name="LOW_UTILITY",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Low utility heuristic",
        expected_utility=0.15
    )
    
    # Multiple failures shouldn't go below 0.1
    for _ in range(10):
        new_utility = updater.update_heuristic_utility(
            low_heuristic, "context", successful=False
        )
        assert new_utility >= 0.1


def test_get_all_utilities():
    """Test getting all utilities for a heuristic."""
    updater = UtilityUpdater()
    
    heuristic = Heuristic(
        name="TEST_HEURISTIC",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Test",
        expected_utility=0.5
    )
    
    # Update in multiple contexts
    updater.update_heuristic_utility(heuristic, "context1", successful=True)
    updater.update_heuristic_utility(heuristic, "context2", successful=False)
    updater.update_heuristic_utility(heuristic, "context3", successful=True)
    
    # Get all utilities
    all_utilities = updater.get_all_utilities("TEST_HEURISTIC")
    
    assert len(all_utilities) == 3
    assert "context1" in all_utilities
    assert "context2" in all_utilities
    assert "context3" in all_utilities
    assert all_utilities["context1"] > 0.5
    assert all_utilities["context2"] < 0.5


def test_reset_utilities():
    """Test resetting utilities."""
    updater = UtilityUpdater()
    
    heuristic1 = Heuristic(
        name="HEURISTIC_1",
        reasoning_type=ReasoningType.HEURISTIC,
        description="First",
        expected_utility=0.5
    )
    
    heuristic2 = Heuristic(
        name="HEURISTIC_2",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Second",
        expected_utility=0.5
    )
    
    # Update both
    updater.update_heuristic_utility(heuristic1, "context", successful=True)
    updater.update_heuristic_utility(heuristic2, "context", successful=True)
    
    # Reset one
    updater.reset_utilities("HEURISTIC_1")
    
    # Check that only one was reset
    assert updater.get_context_utility(heuristic1, "context") == 0.5  # Back to base
    assert updater.get_context_utility(heuristic2, "context") > 0.5  # Still updated
    
    # Reset all
    updater.reset_utilities()
    assert len(updater.context_utilities) == 0


def test_learning_summary():
    """Test the learning summary generation."""
    updater = UtilityUpdater()
    
    # Empty summary
    assert updater.get_learning_summary() == "No learning has occurred yet."
    
    # Add some learning
    h1 = Heuristic("H1", ReasoningType.HEURISTIC, "Test", expected_utility=0.5)
    h2 = Heuristic("H2", ReasoningType.HEURISTIC, "Test", expected_utility=0.7)
    
    updater.update_heuristic_utility(h1, "database", successful=True)
    updater.update_heuristic_utility(h1, "general", successful=False)
    updater.update_heuristic_utility(h2, "authentication", successful=True)
    
    summary = updater.get_learning_summary()
    
    assert "Heuristic Learning Summary" in summary
    assert "H1:" in summary
    assert "database:" in summary
    assert "general:" in summary
    assert "H2:" in summary
    assert "authentication:" in summary


def test_sequential_learning():
    """Test that learning compounds over multiple executions."""
    updater = UtilityUpdater()
    
    heuristic = Heuristic(
        name="LEARNER",
        reasoning_type=ReasoningType.HEURISTIC,
        description="Learning heuristic",
        expected_utility=0.5
    )
    
    context = "test-context"
    utilities = [0.5]  # Starting utility
    
    # Simulate multiple successful executions
    for _ in range(5):
        new_utility = updater.update_heuristic_utility(
            heuristic, context, successful=True
        )
        utilities.append(new_utility)
    
    # Each utility should be higher than the last
    for i in range(1, len(utilities)):
        assert utilities[i] > utilities[i-1]
    
    # But the increases should get smaller (approaching 1.0)
    differences = [utilities[i] - utilities[i-1] for i in range(1, len(utilities))]
    for i in range(1, len(differences)):
        assert differences[i] < differences[i-1]


if __name__ == "__main__":
    # Run tests
    test_utility_updater_initialization()
    print("✓ Initialization tests passed")
    
    test_successful_update()
    print("✓ Successful update tests passed")
    
    test_failed_update()
    print("✓ Failed update tests passed")
    
    test_multiple_contexts()
    print("✓ Multiple contexts tests passed")
    
    test_utility_bounds()
    print("✓ Utility bounds tests passed")
    
    test_get_all_utilities()
    print("✓ Get all utilities tests passed")
    
    test_reset_utilities()
    print("✓ Reset utilities tests passed")
    
    test_learning_summary()
    print("✓ Learning summary tests passed")
    
    test_sequential_learning()
    print("✓ Sequential learning tests passed")
    
    print("\nAll UtilityUpdater tests passed!")