"""
Tactic executor for interacting with the Lean theorem prover.

This module provides the critical bridge between RegionAI's abstract
reasoning and the external Lean theorem prover, executing tactics
and returning new proof states.
"""

import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple
import re

from tier2.linguistics.lean_ast import ProofState, Tactic, Hypothesis, TacticType


logger = logging.getLogger(__name__)


class TacticExecutionError(Exception):
    """Raised when tactic execution fails."""


class LeanNotFoundError(Exception):
    """Raised when Lean executable is not found."""


class TacticExecutor:
    """
    Executes Lean tactics against proof states.
    
    This class interacts with the Lean command-line tool to execute
    tactics and parse the resulting proof states. It handles the
    generation of temporary Lean files, subprocess management, and
    output parsing.
    """
    
    def __init__(self, lean_path: Optional[str] = None, timeout: Optional[int] = None, config=None):
        """
        Initialize the tactic executor.
        
        Args:
            lean_path: Path to the Lean executable. If None, uses 'lean' from PATH.
            timeout: Maximum time in seconds to wait for tactic execution. If None, uses config value.
            config: Configuration object. If None, uses DEFAULT_CONFIG.
        """
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        self.lean_path = lean_path or "lean"
        self.timeout = timeout if timeout is not None else config.tactic_executor_timeout
        
        # Verify Lean is available
        self._verify_lean_installation()
        
        # Patterns for parsing Lean output
        self.goal_pattern = re.compile(r'⊢\s+(.+)')
        self.hypothesis_pattern = re.compile(r'(\w+)\s*:\s*(.+)')
        self.error_pattern = re.compile(r'error:\s*(.+)', re.IGNORECASE)
        self.goals_accomplished_pattern = re.compile(r'goals accomplished', re.IGNORECASE)
        
    def _verify_lean_installation(self):
        """Verify that Lean is installed and accessible."""
        try:
            result = subprocess.run(
                [self.lean_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise LeanNotFoundError(
                    f"Lean executable not found or not working: {self.lean_path}"
                )
            logger.info(f"Lean version: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise LeanNotFoundError(
                f"Failed to verify Lean installation: {e}"
            )
    
    def execute_tactic(self, proof_state: ProofState, tactic: Tactic) -> ProofState:
        """
        Execute a tactic against a proof state.
        
        Args:
            proof_state: The current proof state
            tactic: The tactic to execute
            
        Returns:
            The new proof state after tactic execution
            
        Raises:
            TacticExecutionError: If the tactic execution fails
        """
        # Generate Lean file content
        lean_content = self._generate_lean_file(proof_state, tactic)
        
        # Execute Lean and capture output
        output, error = self._run_lean(lean_content)
        
        # Parse the output to extract new proof state
        new_state = self._parse_lean_output(output, error, proof_state, tactic)
        
        return new_state
    
    def _generate_lean_file(self, proof_state: ProofState, tactic: Tactic) -> str:
        """
        Generate a temporary Lean file for tactic execution.
        
        Args:
            proof_state: The current proof state
            tactic: The tactic to execute
            
        Returns:
            The Lean file content as a string
        """
        lines = []
        
        # Add theorem declaration with hypotheses
        theorem_name = proof_state.theorem_name or "test_theorem"
        
        # Build hypothesis list
        hyp_strs = []
        for hyp in proof_state.hypotheses:
            hyp_strs.append(f"{hyp.name} : {hyp.type_expr}")
        
        hyp_str = " ".join(f"({h})" for h in hyp_strs) if hyp_strs else ""
        
        lines.append(f"theorem {theorem_name} {hyp_str} : {proof_state.current_goal} := by")
        
        # Add the tactic
        tactic_str = self._format_tactic(tactic)
        lines.append(f"  {tactic_str}")
        
        # Add a command to print the proof state
        lines.append("  trace_state")
        
        # Add sorry to prevent errors if proof is incomplete
        lines.append("  sorry")
        
        return "\n".join(lines)
    
    def _format_tactic(self, tactic: Tactic) -> str:
        """
        Format a tactic for Lean execution.
        
        Args:
            tactic: The tactic to format
            
        Returns:
            The formatted tactic string
        """
        if tactic.tactic_type == TacticType.CUSTOM:
            # For custom tactics, use the raw representation
            return tactic.metadata.get('raw_line', 'skip')
        
        # Format based on tactic type
        tactic_name = tactic.tactic_type.value
        
        if tactic.arguments:
            return f"{tactic_name} {' '.join(tactic.arguments)}"
        else:
            return tactic_name
    
    def _run_lean(self, lean_content: str) -> Tuple[str, str]:
        """
        Run Lean on the generated content.
        
        Args:
            lean_content: The Lean file content
            
        Returns:
            Tuple of (stdout, stderr)
            
        Raises:
            TacticExecutionError: If Lean execution fails
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.lean',
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(lean_content)
            temp_file.flush()
            
            try:
                # Run Lean
                result = subprocess.run(
                    [self.lean_path, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                logger.debug(f"Lean stdout: {result.stdout}")
                logger.debug(f"Lean stderr: {result.stderr}")
                
                return result.stdout, result.stderr
                
            except subprocess.TimeoutExpired:
                raise TacticExecutionError(
                    f"Tactic execution timed out after {self.timeout} seconds"
                )
            except subprocess.SubprocessError as e:
                raise TacticExecutionError(f"Failed to run Lean: {e}")
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)
    
    def _parse_lean_output(
        self,
        stdout: str,
        stderr: str,
        original_state: ProofState,
        tactic: Tactic
    ) -> ProofState:
        """
        Parse Lean output to extract the new proof state.
        
        Args:
            stdout: Lean standard output
            stderr: Lean standard error
            original_state: The original proof state
            tactic: The executed tactic
            
        Returns:
            The new proof state
        """
        # Check for errors
        error_match = self.error_pattern.search(stderr) or self.error_pattern.search(stdout)
        if error_match:
            error_msg = error_match.group(1)
            logger.warning(f"Tactic error: {error_msg}")
            # Return state with error flag
            return ProofState(
                theorem_name=original_state.theorem_name,
                hypotheses=original_state.hypotheses,
                current_goal=original_state.current_goal,
                remaining_goals=original_state.remaining_goals,
                is_complete=False,
                applied_tactics=original_state.applied_tactics + [tactic],
                metadata={
                    **original_state.metadata,
                    'last_error': error_msg,
                    'error_tactic': self._format_tactic(tactic)
                }
            )
        
        # Check if goals are accomplished
        if self.goals_accomplished_pattern.search(stdout):
            logger.info("Goals accomplished!")
            return ProofState(
                theorem_name=original_state.theorem_name,
                hypotheses=original_state.hypotheses,
                current_goal="",  # No current goal
                remaining_goals=[],
                is_complete=True,
                applied_tactics=original_state.applied_tactics + [tactic]
            )
        
        # Parse new goal state
        # This is a simplified parser - a real implementation would need
        # to handle Lean's full output format
        new_hypotheses = list(original_state.hypotheses)
        new_goal = original_state.current_goal
        
        # Look for new hypotheses (e.g., from intro)
        for line in stdout.split('\n'):
            hyp_match = self.hypothesis_pattern.match(line.strip())
            if hyp_match:
                name = hyp_match.group(1)
                type_expr = hyp_match.group(2)
                # Check if this is a new hypothesis
                if not any(h.name == name for h in new_hypotheses):
                    new_hypotheses.append(Hypothesis(name=name, type_expr=type_expr))
        
        # Look for new goal
        for line in stdout.split('\n'):
            goal_match = self.goal_pattern.search(line)
            if goal_match:
                new_goal = goal_match.group(1).strip()
                break
        
        # Create new proof state
        return ProofState(
            theorem_name=original_state.theorem_name,
            hypotheses=new_hypotheses,
            current_goal=new_goal,
            remaining_goals=original_state.remaining_goals,
            is_complete=False,
            applied_tactics=original_state.applied_tactics + [tactic]
        )


def _normalize_expr(expr: str) -> str:
    """Normalize an expression for comparison."""
    expr = ' '.join(expr.split())
    expr = expr.replace('->', '→')
    expr = expr.replace('<->', '↔')
    return expr.strip()


class MockTacticExecutor(TacticExecutor):
    """
    Mock tactic executor for testing without Lean installation.
    
    This executor simulates Lean's behavior for common tactics,
    useful for unit testing and development.
    """
    
    def __init__(self, config=None):
        """Initialize the mock executor."""
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        # Don't call parent __init__ to avoid Lean verification
        self.lean_path = "mock_lean"
        self.timeout = config.tactic_executor_timeout
        
    def execute_tactic(self, proof_state: ProofState, tactic: Tactic) -> ProofState:
        """
        Execute a tactic using mock logic.
        
        Args:
            proof_state: The current proof state
            tactic: The tactic to execute
            
        Returns:
            The new proof state based on mock rules
        """
        tactic_type = tactic.tactic_type
        
        if tactic_type == TacticType.INTRO:
            # intro on implication: p → q becomes hypothesis p, goal q
            if '→' in proof_state.current_goal or '->' in proof_state.current_goal:
                parts = re.split(r'→|->',  proof_state.current_goal, 1)
                if len(parts) == 2:
                    hyp_type = parts[0].strip()
                    new_goal = parts[1].strip()
                    hyp_name = tactic.arguments[0] if tactic.arguments else 'h'
                    
                    new_hypotheses = list(proof_state.hypotheses)
                    new_hypotheses.append(Hypothesis(name=hyp_name, type_expr=hyp_type))
                    
                    return ProofState(
                        theorem_name=proof_state.theorem_name,
                        hypotheses=new_hypotheses,
                        current_goal=new_goal,
                        remaining_goals=proof_state.remaining_goals,
                        is_complete=False,
                        applied_tactics=proof_state.applied_tactics + [tactic]
                    )
        
        elif tactic_type == TacticType.EXACT:
            # exact h: if hypothesis h matches goal, proof is complete
            if tactic.arguments:
                hyp_name = tactic.arguments[0]
                for hyp in proof_state.hypotheses:
                    if hyp.name == hyp_name and hyp.type_expr == proof_state.current_goal:
                        return ProofState(
                            theorem_name=proof_state.theorem_name,
                            hypotheses=proof_state.hypotheses,
                            current_goal="",
                            remaining_goals=[],
                            is_complete=True,
                            applied_tactics=proof_state.applied_tactics + [tactic]
                        )
        
        elif tactic_type == TacticType.APPLY:
            # apply h: if h is A → B and goal is B, new goal is A
            if tactic.arguments:
                hyp_name = tactic.arguments[0]
                for hyp in proof_state.hypotheses:
                    if hyp.name == hyp_name:
                        # Check if hypothesis is an implication
                        if '→' in hyp.type_expr or '->' in hyp.type_expr:
                            parts = re.split(r'→|->',  hyp.type_expr, 1)
                            if len(parts) == 2:
                                premise = parts[0].strip()
                                conclusion = parts[1].strip()
                                if conclusion == proof_state.current_goal:
                                    return ProofState(
                                        theorem_name=proof_state.theorem_name,
                                        hypotheses=proof_state.hypotheses,
                                        current_goal=premise,
                                        remaining_goals=proof_state.remaining_goals,
                                        is_complete=False,
                                        applied_tactics=proof_state.applied_tactics + [tactic]
                                    )
        
        elif tactic_type == TacticType.CONSTRUCTOR:
            # constructor: split conjunction goals
            if '∧' in proof_state.current_goal or '/\\' in proof_state.current_goal:
                parts = re.split(r'∧|/\\', proof_state.current_goal, 1)
                if len(parts) == 2:
                    left_goal = parts[0].strip()
                    right_goal = parts[1].strip()
                    
                    return ProofState(
                        theorem_name=proof_state.theorem_name,
                        hypotheses=proof_state.hypotheses,
                        current_goal=left_goal,
                        remaining_goals=[right_goal] + proof_state.remaining_goals,
                        is_complete=False,
                        applied_tactics=proof_state.applied_tactics + [tactic]
                    )
        
        elif tactic_type == TacticType.CASES:
            # cases h: case analysis on disjunction hypothesis
            if tactic.arguments:
                hyp_name = tactic.arguments[0]
                for hyp in proof_state.hypotheses:
                    if hyp.name == hyp_name:
                        if '∨' in hyp.type_expr or '\\/' in hyp.type_expr:
                            parts = re.split(r'∨|\\/', hyp.type_expr, 1)
                            if len(parts) == 2:
                                # Create two subgoals, one for each case
                                # This is simplified - real cases would create different contexts
                                return ProofState(
                                    theorem_name=proof_state.theorem_name,
                                    hypotheses=proof_state.hypotheses,
                                    current_goal=proof_state.current_goal,
                                    remaining_goals=[proof_state.current_goal] + proof_state.remaining_goals,
                                    is_complete=False,
                                    applied_tactics=proof_state.applied_tactics + [tactic],
                                    metadata={
                                        **proof_state.metadata,
                                        'cases_on': hyp_name
                                    }
                                )
        
        elif tactic_type == TacticType.ASSUMPTION:
            # assumption: search all hypotheses for exact match
            for hyp in proof_state.hypotheses:
                if hyp.type_expr == proof_state.current_goal:
                    return ProofState(
                        theorem_name=proof_state.theorem_name,
                        hypotheses=proof_state.hypotheses,
                        current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                        remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                        is_complete=len(proof_state.remaining_goals) == 0,
                        applied_tactics=proof_state.applied_tactics + [tactic]
                    )
        
        elif tactic_type == TacticType.SIMP:
            # simp: simplify expressions
            goal = proof_state.current_goal
            
            # Simplification rules
            simplifications = [
                (r'(.+)\s*∧\s*True', r'\1'),  # p ∧ True → p
                (r'True\s*∧\s*(.+)', r'\1'),  # True ∧ p → p
                (r'(.+)\s*∨\s*False', r'\1'), # p ∨ False → p
                (r'False\s*∨\s*(.+)', r'\1'), # False ∨ p → p
                (r'¬¬(.+)', r'\1'),           # ¬¬p → p (classical)
            ]
            
            new_goal = goal
            for pattern, replacement in simplifications:
                new_goal = re.sub(pattern, replacement, new_goal)
            
            if new_goal != goal:
                return ProofState(
                    theorem_name=proof_state.theorem_name,
                    hypotheses=proof_state.hypotheses,
                    current_goal=new_goal.strip(),
                    remaining_goals=proof_state.remaining_goals,
                    is_complete=False,
                    applied_tactics=proof_state.applied_tactics + [tactic]
                )
        
        elif tactic_type == TacticType.CUSTOM:
            # Handle custom tactics
            raw_line = tactic.metadata.get('raw_line', '')
            
            if raw_line == 'left':
                # left: choose left side of disjunction
                if '∨' in proof_state.current_goal or '\\/' in proof_state.current_goal:
                    parts = re.split(r'∨|\\/', proof_state.current_goal, 1)
                    if len(parts) == 2:
                        return ProofState(
                            theorem_name=proof_state.theorem_name,
                            hypotheses=proof_state.hypotheses,
                            current_goal=parts[0].strip(),
                            remaining_goals=proof_state.remaining_goals,
                            is_complete=False,
                            applied_tactics=proof_state.applied_tactics + [tactic]
                        )
            
            elif raw_line == 'right':
                # right: choose right side of disjunction
                if '∨' in proof_state.current_goal or '\\/' in proof_state.current_goal:
                    parts = re.split(r'∨|\\/', proof_state.current_goal, 1)
                    if len(parts) == 2:
                        return ProofState(
                            theorem_name=proof_state.theorem_name,
                            hypotheses=proof_state.hypotheses,
                            current_goal=parts[1].strip(),
                            remaining_goals=proof_state.remaining_goals,
                            is_complete=False,
                            applied_tactics=proof_state.applied_tactics + [tactic]
                        )
            
            elif raw_line == 'trivial':
                # trivial: solve True goal
                if proof_state.current_goal.strip() == 'True':
                    return ProofState(
                        theorem_name=proof_state.theorem_name,
                        hypotheses=proof_state.hypotheses,
                        current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                        remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                        is_complete=len(proof_state.remaining_goals) == 0,
                        applied_tactics=proof_state.applied_tactics + [tactic]
                    )
            
            elif raw_line.startswith('exact '):
                # Handle exact with specific hypothesis projections
                parts = raw_line.split(' ', 1)
                if len(parts) > 1:
                    expr = parts[1]
                    
                    # Handle conjunction projections like h.1 or h.2
                    if '.' in expr:
                        hyp_name, proj = expr.split('.', 1)
                        for hyp in proof_state.hypotheses:
                            if hyp.name == hyp_name:
                                if '∧' in hyp.type_expr or '/\\' in hyp.type_expr:
                                    conj_parts = re.split(r'∧|/\\', hyp.type_expr, 1)
                                    if len(conj_parts) == 2:
                                        if proj == '1' and _normalize_expr(conj_parts[0]) == _normalize_expr(proof_state.current_goal):
                                            return ProofState(
                                                theorem_name=proof_state.theorem_name,
                                                hypotheses=proof_state.hypotheses,
                                                current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                                remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                                is_complete=len(proof_state.remaining_goals) == 0,
                                                applied_tactics=proof_state.applied_tactics + [tactic]
                                            )
                                        elif proj == '2' and _normalize_expr(conj_parts[1]) == _normalize_expr(proof_state.current_goal):
                                            return ProofState(
                                                theorem_name=proof_state.theorem_name,
                                                hypotheses=proof_state.hypotheses,
                                                current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                                remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                                is_complete=len(proof_state.remaining_goals) == 0,
                                                applied_tactics=proof_state.applied_tactics + [tactic]
                                            )
                    
                    # Handle modus ponens: exact impl_hyp prem_hyp
                    elif ' ' in expr:
                        tokens = expr.split()
                        if len(tokens) == 2:
                            impl_name, prem_name = tokens
                            impl_hyp = None
                            prem_hyp = None
                            
                            for hyp in proof_state.hypotheses:
                                if hyp.name == impl_name:
                                    impl_hyp = hyp
                                elif hyp.name == prem_name:
                                    prem_hyp = hyp
                            
                            if impl_hyp and prem_hyp and ('→' in impl_hyp.type_expr or '->' in impl_hyp.type_expr):
                                parts = re.split(r'→|->', impl_hyp.type_expr, 1)
                                if len(parts) == 2:
                                    premise = _normalize_expr(parts[0])
                                    conclusion = _normalize_expr(parts[1])
                                    
                                    if (_normalize_expr(prem_hyp.type_expr) == premise and 
                                        conclusion == _normalize_expr(proof_state.current_goal)):
                                        return ProofState(
                                            theorem_name=proof_state.theorem_name,
                                            hypotheses=proof_state.hypotheses,
                                            current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                            remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                            is_complete=len(proof_state.remaining_goals) == 0,
                                            applied_tactics=proof_state.applied_tactics + [tactic]
                                        )
            
            elif raw_line == 'apply Iff.intro':
                # Iff.intro: split p ↔ q into p → q and q → p
                if '↔' in proof_state.current_goal or '<->' in proof_state.current_goal:
                    parts = re.split(r'↔|<->', proof_state.current_goal, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        
                        return ProofState(
                            theorem_name=proof_state.theorem_name,
                            hypotheses=proof_state.hypotheses,
                            current_goal=f"{left} → {right}",
                            remaining_goals=[f"{right} → {left}"] + proof_state.remaining_goals,
                            is_complete=False,
                            applied_tactics=proof_state.applied_tactics + [tactic]
                        )
            
            elif raw_line == 'rw [and_comm]':
                # Rewrite conjunction commutativity
                goal = proof_state.current_goal
                if '=' in goal:
                    eq_parts = goal.split('=', 1)
                    if len(eq_parts) == 2:
                        left = eq_parts[0].strip()
                        right = eq_parts[1].strip()
                        
                        # Check if it's a conjunction commutativity pattern
                        and_l = re.match(r'(.+)\s*∧\s*(.+)', left)
                        and_r = re.match(r'(.+)\s*∧\s*(.+)', right)
                        
                        if and_l and and_r:
                            l1, l2 = and_l.groups()
                            r1, r2 = and_r.groups()
                            
                            if (_normalize_expr(l1) == _normalize_expr(r2) and 
                                _normalize_expr(l2) == _normalize_expr(r1)):
                                # Goal is proved by commutativity
                                return ProofState(
                                    theorem_name=proof_state.theorem_name,
                                    hypotheses=proof_state.hypotheses,
                                    current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                    remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                    is_complete=len(proof_state.remaining_goals) == 0,
                                    applied_tactics=proof_state.applied_tactics + [tactic]
                                )
            
            elif raw_line == 'rw [or_comm]':
                # Rewrite disjunction commutativity
                goal = proof_state.current_goal
                if '=' in goal:
                    eq_parts = goal.split('=', 1)
                    if len(eq_parts) == 2:
                        left = eq_parts[0].strip()
                        right = eq_parts[1].strip()
                        
                        # Check if it's a disjunction commutativity pattern
                        or_l = re.match(r'(.+)\s*∨\s*(.+)', left)
                        or_r = re.match(r'(.+)\s*∨\s*(.+)', right)
                        
                        if or_l and or_r:
                            l1, l2 = or_l.groups()
                            r1, r2 = or_r.groups()
                            
                            if (_normalize_expr(l1) == _normalize_expr(r2) and 
                                _normalize_expr(l2) == _normalize_expr(r1)):
                                # Goal is proved by commutativity
                                return ProofState(
                                    theorem_name=proof_state.theorem_name,
                                    hypotheses=proof_state.hypotheses,
                                    current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                    remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                    is_complete=len(proof_state.remaining_goals) == 0,
                                    applied_tactics=proof_state.applied_tactics + [tactic]
                                )
            
            elif raw_line == 'rfl':
                # Reflexivity for equality
                if '=' in proof_state.current_goal:
                    parts = proof_state.current_goal.split('=', 1)
                    if len(parts) == 2:
                        left = _normalize_expr(parts[0])
                        right = _normalize_expr(parts[1])
                        
                        if left == right:
                            return ProofState(
                                theorem_name=proof_state.theorem_name,
                                hypotheses=proof_state.hypotheses,
                                current_goal=proof_state.remaining_goals[0] if proof_state.remaining_goals else "",
                                remaining_goals=proof_state.remaining_goals[1:] if proof_state.remaining_goals else [],
                                is_complete=len(proof_state.remaining_goals) == 0,
                                applied_tactics=proof_state.applied_tactics + [tactic]
                            )
            
            elif raw_line == 'tauto':
                # Tautology prover for simple logical tautologies
                # Handle impl_as_disj: (p → q) → (¬p ∨ q)
                impl_disj_pattern = re.match(r'\((.+)\s*→\s*(.+)\)\s*→\s*\(¬(.+)\s*∨\s*(.+)\)', proof_state.current_goal)
                if impl_disj_pattern:
                    p1, q1, p2, q2 = impl_disj_pattern.groups()
                    if _normalize_expr(p1) == _normalize_expr(p2) and _normalize_expr(q1) == _normalize_expr(q2):
                        # This is a tautology, mark as complete
                        return ProofState(
                            theorem_name=proof_state.theorem_name,
                            hypotheses=proof_state.hypotheses,
                            current_goal="",
                            remaining_goals=[],
                            is_complete=True,
                            applied_tactics=proof_state.applied_tactics + [tactic]
                        )
                        
            elif raw_line.startswith('by_cases'):
                # Case analysis: by_cases h : p creates two subgoals
                # One with h : p, another with h : ¬p
                parts = raw_line.split(':', 1)
                if len(parts) > 1:
                    prop = parts[1].strip()
                    
                    # Create two subgoals with different hypotheses
                    return ProofState(
                        theorem_name=proof_state.theorem_name,
                        hypotheses=proof_state.hypotheses + [Hypothesis(name='h', type_expr=prop)],
                        current_goal=proof_state.current_goal,
                        remaining_goals=[proof_state.current_goal] + proof_state.remaining_goals,
                        is_complete=False,
                        applied_tactics=proof_state.applied_tactics + [tactic],
                        metadata={
                            **proof_state.metadata,
                            'second_case_hyp': f'¬{prop}'  # The second subgoal will have ¬p
                        }
                    )
        
        # If tactic doesn't apply or fails, return state with error
        return ProofState(
            theorem_name=proof_state.theorem_name,
            hypotheses=proof_state.hypotheses,
            current_goal=proof_state.current_goal,
            remaining_goals=proof_state.remaining_goals,
            is_complete=False,
            applied_tactics=proof_state.applied_tactics + [tactic],
            metadata={
                **proof_state.metadata,
                'last_error': f"Tactic {tactic_type.value} failed",
                'error_tactic': str(tactic)
            }
        )