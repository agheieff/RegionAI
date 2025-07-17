"""
Tests for the proof runner with exponential safety guards.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time
from unittest.mock import Mock

from regionai.reasoning.proof_runner import (
    ProofRunner, ProofMetrics, ProofRunnerPool
)
from regionai.knowledge.exceptions import (
    ExponentialSearchException, ProofTimeoutException
)
from regionai.domains.language.lean_ast import (
    ProofState, Tactic, TacticType, Theorem, Hypothesis
)
from regionai.config import RegionAIConfig


class TestProofMetrics:
    """Test the ProofMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating proof metrics."""
        metrics = ProofMetrics()
        assert metrics.steps_taken == 0
        assert metrics.goal_entropies == []
        assert metrics.backtrack_count == 0
        assert metrics.failed_tactics == 0
    
    def test_elapsed_seconds(self):
        """Test elapsed time calculation."""
        metrics = ProofMetrics()
        time.sleep(0.1)  # Sleep briefly
        elapsed = metrics.elapsed_seconds()
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should be close to sleep time
    
    def test_get_latest_entropy(self):
        """Test getting latest entropy."""
        metrics = ProofMetrics()
        assert metrics.get_latest_entropy() is None
        
        metrics.goal_entropies = [1.0, 0.8, 0.6]
        assert metrics.get_latest_entropy() == 0.6
    
    def test_get_entropy_trend(self):
        """Test entropy trend calculation."""
        metrics = ProofMetrics()
        
        # Not enough data
        assert metrics.get_entropy_trend(window=5) is None
        
        # Decreasing entropy (good progress) - need window+1 items
        metrics.goal_entropies = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
        trend = metrics.get_entropy_trend(window=5)
        assert trend < 0  # Negative slope means decreasing
        
        # Increasing entropy (bad progress)
        metrics.goal_entropies = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        trend = metrics.get_entropy_trend(window=5)
        assert trend > 0  # Positive slope means increasing
        
        # Flat entropy (no progress)
        metrics.goal_entropies = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        trend = metrics.get_entropy_trend(window=5)
        assert abs(trend) < 0.001  # Nearly zero


class TestProofRunner:
    """Test the ProofRunner class."""
    
    def test_basic_creation(self):
        """Test creating a proof runner."""
        runner = ProofRunner()
        assert runner.max_proof_sec == 600.0  # Default from config
        assert runner.progress_window == 50
        assert runner.entropy_epsilon == 0.01
        assert not runner.is_aborted
        assert runner.abort_reason is None
    
    def test_with_custom_config(self):
        """Test runner with custom configuration."""
        config = RegionAIConfig(max_proof_sec=30.0)
        runner = ProofRunner(config=config)
        assert runner.max_proof_sec == 30.0
    
    def test_set_current_heuristic(self):
        """Test setting current heuristic."""
        runner = ProofRunner()
        runner.set_current_heuristic("breadth_first")
        assert runner.current_heuristic == "breadth_first"
    
    def test_time_budget_guard(self):
        """Test Guard A: Global time budget."""
        config = RegionAIConfig(max_proof_sec=0.1)  # Very short timeout
        runner = ProofRunner(config=config)
        
        # Wait for timeout
        time.sleep(0.15)
        
        with pytest.raises(ProofTimeoutException) as exc_info:
            runner.check_abort()
        
        assert runner.is_aborted
        assert "Time budget exceeded" in runner.abort_reason
        assert exc_info.value.timeout_limit == 0.1
    
    def test_step_count_guard(self):
        """Test Guard B: Step count limit."""
        runner = ProofRunner()
        runner.max_steps = 10  # Set very low for testing
        
        # Simulate many steps
        runner.metrics.steps_taken = 11
        
        with pytest.raises(ExponentialSearchException) as exc_info:
            runner.check_abort()
        
        assert runner.is_aborted
        assert "Step limit exceeded" in runner.abort_reason
        assert exc_info.value.steps_taken == 11
    
    def test_entropy_progress_guard(self):
        """Test Guard C: Progress oracle based on entropy."""
        runner = ProofRunner()
        runner.progress_window = 5  # Small window for testing
        runner.current_heuristic = "test_heuristic"
        
        # Simulate lack of progress (flat entropy)
        for i in range(10):
            runner.metrics.goal_entropies.append(0.5)
        
        with pytest.raises(ExponentialSearchException) as exc_info:
            runner.check_abort()
        
        assert runner.is_aborted
        assert "Insufficient progress" in runner.abort_reason
        assert exc_info.value.context['current_heuristic'] == "test_heuristic"
    
    def test_backtrack_guard(self):
        """Test Guard D: Excessive backtracking."""
        runner = ProofRunner()
        runner.metrics.steps_taken = 200
        runner.metrics.backtrack_count = 101  # More than 50%
        
        with pytest.raises(ExponentialSearchException) as exc_info:
            runner.check_abort()
        
        assert runner.is_aborted
        assert "Excessive backtracking" in runner.abort_reason
        assert exc_info.value.context['backtrack_ratio'] > 0.5
    
    def test_record_step(self):
        """Test recording proof steps."""
        runner = ProofRunner()
        
        tactic = Tactic(TacticType.INTRO)
        runner.record_step(tactic, success=True)
        
        assert runner.metrics.steps_taken == 1
        assert len(runner.metrics.tactic_applications) == 1
        assert runner.metrics.failed_tactics == 0
        
        # Record a failed step
        runner.record_step(tactic, success=False)
        assert runner.metrics.steps_taken == 2
        assert runner.metrics.failed_tactics == 1
    
    def test_update_goal_state(self):
        """Test updating goal state and entropy calculation."""
        runner = ProofRunner()
        
        # Empty state (completed)
        state = ProofState(is_complete=True)
        runner.update_goal_state(state)
        assert runner.metrics.goal_entropies[-1] == 0.0
        
        # Single simple goal
        state = ProofState(current_goal="P")
        runner.update_goal_state(state)
        entropy1 = runner.metrics.goal_entropies[-1]
        assert entropy1 > 0
        
        # Multiple complex goals
        state = ProofState(
            current_goal="P → Q → R",
            remaining_goals=["∀x. P(x) → ∃y. Q(x, y)"],
            hypotheses=[Hypothesis("h1", "P"), Hypothesis("h2", "Q")]
        )
        runner.update_goal_state(state)
        entropy2 = runner.metrics.goal_entropies[-1]
        assert entropy2 > entropy1  # More complex state has higher entropy
    
    def test_get_summary(self):
        """Test getting runner summary."""
        runner = ProofRunner()
        runner.current_heuristic = "test_heuristic"
        runner.metrics.steps_taken = 100
        runner.metrics.failed_tactics = 10
        runner.metrics.goal_entropies = [1.0, 0.8, 0.6]
        
        summary = runner.get_summary()
        assert summary['completed'] is True  # Not aborted
        assert summary['steps_taken'] == 100
        assert summary['failed_tactics'] == 10
        assert summary['final_entropy'] == 0.6
        assert summary['responsible_heuristic'] == "test_heuristic"
    
    def test_context_manager(self):
        """Test using runner as context manager."""
        with ProofRunner() as runner:
            assert not runner.is_aborted
            runner.metrics.steps_taken = 5
        
        # Summary should be logged (we can't easily test logging)
        assert runner.metrics.steps_taken == 5
    
    def test_integration_with_trace_recorder(self):
        """Test integration with proof trace recorder."""
        from regionai.reasoning.proof_trace import ProofTraceRecorder
        
        trace_recorder = Mock(spec=ProofTraceRecorder)
        theorem = Theorem(name="test", statement="P")
        
        runner = ProofRunner(trace_recorder=trace_recorder, theorem=theorem)
        
        # Simulate timeout
        runner.max_proof_sec = 0.01
        time.sleep(0.02)
        
        with pytest.raises(ProofTimeoutException):
            runner.check_abort()
        
        # Check that timeout was recorded
        trace_recorder.record_timeout.assert_called_once()
        
        # Check context manager exit records summary
        with runner:
            pass
        trace_recorder.record_custom_event.assert_called()


class TestProofRunnerPool:
    """Test the ProofRunnerPool class."""
    
    def test_pool_creation(self):
        """Test creating a runner pool."""
        pool = ProofRunnerPool(max_runners=4)
        assert pool.max_runners == 4
        assert len(pool.active_runners) == 0
    
    def test_create_runner(self):
        """Test creating runners in pool."""
        pool = ProofRunnerPool(max_runners=2)
        
        runner1 = pool.create_runner()
        assert isinstance(runner1, ProofRunner)
        assert len(pool.active_runners) == 1
        
        pool.create_runner()
        assert len(pool.active_runners) == 2
        
        # Should fail when at max
        with pytest.raises(RuntimeError, match="Maximum number of runners"):
            pool.create_runner()
    
    def test_remove_runner(self):
        """Test removing runner from pool."""
        pool = ProofRunnerPool()
        
        runner = pool.create_runner()
        assert len(pool.active_runners) == 1
        
        pool.remove_runner(runner)
        assert len(pool.active_runners) == 0
        
        # Removing non-existent runner should not error
        pool.remove_runner(runner)  # Already removed
        assert len(pool.active_runners) == 0