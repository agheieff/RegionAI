"""
Proof runner with exponential growth detection and safety guards.

This module manages individual proof attempts with multiple safety
mechanisms to prevent exponential search space blow-ups and ensure
system stability during mathematical reasoning.
"""

import time
import math
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

from ..config import RegionAIConfig, DEFAULT_CONFIG
from ..knowledge.exceptions import ExponentialSearchException, ProofTimeoutException
from tier2.linguistics.lean_ast import ProofState, Tactic, Theorem
from .proof_trace import ProofTraceRecorder
from .tactic_executor import TacticExecutor


logger = logging.getLogger(__name__)


@dataclass
class ProofMetrics:
    """
    Metrics tracked during proof search.
    
    Used for progress detection and exponential growth identification.
    """
    steps_taken: int = 0
    start_time: float = field(default_factory=time.monotonic)
    goal_entropies: List[float] = field(default_factory=list)
    tactic_applications: List[Tactic] = field(default_factory=list)
    backtrack_count: int = 0
    failed_tactics: int = 0
    goals_created: int = 0
    goals_closed: int = 0
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return time.monotonic() - self.start_time
    
    def get_latest_entropy(self) -> Optional[float]:
        """Get the most recent entropy value."""
        return self.goal_entropies[-1] if self.goal_entropies else None
    
    def get_entropy_trend(self, window: int = 10) -> Optional[float]:
        """
        Calculate entropy trend over recent steps.
        
        Returns:
            Negative value if improving (decreasing entropy)
            Positive value if worsening (increasing entropy)
            None if insufficient data
        """
        if len(self.goal_entropies) < window + 1:
            return None
            
        recent = self.goal_entropies[-window:]
        # Simple linear regression slope
        n = len(recent)
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
            
        return numerator / denominator


class ProofRunner:
    """
    Manages a single proof attempt with safety guards.
    
    This class implements multiple safety mechanisms to prevent
    exponential search space blow-ups:
    
    1. Global time budget (Guard A)
    2. Progress oracle based on entropy (Guard C)
    3. Step count limits
    4. Backtracking detection
    
    The runner monitors proof progress and can abort early if
    exponential behavior is detected.
    """
    
    def __init__(self, 
                 config: Optional[RegionAIConfig] = None,
                 trace_recorder: Optional[ProofTraceRecorder] = None,
                 theorem: Optional[Theorem] = None,
                 tactic_executor: Optional[TacticExecutor] = None):
        """
        Initialize the proof runner.
        
        Args:
            config: Configuration object (uses DEFAULT_CONFIG if None)
            trace_recorder: Optional trace recorder for debugging
            theorem: The theorem being proved (for context)
            tactic_executor: Optional tactic executor for running Lean tactics
        """
        self.config = config or DEFAULT_CONFIG
        self.trace_recorder = trace_recorder
        self.theorem = theorem
        self.tactic_executor = tactic_executor
        self.metrics = ProofMetrics()
        
        # Safety parameters
        self.max_proof_sec = self.config.max_proof_sec
        self.progress_window = 50  # Steps to check for progress
        self.entropy_epsilon = 0.01  # Minimum entropy improvement
        self.max_steps = 10000  # Hard limit on proof steps
        self.max_backtrack_ratio = 0.5  # Max ratio of backtracks to steps
        
        # State tracking
        self.is_aborted = False
        self.abort_reason: Optional[str] = None
        self.current_heuristic: Optional[str] = None
        
        logger.info(f"ProofRunner initialized with {self.max_proof_sec}s timeout")
    
    def set_current_heuristic(self, heuristic_name: str) -> None:
        """
        Set the currently active heuristic.
        
        This is used to identify which heuristic was responsible
        when exponential behavior is detected.
        """
        self.current_heuristic = heuristic_name
    
    def check_abort(self) -> None:
        """
        Check if the proof attempt should be aborted.
        
        This method implements the safety guards and raises
        ExponentialSearchException if any guard is triggered.
        
        Raises:
            ExponentialSearchException: If exponential behavior detected
            ProofTimeoutException: If time budget exceeded
        """
        if self.is_aborted:
            return
            
        # Guard A: Global time budget
        elapsed = self.metrics.elapsed_seconds()
        if elapsed > self.max_proof_sec:
            self.is_aborted = True
            self.abort_reason = f"Time budget exceeded: {elapsed:.2f}s > {self.max_proof_sec}s"
            
            if self.trace_recorder:
                self.trace_recorder.record_timeout(self.max_proof_sec)
                
            raise ProofTimeoutException(
                self.abort_reason,
                timeout_limit=self.max_proof_sec,
                actual_time=elapsed
            )
        
        # Guard B: Step count limit
        if self.metrics.steps_taken > self.max_steps:
            self.is_aborted = True
            self.abort_reason = f"Step limit exceeded: {self.metrics.steps_taken} > {self.max_steps}"
            
            context = {
                'steps_taken': self.metrics.steps_taken,
                'elapsed_time': elapsed,
                'current_heuristic': self.current_heuristic
            }
            
            raise ExponentialSearchException(
                self.abort_reason,
                elapsed_time=elapsed,
                steps_taken=self.metrics.steps_taken,
                context=context
            )
        
        # Guard C: Progress oracle (entropy-based)
        if len(self.metrics.goal_entropies) >= self.progress_window:
            entropy_trend = self.metrics.get_entropy_trend(self.progress_window)
            
            if entropy_trend is not None and entropy_trend > -self.entropy_epsilon:
                # Not making sufficient progress
                self.is_aborted = True
                self.abort_reason = (
                    f"Insufficient progress: entropy trend {entropy_trend:.4f} "
                    f"(threshold: {-self.entropy_epsilon})"
                )
                
                context = {
                    'entropy_trend': entropy_trend,
                    'window_size': self.progress_window,
                    'recent_entropies': self.metrics.goal_entropies[-10:],
                    'current_heuristic': self.current_heuristic
                }
                
                raise ExponentialSearchException(
                    self.abort_reason,
                    elapsed_time=elapsed,
                    steps_taken=self.metrics.steps_taken,
                    context=context
                )
        
        # Guard D: Excessive backtracking
        if self.metrics.steps_taken > 100:  # Only check after some steps
            backtrack_ratio = self.metrics.backtrack_count / self.metrics.steps_taken
            if backtrack_ratio > self.max_backtrack_ratio:
                self.is_aborted = True
                self.abort_reason = (
                    f"Excessive backtracking: {backtrack_ratio:.2%} "
                    f"(threshold: {self.max_backtrack_ratio:.2%})"
                )
                
                context = {
                    'backtrack_count': self.metrics.backtrack_count,
                    'backtrack_ratio': backtrack_ratio,
                    'current_heuristic': self.current_heuristic
                }
                
                raise ExponentialSearchException(
                    self.abort_reason,
                    elapsed_time=elapsed,
                    steps_taken=self.metrics.steps_taken,
                    context=context
                )
    
    def execute_tactic(self, proof_state: ProofState, tactic: Tactic) -> ProofState:
        """
        Execute a tactic and return the new proof state.
        
        Args:
            proof_state: Current proof state
            tactic: Tactic to execute
            
        Returns:
            New proof state after tactic execution
            
        Raises:
            TacticExecutionError: If tactic execution fails
        """
        if not self.tactic_executor:
            raise RuntimeError("No tactic executor configured")
            
        # Execute the tactic
        new_state = self.tactic_executor.execute_tactic(proof_state, tactic)
        
        # Record the step
        success = not new_state.metadata.get('last_error')
        self.record_step(tactic, success)
        
        # Update goal state metrics
        self.update_goal_state(new_state)
        
        # Record in trace if available
        if self.trace_recorder:
            self.trace_recorder.record_tactic_application(
                tactic=tactic,
                before_state=proof_state,
                after_state=new_state,
                success=success
            )
        
        return new_state

    def record_step(self, tactic: Tactic, success: bool) -> None:
        """
        Record a proof step.
        
        Args:
            tactic: The tactic that was applied
            success: Whether the tactic succeeded
        """
        self.metrics.steps_taken += 1
        self.metrics.tactic_applications.append(tactic)
        
        if not success:
            self.metrics.failed_tactics += 1
            
        # Check safety after each step
        self.check_abort()
    
    def record_backtrack(self) -> None:
        """Record that backtracking occurred."""
        self.metrics.backtrack_count += 1
    
    def update_goal_state(self, proof_state: ProofState) -> None:
        """
        Update metrics based on current proof state.
        
        Args:
            proof_state: Current state of the proof
        """
        # Calculate Shannon entropy of goal state
        entropy = self._calculate_goal_entropy(proof_state)
        self.metrics.goal_entropies.append(entropy)
        
        # Track goal creation/closure
        current_goals = len(proof_state.goals)
        if len(self.metrics.goal_entropies) > 1:
            # Compare with previous state
            # This is simplified - in reality we'd track individual goal IDs
            if current_goals > self.metrics.goals_created - self.metrics.goals_closed:
                self.metrics.goals_created += current_goals - (self.metrics.goals_created - self.metrics.goals_closed)
            elif current_goals < self.metrics.goals_created - self.metrics.goals_closed:
                self.metrics.goals_closed += (self.metrics.goals_created - self.metrics.goals_closed) - current_goals
    
    def _calculate_goal_entropy(self, proof_state: ProofState) -> float:
        """
        Calculate Shannon entropy of the proof state.
        
        This is a simplified measure based on:
        - Number of goals
        - Goal complexity (length)
        - Hypothesis count
        
        Lower entropy indicates a simpler, more focused state.
        
        Args:
            proof_state: Current proof state
            
        Returns:
            Entropy value (lower is better)
        """
        if proof_state.completed:
            return 0.0
            
        # Base entropy from number of goals
        num_goals = len(proof_state.goals)
        if num_goals == 0:
            return 0.0
            
        goal_entropy = math.log(num_goals + 1)
        
        # Add complexity from goal lengths
        total_goal_length = sum(len(str(g)) for g in proof_state.goals)
        avg_goal_length = total_goal_length / num_goals
        complexity_entropy = math.log(avg_goal_length + 1) / 10
        
        # Factor in hypothesis count (more hypotheses = more choice = higher entropy)
        hyp_entropy = math.log(len(proof_state.hypotheses) + 1) / 20
        
        return goal_entropy + complexity_entropy + hyp_entropy
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the proof attempt.
        
        Returns:
            Dictionary with metrics and status
        """
        return {
            'completed': not self.is_aborted,
            'abort_reason': self.abort_reason,
            'elapsed_seconds': self.metrics.elapsed_seconds(),
            'steps_taken': self.metrics.steps_taken,
            'failed_tactics': self.metrics.failed_tactics,
            'backtrack_count': self.metrics.backtrack_count,
            'goals_created': self.metrics.goals_created,
            'goals_closed': self.metrics.goals_closed,
            'final_entropy': self.metrics.get_latest_entropy(),
            'entropy_trend': self.metrics.get_entropy_trend(),
            'responsible_heuristic': self.current_heuristic
        }
    
    def __enter__(self):
        """Context manager entry."""
        logger.debug(f"Starting proof attempt for {self.theorem.name if self.theorem else 'unknown'}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        summary = self.get_summary()
        logger.info(f"Proof attempt ended: {summary}")
        
        if self.trace_recorder:
            self.trace_recorder.record_custom_event('proof_runner_summary', summary)
            
        return False  # Don't suppress exceptions


class ProofRunnerPool:
    """
    Manages multiple proof runners for parallel proof search.
    
    This is a placeholder for future functionality where multiple
    proof attempts could be run in parallel with different strategies.
    """
    
    def __init__(self, max_runners: int = 4):
        self.max_runners = max_runners
        self.active_runners: List[ProofRunner] = []
        
    def create_runner(self, **kwargs) -> ProofRunner:
        """Create a new proof runner."""
        if len(self.active_runners) >= self.max_runners:
            raise RuntimeError(f"Maximum number of runners ({self.max_runners}) reached")
            
        runner = ProofRunner(**kwargs)
        self.active_runners.append(runner)
        return runner
    
    def remove_runner(self, runner: ProofRunner) -> None:
        """Remove a runner from the pool."""
        if runner in self.active_runners:
            self.active_runners.remove(runner)