"""
Tests for Planner integration with ProofRunner.
"""

from unittest.mock import Mock, patch

from regionai.scenarios.planner import Planner
from regionai.scenarios.utility_updater import UtilityUpdater
from regionai.world_contexts.knowledge.models import ReasoningKnowledgeGraph, Heuristic
from regionai.linguistics.lean_ast import Theorem, ProofState
from regionai.knowledge.exceptions import ExponentialSearchException
from regionai.knowledge.planning import ExecutionPlan


class TestPlannerProofIntegration:
    """Test the Planner's proof attempt functionality."""
    
    def create_mock_rkg_with_proof_heuristics(self):
        """Create a mock RKG with proof-related heuristics."""
        rkg = Mock(spec=ReasoningKnowledgeGraph)
        
        # Create some proof heuristics
        h1 = Heuristic(
            name="intro_first",
            expected_utility=0.8,
            applicability_conditions=["proof", "implication"]
        )
        h2 = Heuristic(
            name="apply_hypothesis",
            expected_utility=0.7,
            applicability_conditions=["proof", "hypothesis_available"]
        )
        h3 = Heuristic(
            name="general_proof",
            expected_utility=0.5,
            applicability_conditions=["proof"]
        )
        
        # Mock the graph nodes
        rkg.graph.nodes.return_value = [h1, h2, h3]
        
        return rkg, [h1, h2, h3]
    
    def test_attempt_proof_success(self):
        """Test successful proof attempt."""
        planner = Planner()
        rkg, heuristics = self.create_mock_rkg_with_proof_heuristics()
        
        theorem = Theorem(
            name="simple",
            statement="P → P",
            hypotheses=[]
        )
        
        # Mock the proof runner to simulate success
        with patch('regionai.reasoning.planner.ProofRunner') as MockRunner:
            mock_runner = MockRunner.return_value.__enter__.return_value
            mock_runner.metrics.final_status = 'success'
            
            # Override check_abort to not actually abort
            mock_runner.check_abort.return_value = None
            
            # Create a mock proof state that becomes completed
            proof_state = Mock(spec=ProofState)
            proof_state.completed = False
            
            # Make it complete after first iteration
            def side_effect():
                proof_state.completed = True
            
            mock_runner.update_goal_state.side_effect = side_effect
            
            result = planner.attempt_proof(theorem, rkg)
            
            assert isinstance(result, ExecutionPlan)
            assert result.status == "COMPLETED"
            assert len(result.steps) > 0
            assert mock_runner.set_current_heuristic.called
    
    def test_attempt_proof_exponential_failure(self):
        """Test proof attempt that triggers exponential search exception."""
        utility_updater = Mock(spec=UtilityUpdater)
        planner = Planner(utility_updater=utility_updater)
        rkg, heuristics = self.create_mock_rkg_with_proof_heuristics()
        
        theorem = Theorem(
            name="complex",
            statement="∀x. P(x) → ∃y. Q(x, y)",
            hypotheses=[]
        )
        
        # Mock the proof runner to raise ExponentialSearchException
        with patch('regionai.reasoning.planner.ProofRunner') as MockRunner:
            mock_runner = MockRunner.return_value.__enter__.return_value
            
            # Make check_abort raise exception
            exc = ExponentialSearchException(
                "Exponential growth detected",
                elapsed_time=100.0,
                steps_taken=5000,
                context={'current_heuristic': 'intro_first'}
            )
            mock_runner.check_abort.side_effect = exc
            
            result = planner.attempt_proof(theorem, rkg)
            
            assert result.status == "FAILED"
            assert "Exponential search" in result.failure_reason
            assert len(result.steps) == 0
            
            # Check that utility updater was called
            utility_updater.handle_exponential_failure.assert_called_once_with(
                heuristic_name='intro_first',
                context='proof_search',
                details=str(exc)
            )
    
    def test_attempt_proof_no_heuristics(self):
        """Test proof attempt when no heuristics are available."""
        planner = Planner()
        
        # Create RKG with no proof heuristics
        rkg = Mock(spec=ReasoningKnowledgeGraph)
        rkg.graph.nodes.return_value = []  # No heuristics
        
        theorem = Theorem(name="test", statement="P")
        
        result = planner.attempt_proof(theorem, rkg)
        
        assert result.status == "FAILED"
        assert len(result.steps) == 0
    
    def test_get_proof_heuristics(self):
        """Test getting proof-specific heuristics."""
        planner = Planner()
        rkg, heuristics = self.create_mock_rkg_with_proof_heuristics()
        
        proof_heuristics = planner._get_proof_heuristics(rkg)
        
        assert len(proof_heuristics) == 3
        assert all(h in heuristics for h in proof_heuristics)
        # Should be sorted by utility
        assert proof_heuristics[0].name == "intro_first"
        assert proof_heuristics[1].name == "apply_hypothesis"
        assert proof_heuristics[2].name == "general_proof"
    
    def test_get_proof_heuristics_with_utility_updater(self):
        """Test proof heuristic selection with learned utilities."""
        utility_updater = Mock(spec=UtilityUpdater)
        # Make intro_first have lower learned utility
        utility_updater.get_effective_utility.side_effect = lambda h, c: {
            "intro_first": 0.3,
            "apply_hypothesis": 0.9,
            "general_proof": 0.5
        }.get(h.name, h.expected_utility)
        
        planner = Planner(utility_updater=utility_updater)
        rkg, _ = self.create_mock_rkg_with_proof_heuristics()
        
        proof_heuristics = planner._get_proof_heuristics(rkg)
        
        # Order should be different due to learned utilities
        assert proof_heuristics[0].name == "apply_hypothesis"
        assert proof_heuristics[1].name == "general_proof"
        assert proof_heuristics[2].name == "intro_first"
    
    def test_attempt_proof_with_trace_recorder(self):
        """Test proof attempt with trace recording."""
        from regionai.scenarios.proof_trace import ProofTraceRecorder
        
        planner = Planner()
        rkg, _ = self.create_mock_rkg_with_proof_heuristics()
        trace_recorder = Mock(spec=ProofTraceRecorder)
        
        theorem = Theorem(name="traced", statement="P ∨ ¬P")
        
        with patch('regionai.reasoning.planner.ProofRunner') as MockRunner:
            mock_runner = MockRunner.return_value.__enter__.return_value
            mock_runner.check_abort.return_value = None
            
            # Make proof complete quickly
            proof_state = Mock(spec=ProofState)
            proof_state.completed = True
            mock_runner.update_goal_state.return_value = None
            
            planner.attempt_proof(theorem, rkg, trace_recorder)
            
            # Check that runner was created with trace recorder
            MockRunner.assert_called_once_with(
                trace_recorder=trace_recorder,
                theorem=theorem
            )
    
    def test_select_best_proof_heuristic(self):
        """Test selecting best heuristic for proof state."""
        planner = Planner()
        
        h1 = Heuristic(name="h1", expected_utility=0.8)
        h2 = Heuristic(name="h2", expected_utility=0.9)
        heuristics = [h1, h2]
        
        proof_state = ProofState(goals=["P → Q"])
        
        # Should return highest utility heuristic
        best = planner._select_best_proof_heuristic(proof_state, heuristics)
        assert best == h1  # First in list
        
        # Empty heuristics
        best = planner._select_best_proof_heuristic(proof_state, [])
        assert best is None