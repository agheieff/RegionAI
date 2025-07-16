"""
Tests for foundational mathematical heuristics.

This module tests the basic heuristics for mathematical theorem proving,
including intro, exact, and apply tactics.
"""

import unittest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock, MagicMock

from regionai.reasoning.heuristics.math_foundations import (
    heuristic_intro, heuristic_exact, heuristic_apply,
    reset_hypothesis_names, _generate_hypothesis_name, _normalize_expr
)
from regionai.linguistics.lean_ast import ProofState, Hypothesis, Tactic, TacticType


class TestMathFoundationsHeuristics(unittest.TestCase):
    """Test mathematical heuristics."""
    
    def setUp(self):
        """Reset state before each test."""
        reset_hypothesis_names()
    
    def test_normalize_expr(self):
        """Test expression normalization."""
        # Test whitespace normalization
        self.assertEqual(_normalize_expr("p  →   q"), "p → q")
        
        # Test arrow normalization
        self.assertEqual(_normalize_expr("p -> q"), "p → q")
        
        # Test combined
        self.assertEqual(_normalize_expr("  p  ->  q  "), "p → q")
    
    def test_generate_hypothesis_name(self):
        """Test hypothesis name generation."""
        # Empty state should use 'h'
        proof_state = ProofState(hypotheses=[])
        name = _generate_hypothesis_name(proof_state)
        self.assertEqual(name, "h")
        
        # With 'h' taken, should use 'p'
        proof_state = ProofState(hypotheses=[Hypothesis(name="h", type_expr="Prop")])
        name = _generate_hypothesis_name(proof_state)
        self.assertEqual(name, "p")
        
        # With common names taken, should use numbered
        hypotheses = [
            Hypothesis(name=n, type_expr="Prop")
            for n in ["h", "p", "q", "r", "x", "y", "z"]
        ]
        proof_state = ProofState(hypotheses=hypotheses)
        name = _generate_hypothesis_name(proof_state)
        self.assertEqual(name, "h1")
    
    def test_heuristic_intro_success(self):
        """Test intro heuristic on implication goal."""
        # Create mock planner
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state with implication goal
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p → q",
            hypotheses=[]
        )
        
        # Create context
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_intro(None, context)
        
        # Verify result
        self.assertTrue(result)
        mock_planner.add_action.assert_called_once()
        
        # Check the action
        action = mock_planner.add_action.call_args[0][0]
        self.assertEqual(action['type'], 'apply_tactic')
        self.assertEqual(action['heuristic'], 'math.intro')
        self.assertIsInstance(action['tactic'], Tactic)
        self.assertEqual(action['tactic'].tactic_type, TacticType.INTRO)
        self.assertEqual(action['tactic'].arguments, ['h'])
    
    def test_heuristic_intro_no_implication(self):
        """Test intro heuristic on non-implication goal."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state without implication
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p ∧ q",
            hypotheses=[]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_intro(None, context)
        
        # Should not propose action
        self.assertFalse(result)
        mock_planner.add_action.assert_not_called()
    
    def test_heuristic_exact_success(self):
        """Test exact heuristic when hypothesis matches goal."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state where hypothesis matches goal
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p",
            hypotheses=[
                Hypothesis(name="h1", type_expr="q"),
                Hypothesis(name="h2", type_expr="p")  # This matches!
            ]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_exact(None, context)
        
        # Verify result
        self.assertTrue(result)
        mock_planner.add_action.assert_called_once()
        
        # Check the action
        action = mock_planner.add_action.call_args[0][0]
        self.assertEqual(action['type'], 'apply_tactic')
        self.assertEqual(action['heuristic'], 'math.exact')
        self.assertEqual(action['priority'], 1.0)  # Highest priority
        self.assertIsInstance(action['tactic'], Tactic)
        self.assertEqual(action['tactic'].tactic_type, TacticType.EXACT)
        self.assertEqual(action['tactic'].arguments, ['h2'])
    
    def test_heuristic_exact_no_match(self):
        """Test exact heuristic when no hypothesis matches goal."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state where no hypothesis matches
        proof_state = ProofState(
            theorem_name="test",
            current_goal="r",
            hypotheses=[
                Hypothesis(name="h1", type_expr="p"),
                Hypothesis(name="h2", type_expr="q")
            ]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_exact(None, context)
        
        # Should not propose action
        self.assertFalse(result)
        mock_planner.add_action.assert_not_called()
    
    def test_heuristic_apply_success(self):
        """Test apply heuristic with matching implication."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state with applicable implication
        proof_state = ProofState(
            theorem_name="test",
            current_goal="q",
            hypotheses=[
                Hypothesis(name="h1", type_expr="p"),
                Hypothesis(name="h2", type_expr="p → q")  # This applies!
            ]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_apply(None, context)
        
        # Verify result
        self.assertTrue(result)
        mock_planner.add_action.assert_called_once()
        
        # Check the action
        action = mock_planner.add_action.call_args[0][0]
        self.assertEqual(action['type'], 'apply_tactic')
        self.assertEqual(action['heuristic'], 'math.apply')
        self.assertIsInstance(action['tactic'], Tactic)
        self.assertEqual(action['tactic'].tactic_type, TacticType.APPLY)
        self.assertEqual(action['tactic'].arguments, ['h2'])
    
    def test_heuristic_apply_complex_implication(self):
        """Test apply heuristic with complex implications."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state with multiple implications
        proof_state = ProofState(
            theorem_name="test",
            current_goal="r",
            hypotheses=[
                Hypothesis(name="h1", type_expr="p → q → r"),  # Complex premise
                Hypothesis(name="h2", type_expr="q → r"),      # Simpler premise
                Hypothesis(name="h3", type_expr="p → s")       # Wrong conclusion
            ]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_apply(None, context)
        
        # Should prefer h2 (simpler premise)
        self.assertTrue(result)
        action = mock_planner.add_action.call_args[0][0]
        self.assertEqual(action['tactic'].arguments, ['h2'])
        # Priority should be based on simplicity
        self.assertGreater(action['priority'], 0.3)
    
    def test_heuristic_apply_no_match(self):
        """Test apply heuristic with no matching implications."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Create proof state with no applicable implications
        proof_state = ProofState(
            theorem_name="test",
            current_goal="s",
            hypotheses=[
                Hypothesis(name="h1", type_expr="p → q"),
                Hypothesis(name="h2", type_expr="q → r")
            ]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        # Execute heuristic
        result = heuristic_apply(None, context)
        
        # Should not propose action
        self.assertFalse(result)
        mock_planner.add_action.assert_not_called()
    
    def test_missing_context_elements(self):
        """Test heuristics with missing context elements."""
        # Test with missing proof_state
        context = {'planner': Mock()}
        self.assertFalse(heuristic_intro(None, context))
        self.assertFalse(heuristic_exact(None, context))
        self.assertFalse(heuristic_apply(None, context))
        
        # Test with missing planner
        proof_state = ProofState(current_goal="p → q")
        context = {'proof_state': proof_state}
        self.assertFalse(heuristic_intro(None, context))
        self.assertFalse(heuristic_exact(None, context))
        self.assertFalse(heuristic_apply(None, context))
    
    def test_arrow_notation_variants(self):
        """Test heuristics work with different arrow notations."""
        mock_planner = Mock()
        mock_planner.add_action = MagicMock()
        
        # Test intro with ASCII arrow
        proof_state = ProofState(
            current_goal="p -> q",  # ASCII arrow
            hypotheses=[]
        )
        
        context = {
            'proof_state': proof_state,
            'planner': mock_planner
        }
        
        result = heuristic_intro(None, context)
        self.assertTrue(result)
        
        # Reset for apply test
        mock_planner.reset_mock()
        
        # Test apply with mixed arrows
        proof_state = ProofState(
            current_goal="q",
            hypotheses=[Hypothesis(name="h", type_expr="p -> q")]  # ASCII
        )
        
        context['proof_state'] = proof_state
        result = heuristic_apply(None, context)
        self.assertTrue(result)


class TestHypothesisNameGeneration(unittest.TestCase):
    """Test hypothesis name generation across multiple proofs."""
    
    def test_name_persistence_across_calls(self):
        """Test that names persist across multiple calls."""
        reset_hypothesis_names()
        
        # First call uses 'h'
        proof_state = ProofState(hypotheses=[])
        name1 = _generate_hypothesis_name(proof_state)
        self.assertEqual(name1, "h")
        
        # Second call should not reuse 'h'
        name2 = _generate_hypothesis_name(proof_state)
        self.assertEqual(name2, "p")
        
        # After reset, 'h' should be available again
        reset_hypothesis_names()
        name3 = _generate_hypothesis_name(proof_state)
        self.assertEqual(name3, "h")


if __name__ == '__main__':
    unittest.main()