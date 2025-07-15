"""
Real Lean 4 tactic executor for theorem proving.

This module provides the actual integration with Lean 4, executing tactics
and parsing the proof states from Lean's output.
"""

import subprocess
import tempfile
import logging
import json
import re
from pathlib import Path
from typing import Optional, Tuple

from tier2.linguistics.lean_ast import ProofState, Tactic, Hypothesis, TacticType


logger = logging.getLogger(__name__)


class LeanExecutor:
    """
    Executes Lean 4 tactics against proof states.
    
    This class provides real integration with Lean 4, using the
    interactive mode to execute tactics and retrieve proof states.
    """
    
    def __init__(self, lean_path: Optional[str] = None, timeout: Optional[int] = None, config=None):
        """
        Initialize the Lean executor.
        
        Args:
            lean_path: Path to the Lean executable. If None, uses 'lean' from PATH.
            timeout: Maximum time in seconds to wait for tactic execution. If None, uses config value.
            config: Configuration object. If None, uses DEFAULT_CONFIG.
        """
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        timeout = timeout if timeout is not None else config.lean_executor_timeout
        # Validate and sanitize lean_path
        if lean_path:
            # Ensure it's a valid path without shell metacharacters
            if any(char in lean_path for char in [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']):
                raise ValueError(f"Invalid characters in lean_path: {lean_path}")
            
            # Convert to Path and resolve
            lean_path_obj = Path(lean_path).resolve()
            
            # Check if it's an absolute path to an existing file
            if lean_path_obj.exists() and not lean_path_obj.is_file():
                raise ValueError(f"lean_path must point to a file, not a directory: {lean_path}")
                
            self.lean_path = str(lean_path_obj)
        else:
            # Use 'lean' from PATH - this is safe as it relies on PATH resolution
            self.lean_path = "lean"
        
        # Validate timeout
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(f"timeout must be a positive number, got: {timeout}")
        
        self.timeout = min(int(timeout), 300)  # Cap at 5 minutes for safety
        self.verify_lean_installation()
        
    def verify_lean_installation(self):
        """Verify that Lean 4 is installed and accessible."""
        try:
            result = subprocess.run(
                [self.lean_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Lean executable not found or not working: {self.lean_path}"
                )
            version_info = result.stdout.strip()
            if "Lean (version 4" not in version_info:
                raise RuntimeError(
                    f"Lean 4 is required, but found: {version_info}"
                )
            logger.info(f"Using {version_info}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to verify Lean installation: {e}")
    
    def execute_tactic(self, proof_state: ProofState, tactic: Tactic) -> ProofState:
        """
        Execute a tactic against a proof state using real Lean 4.
        
        Args:
            proof_state: The current proof state
            tactic: The tactic to execute
            
        Returns:
            The new proof state after tactic execution
        """
        # Generate Lean 4 file content
        lean_content = self._generate_lean4_file(proof_state, tactic)
        
        # Execute Lean and capture output
        output, error, returncode = self._run_lean4(lean_content)
        
        # Parse the output to extract new proof state
        new_state = self._parse_lean4_output(
            output, error, returncode, proof_state, tactic
        )
        
        return new_state
    
    def _generate_lean4_file(self, proof_state: ProofState, tactic: Tactic) -> str:
        """
        Generate a Lean 4 file for tactic execution.
        
        Uses the #print tactic state and other Lean 4 features.
        """
        lines = []
        
        # Add any necessary imports for basic tactics
        lines.append("-- Auto-generated Lean 4 proof")
        lines.append("")
        
        # Build the theorem declaration
        theorem_name = proof_state.theorem_name or "test_theorem"
        
        # Format hypotheses
        if proof_state.hypotheses:
            hyp_parts = []
            for hyp in proof_state.hypotheses:
                hyp_parts.append(f"({hyp.name} : {hyp.type_expr})")
            hyp_str = " ".join(hyp_parts) + " "
        else:
            hyp_str = ""
        
        # Start the theorem
        lines.append(f"theorem {theorem_name} {hyp_str}: {proof_state.current_goal} := by")
        
        # Add previously applied tactics
        for prev_tactic in proof_state.applied_tactics:
            lines.append(f"  {self._format_tactic(prev_tactic)}")
        
        # Add the new tactic
        tactic_str = self._format_tactic(tactic)
        lines.append(f"  {tactic_str}")
        
        # Add a checkpoint to capture the state after the tactic
        lines.append("  -- CHECKPOINT: Tactic applied")
        
        # Try to complete the proof or leave it incomplete
        lines.append("  sorry")
        
        # Add a check to see if goals were completed before sorry
        lines.append("")
        lines.append("#check " + theorem_name)
        
        return "\n".join(lines)
    
    def _format_tactic(self, tactic: Tactic) -> str:
        """Format a tactic for Lean 4 execution."""
        if tactic.tactic_type == TacticType.CUSTOM:
            return tactic.metadata.get('raw_line', 'skip')
        
        # Map our tactic types to Lean 4 syntax
        tactic_mapping = {
            TacticType.INTRO: "intro",
            TacticType.EXACT: "exact",
            TacticType.APPLY: "apply",
            TacticType.CONSTRUCTOR: "constructor",
            TacticType.CASES: "cases",
            TacticType.SIMP: "simp",
            TacticType.ASSUMPTION: "assumption",
        }
        
        tactic_name = tactic_mapping.get(tactic.tactic_type, tactic.tactic_type.value)
        
        if tactic.arguments:
            return f"{tactic_name} {' '.join(tactic.arguments)}"
        else:
            return tactic_name
    
    def _run_lean4(self, lean_content: str) -> Tuple[str, str, int]:
        """Run Lean 4 on the generated content."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.lean',
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(lean_content)
            temp_file.flush()
            
            try:
                # Run Lean 4 with JSON output for better parsing
                result = subprocess.run(
                    [self.lean_path, "--json", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                return result.stdout, result.stderr, result.returncode
                
            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    f"Lean execution timed out after {self.timeout} seconds"
                )
            except subprocess.SubprocessError as e:
                raise RuntimeError(f"Failed to run Lean: {e}")
            finally:
                temp_path.unlink(missing_ok=True)
    
    def _parse_lean4_output(
        self, 
        stdout: str, 
        stderr: str, 
        returncode: int,
        original_state: ProofState, 
        tactic: Tactic
    ) -> ProofState:
        """
        Parse Lean 4 output to extract the new proof state.
        
        Lean 4 with --json outputs structured data we can parse.
        """
        # Parse the goal state from error messages if present
        # Lean 4 often reports the current goal state in error messages
        new_hypotheses = list(original_state.hypotheses)
        new_goal = original_state.current_goal
        new_remaining = list(original_state.remaining_goals)
        
        # Look for goal state in output
        goal_state_pattern = re.compile(r'⊢\s+(.+)')
        hypothesis_pattern = re.compile(r'^(\w+)\s*:\s*(.+)$', re.MULTILINE)
        
        # Extract error message and goal state
        error_msg = None
        for line in stdout.split('\n'):
            if line.strip():
                try:
                    msg = json.loads(line)
                    if msg.get('severity') == 'error':
                        error_text = msg.get('data', '')
                        if 'tactic' in error_text and 'failed' in error_text:
                            error_msg = error_text
                            # Extract goal state from error
                            if '⊢' in error_text:
                                # Parse hypotheses
                                new_hypotheses = []
                                for match in hypothesis_pattern.finditer(error_text):
                                    name, type_expr = match.groups()
                                    if name != 'Prop':  # Skip type declarations
                                        new_hypotheses.append(
                                            Hypothesis(name=name, type_expr=type_expr)
                                        )
                                
                                # Parse goal
                                goal_match = goal_state_pattern.search(error_text)
                                if goal_match:
                                    new_goal = goal_match.group(1).strip()
                except json.JSONDecodeError:
                    pass
        
        # If we have an error, return updated state with error
        if error_msg:
            return ProofState(
                theorem_name=original_state.theorem_name,
                hypotheses=new_hypotheses,
                current_goal=new_goal,
                remaining_goals=new_remaining,
                is_complete=False,
                applied_tactics=original_state.applied_tactics + [tactic],
                metadata={
                    **original_state.metadata,
                    'last_error': error_msg,
                    'error_tactic': self._format_tactic(tactic)
                }
            )
        
        # Check if returncode indicates success
        if returncode == 0:
            # The tactic succeeded
            # For intro tactic, update hypotheses
            if tactic.tactic_type == TacticType.INTRO and tactic.arguments:
                # After intro, we should have a new hypothesis
                hyp_name = tactic.arguments[0]
                # Try to determine the type from the original goal
                if '→' in original_state.current_goal or '->' in original_state.current_goal:
                    parts = re.split(r'→|->', original_state.current_goal, 1)
                    if len(parts) == 2:
                        hyp_type = parts[0].strip()
                        new_goal = parts[1].strip()
                        new_hypotheses.append(Hypothesis(name=hyp_name, type_expr=hyp_type))
            
            return ProofState(
                theorem_name=original_state.theorem_name,
                hypotheses=new_hypotheses,
                current_goal=new_goal,
                remaining_goals=new_remaining,
                is_complete=False,
                applied_tactics=original_state.applied_tactics + [tactic]
            )
        
        # Default case - return with error
        return ProofState(
            theorem_name=original_state.theorem_name,
            hypotheses=original_state.hypotheses,
            current_goal=original_state.current_goal,
            remaining_goals=original_state.remaining_goals,
            is_complete=False,
            applied_tactics=original_state.applied_tactics + [tactic],
            metadata={
                **original_state.metadata,
                'last_error': 'Unknown error',
                'lean_output': stdout[:500]
            }
        )
    
    def _extract_error_message(self, stdout: str, stderr: str) -> str:
        """Extract error message from Lean output."""
        # Try to parse JSON messages
        error_messages = []
        
        for line in stdout.split('\n'):
            if line.strip():
                try:
                    msg = json.loads(line)
                    if msg.get('severity') == 'error':
                        error_messages.append(msg.get('data', 'Unknown error'))
                except json.JSONDecodeError:
                    # Not JSON, might be plain text error
                    if 'error' in line.lower():
                        error_messages.append(line)
        
        # Also check stderr
        if stderr:
            error_messages.append(stderr)
        
        return ' | '.join(error_messages) if error_messages else "Unknown error"


class LeanMockExecutor:
    """
    Enhanced mock executor that mimics Lean 4 behavior more closely.
    
    This is used when we want to test without requiring Lean installation.
    """
    
    def __init__(self, config=None):
        """Initialize the mock executor."""
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        self.lean_path = "mock_lean"
        self.timeout = config.lean_executor_timeout
        
    def execute_tactic(self, proof_state: ProofState, tactic: Tactic) -> ProofState:
        """Execute a tactic using mock logic that mimics Lean 4."""
        # Import the MockTacticExecutor logic
        from .tactic_executor import MockTacticExecutor
        
        mock = MockTacticExecutor()
        return mock.execute_tactic(proof_state, tactic)