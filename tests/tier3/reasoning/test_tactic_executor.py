"""
Tests for the tactic executor module.

This module tests the TacticExecutor class, which bridges RegionAI's
reasoning system with the external Lean theorem prover.
"""

import unittest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import patch, MagicMock
import subprocess

from tier3.scenarios.tactic_executor import (
    TacticExecutor, MockTacticExecutor, TacticExecutionError, LeanNotFoundError
)
from tier2.linguistics.lean_ast import ProofState, Tactic, TacticType, Hypothesis


class TestTacticExecutor(unittest.TestCase):
    """Test the TacticExecutor class."""
    
    @patch('subprocess.run')
    def test_lean_verification(self, mock_run):
        """Test Lean installation verification."""
        # Mock successful Lean verification
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Lean (version 4.0.0)"
        mock_run.return_value = mock_result
        
        # Should not raise exception
        executor = TacticExecutor()
        self.assertEqual(executor.lean_path, "lean")
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args, ["lean", "--version"])
    
    @patch('subprocess.run')
    def test_lean_not_found(self, mock_run):
        """Test handling of missing Lean installation."""
        # Mock Lean not found
        mock_run.side_effect = FileNotFoundError("lean not found")
        
        # Should raise LeanNotFoundError
        with self.assertRaises(LeanNotFoundError):
            TacticExecutor()
    
    @patch('subprocess.run')
    def test_execute_intro_tactic(self, mock_run):
        """Test executing an intro tactic."""
        # Mock Lean verification
        mock_verify = MagicMock()
        mock_verify.returncode = 0
        mock_verify.stdout = "Lean (version 4.0.0)"
        
        # Mock tactic execution output
        mock_exec = MagicMock()
        mock_exec.returncode = 0
        mock_exec.stdout = """
        h : p
        ⊢ q
        """
        mock_exec.stderr = ""
        
        mock_run.side_effect = [mock_verify, mock_exec]
        
        # Create executor and proof state
        executor = TacticExecutor()
        proof_state = ProofState(
            theorem_name="test_theorem",
            current_goal="p → q",
            hypotheses=[]
        )
        
        # Execute intro tactic
        tactic = Tactic(
            tactic_type=TacticType.INTRO,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify new state
        self.assertEqual(new_state.current_goal, "q")
        self.assertEqual(len(new_state.hypotheses), 1)
        self.assertEqual(new_state.hypotheses[0].name, "h")
        self.assertEqual(new_state.hypotheses[0].type_expr, "p")
        self.assertFalse(new_state.is_complete)
    
    @patch('subprocess.run')
    def test_execute_exact_tactic_success(self, mock_run):
        """Test executing an exact tactic that completes the proof."""
        # Mock Lean verification
        mock_verify = MagicMock()
        mock_verify.returncode = 0
        mock_verify.stdout = "Lean (version 4.0.0)"
        
        # Mock tactic execution output - goals accomplished
        mock_exec = MagicMock()
        mock_exec.returncode = 0
        mock_exec.stdout = "goals accomplished"
        mock_exec.stderr = ""
        
        mock_run.side_effect = [mock_verify, mock_exec]
        
        # Create executor and proof state
        executor = TacticExecutor()
        proof_state = ProofState(
            theorem_name="test_theorem",
            current_goal="p",
            hypotheses=[Hypothesis(name="h", type_expr="p")]
        )
        
        # Execute exact tactic
        tactic = Tactic(
            tactic_type=TacticType.EXACT,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify proof is complete
        self.assertTrue(new_state.is_complete)
        self.assertEqual(new_state.current_goal, "")
        self.assertEqual(len(new_state.remaining_goals), 0)
    
    @patch('subprocess.run')
    def test_execute_tactic_error(self, mock_run):
        """Test handling of tactic execution errors."""
        # Mock Lean verification
        mock_verify = MagicMock()
        mock_verify.returncode = 0
        mock_verify.stdout = "Lean (version 4.0.0)"
        
        # Mock tactic execution error
        mock_exec = MagicMock()
        mock_exec.returncode = 1
        mock_exec.stdout = ""
        mock_exec.stderr = "error: tactic 'exact' failed, unable to find matching hypothesis"
        
        mock_run.side_effect = [mock_verify, mock_exec]
        
        # Create executor and proof state
        executor = TacticExecutor()
        proof_state = ProofState(
            theorem_name="test_theorem",
            current_goal="q",
            hypotheses=[Hypothesis(name="h", type_expr="p")]
        )
        
        # Execute exact tactic (should fail)
        tactic = Tactic(
            tactic_type=TacticType.EXACT,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify error is recorded
        self.assertFalse(new_state.is_complete)
        self.assertEqual(new_state.current_goal, "q")  # Goal unchanged
        self.assertIn('last_error', new_state.metadata)
        self.assertIn('failed', new_state.metadata['last_error'])
    
    @patch('subprocess.run')
    def test_tactic_timeout(self, mock_run):
        """Test handling of tactic execution timeout."""
        # Mock Lean verification
        mock_verify = MagicMock()
        mock_verify.returncode = 0
        mock_verify.stdout = "Lean (version 4.0.0)"
        
        # Mock timeout
        mock_run.side_effect = [mock_verify, subprocess.TimeoutExpired("lean", 30)]
        
        # Create executor with short timeout
        executor = TacticExecutor(timeout=1)
        proof_state = ProofState(
            theorem_name="test_theorem",
            current_goal="p",
            hypotheses=[]
        )
        
        # Execute tactic
        tactic = Tactic(tactic_type=TacticType.SIMP)
        
        # Should raise TacticExecutionError
        with self.assertRaises(TacticExecutionError) as cm:
            executor.execute_tactic(proof_state, tactic)
        
        self.assertIn("timed out", str(cm.exception))


class TestMockTacticExecutor(unittest.TestCase):
    """Test the MockTacticExecutor for development and testing."""
    
    def test_mock_intro_tactic(self):
        """Test mock intro tactic execution."""
        executor = MockTacticExecutor()
        
        # Create proof state with implication goal
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p → q",
            hypotheses=[]
        )
        
        # Execute intro
        tactic = Tactic(
            tactic_type=TacticType.INTRO,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify result
        self.assertEqual(new_state.current_goal, "q")
        self.assertEqual(len(new_state.hypotheses), 1)
        self.assertEqual(new_state.hypotheses[0].name, "h")
        self.assertEqual(new_state.hypotheses[0].type_expr, "p")
    
    def test_mock_exact_tactic_success(self):
        """Test mock exact tactic that succeeds."""
        executor = MockTacticExecutor()
        
        # Create proof state where hypothesis matches goal
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p",
            hypotheses=[Hypothesis(name="h", type_expr="p")]
        )
        
        # Execute exact
        tactic = Tactic(
            tactic_type=TacticType.EXACT,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify proof is complete
        self.assertTrue(new_state.is_complete)
        self.assertEqual(new_state.current_goal, "")
    
    def test_mock_exact_tactic_failure(self):
        """Test mock exact tactic that fails."""
        executor = MockTacticExecutor()
        
        # Create proof state where hypothesis doesn't match goal
        proof_state = ProofState(
            theorem_name="test",
            current_goal="q",
            hypotheses=[Hypothesis(name="h", type_expr="p")]
        )
        
        # Execute exact
        tactic = Tactic(
            tactic_type=TacticType.EXACT,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify failure
        self.assertFalse(new_state.is_complete)
        self.assertEqual(new_state.current_goal, "q")  # Unchanged
        self.assertIn('last_error', new_state.metadata)
    
    def test_mock_apply_tactic(self):
        """Test mock apply tactic."""
        executor = MockTacticExecutor()
        
        # Create proof state with implication hypothesis
        proof_state = ProofState(
            theorem_name="test",
            current_goal="q",
            hypotheses=[Hypothesis(name="h", type_expr="p → q")]
        )
        
        # Execute apply
        tactic = Tactic(
            tactic_type=TacticType.APPLY,
            arguments=["h"]
        )
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Verify new goal
        self.assertEqual(new_state.current_goal, "p")
        self.assertFalse(new_state.is_complete)
    
    def test_mock_unsupported_tactic(self):
        """Test mock executor with unsupported tactic."""
        executor = MockTacticExecutor()
        
        proof_state = ProofState(
            theorem_name="test",
            current_goal="p",
            hypotheses=[]
        )
        
        # Execute unsupported tactic
        tactic = Tactic(tactic_type=TacticType.RING)
        
        new_state = executor.execute_tactic(proof_state, tactic)
        
        # Should fail gracefully
        self.assertFalse(new_state.is_complete)
        self.assertEqual(new_state.current_goal, "p")  # Unchanged
        self.assertIn('last_error', new_state.metadata)


class TestLeanFileGeneration(unittest.TestCase):
    """Test Lean file generation for tactic execution."""
    
    @patch('subprocess.run')
    def test_generate_lean_file(self, mock_run):
        """Test generation of Lean file content."""
        # Mock Lean verification
        mock_verify = MagicMock()
        mock_verify.returncode = 0
        mock_verify.stdout = "Lean (version 4.0.0)"
        mock_run.return_value = mock_verify
        
        executor = TacticExecutor()
        
        # Create proof state
        proof_state = ProofState(
            theorem_name="my_theorem",
            current_goal="p → q",
            hypotheses=[Hypothesis(name="h1", type_expr="r")]
        )
        
        # Create tactic
        tactic = Tactic(
            tactic_type=TacticType.INTRO,
            arguments=["h"]
        )
        
        # Generate Lean file content
        content = executor._generate_lean_file(proof_state, tactic)
        
        # Verify content
        self.assertIn("theorem my_theorem", content)
        self.assertIn("(h1 : r)", content)
        self.assertIn(": p → q := by", content)
        self.assertIn("intro h", content)
        self.assertIn("trace_state", content)
        self.assertIn("sorry", content)


if __name__ == '__main__':
    unittest.main()