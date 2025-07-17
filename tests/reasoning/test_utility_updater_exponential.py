"""
Tests for UtilityUpdater exponential failure handling.
"""

from unittest.mock import patch

from regionai.reasoning.utility_updater import UtilityUpdater
from regionai.knowledge.models import Heuristic, ReasoningType


class TestUtilityUpdaterExponentialFailure:
    """Test the UtilityUpdater's handling of exponential failures."""
    
    def test_handle_exponential_failure_new_heuristic(self):
        """Test handling exponential failure for a new heuristic."""
        updater = UtilityUpdater()
        
        # Handle failure for a heuristic not seen before
        new_utility = updater.handle_exponential_failure(
            heuristic_name="breadth_first",
            context="proof_search",
            details="Search space grew to 10^6 nodes"
        )
        
        # Should apply severe penalty (penalty calculation: max(0.1, 0.5 - 0.5) = 0.1)
        assert new_utility == 0.1  # For new heuristic, starts at 0.5, penalty brings it to minimum 0.1
        assert "breadth_first" in updater.context_utilities
        assert updater.context_utilities["breadth_first"]["proof_search"] == 0.1
    
    def test_handle_exponential_failure_existing_heuristic(self):
        """Test handling exponential failure for existing heuristic."""
        updater = UtilityUpdater()
        
        # Set up initial utility
        heuristic = Heuristic(
            name="depth_first",
            reasoning_type=ReasoningType.HEURISTIC,
            description="Depth-first search heuristic",
            expected_utility=0.8
        )
        updater.update_heuristic_utility(heuristic, "proof_search", successful=True)
        initial_utility = updater.get_context_utility(heuristic, "proof_search")
        assert initial_utility > 0.8  # Should have increased
        
        # Now handle exponential failure
        new_utility = updater.handle_exponential_failure(
            heuristic_name="depth_first",
            context="proof_search",
            details="Infinite recursion detected"
        )
        
        # Should be severely reduced
        assert new_utility < initial_utility
        assert new_utility < 0.4  # Should be severely reduced
    
    def test_exponential_penalty_calculation(self):
        """Test the penalty calculation for exponential failures."""
        updater = UtilityUpdater()
        
        # Test with different starting utilities
        # Penalty is 10.0 * 0.05 = 0.5, so max(0.1, start_utility - 0.5)
        test_cases = [
            (0.9, 0.4),   # High utility -> 0.9 - 0.5 = 0.4
            (0.5, 0.1),   # Medium utility -> max(0.1, 0.5 - 0.5) = 0.1
            (0.2, 0.1),   # Low utility -> max(0.1, 0.2 - 0.5) = 0.1 (stays at floor)
            (0.1, 0.1),   # Already at minimum -> max(0.1, 0.1 - 0.5) = 0.1
        ]
        
        for start_utility, expected in test_cases:
            # Set initial utility
            updater.context_utilities["test_heuristic"] = {
                "test_context": start_utility
            }
            
            # Apply exponential penalty
            new_utility = updater.handle_exponential_failure(
                heuristic_name="test_heuristic",
                context="test_context"
            )
            
            assert new_utility == expected
    
    def test_exponential_failure_different_contexts(self):
        """Test that exponential failure only affects specific context."""
        updater = UtilityUpdater()
        
        # Set up utilities in multiple contexts
        heuristic = Heuristic(
            name="multi_context", 
            reasoning_type=ReasoningType.HEURISTIC,
            description="Multi-context heuristic",
            expected_utility=0.7
        )
        updater.update_heuristic_utility(heuristic, "context1", successful=True)
        updater.update_heuristic_utility(heuristic, "context2", successful=True)
        
        # Handle exponential failure in context1
        updater.handle_exponential_failure(
            heuristic_name="multi_context",
            context="context1",
            details="Exploded in context1"
        )
        
        # Check that only context1 was penalized
        context1_utility = updater.get_context_utility(heuristic, "context1")
        context2_utility = updater.get_context_utility(heuristic, "context2")
        
        assert context1_utility >= 0.1  # Should be at least the minimum
        assert context1_utility < 0.7   # Should be penalized from original
        assert context2_utility > 0.7   # Unaffected
    
    @patch('regionai.reasoning.utility_updater.logger')
    def test_exponential_failure_logging(self, mock_logger):
        """Test that exponential failures are properly logged."""
        updater = UtilityUpdater()
        
        updater.handle_exponential_failure(
            heuristic_name="test_heuristic",
            context="test_context",
            details="Test failure details"
        )
        
        # Check warning was logged
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "test_heuristic" in warning_msg
        assert "test_context" in warning_msg
        assert "Test failure details" in warning_msg
        
        # Check info was logged
        mock_logger.info.assert_called_once()
        info_msg = mock_logger.info.call_args[0][0]
        assert "0.500 -> 0.100" in info_msg  # Default to expected adjustment
        assert "exponential penalty" in info_msg
    
    def test_learning_summary_includes_exponential_penalties(self):
        """Test that learning summary shows exponentially penalized heuristics."""
        updater = UtilityUpdater()
        
        # Set up some normal updates
        h1 = Heuristic(
            name="good_heuristic", 
            reasoning_type=ReasoningType.HEURISTIC,
            description="Good heuristic for testing",
            expected_utility=0.5
        )
        updater.update_heuristic_utility(h1, "context1", successful=True)
        
        # Add exponential failure
        updater.handle_exponential_failure(
            heuristic_name="bad_heuristic",
            context="proof_search"
        )
        
        summary = updater.get_learning_summary()
        
        assert "good_heuristic" in summary
        assert "bad_heuristic" in summary
        assert "proof_search: 0.100" in summary  # Shows minimum utility
    
    def test_reset_clears_exponential_penalties(self):
        """Test that reset clears exponentially penalized utilities."""
        updater = UtilityUpdater()
        
        # Apply exponential penalty
        updater.handle_exponential_failure("heuristic1", "context1")
        assert "heuristic1" in updater.context_utilities
        
        # Reset specific heuristic
        updater.reset_utilities("heuristic1")
        assert "heuristic1" not in updater.context_utilities
        
        # Apply another penalty
        updater.handle_exponential_failure("heuristic2", "context2")
        
        # Reset all
        updater.reset_utilities()
        assert len(updater.context_utilities) == 0