"""
Thread-safe proof trace recording for RegionAI.

This module provides utilities for recording detailed traces of proof
attempts, enabling post-hoc analysis and learning from both successful
and failed proofs.
"""

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import logging

from tier2.linguistics.lean_ast import ProofStep, Tactic, ProofState


logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """
    Represents a single event in a proof trace.
    
    Attributes:
        timestamp: When the event occurred
        event_type: Type of event (e.g., 'tactic_apply', 'goal_change', 'error')
        data: Event-specific data
        thread_id: ID of the thread that generated this event
    """
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]
    thread_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'data': self.data,
            'thread_id': self.thread_id
        }


class ProofTraceRecorder:
    """
    Thread-safe recorder for proof attempt traces.
    
    This class records detailed information about proof attempts,
    including applied tactics, state changes, timing information,
    and errors. The traces are written to JSONL (JSON Lines) format
    for easy streaming and analysis.
    
    Thread Safety:
        All public methods are thread-safe through the use of a lock.
        Multiple threads can safely record events to the same trace.
    """
    
    def __init__(self, trace_file: Optional[Union[str, Path]] = None, config=None):
        """
        Initialize a new proof trace recorder.
        
        Args:
            trace_file: Path to the JSONL trace file. If None, traces
                       are only kept in memory.
            config: Configuration object. If None, uses DEFAULT_CONFIG.
        """
        from ..config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        
        self.trace_file = Path(trace_file) if trace_file else None
        self.events: List[TraceEvent] = []
        self.proof_steps: List[ProofStep] = []
        self._lock = threading.Lock()
        self._start_time = time.monotonic()
        self._is_closed = False
        
        # Buffered writer for efficiency
        self._file_handle = None
        self._write_buffer: List[str] = []
        self._buffer_size = config.proof_trace_buffer_size  # Configurable buffer size
        self._last_flush_time = time.time()
        
        # Proof metadata
        self.theorem_name: Optional[str] = None
        self.theorem_statement: Optional[str] = None
        self.final_status: Optional[str] = None  # 'success', 'failure', 'timeout'
        self.total_time_ms: float = 0.0
        
        # Statistics
        self.tactic_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Create trace file if specified
        if self.trace_file:
            self.trace_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                # Open file handle for buffered writing with no buffering
                self._file_handle = open(self.trace_file, 'a', buffering=1)
                # Write initial metadata
                self._write_event({
                    'event_type': 'trace_start',
                    'timestamp': datetime.now().isoformat(),
                    'trace_file': str(self.trace_file)
                })
            except Exception as e:
                logger.error(f"Failed to open trace file: {e}")
                self._file_handle = None
                self.trace_file = None
    
    def set_theorem_info(self, name: str, statement: str) -> None:
        """
        Set information about the theorem being proved.
        
        Args:
            name: Name of the theorem
            statement: The theorem statement
        """
        with self._lock:
            self.theorem_name = name
            self.theorem_statement = statement
            
            # Record theorem info event
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='theorem_info',
                data={'name': name, 'statement': statement},
                thread_id=threading.get_ident()
            )
            self._add_event(event)
            
            # Also record theorem start event for mining
            start_event = TraceEvent(
                timestamp=datetime.now(),
                event_type='theorem_start',
                data={'name': name, 'statement': statement},
                thread_id=threading.get_ident()
            )
            self._add_event(start_event)
    
    def record_step(self, proof_step: ProofStep) -> None:
        """
        Record a proof step.
        
        This is the main method for recording tactic applications
        and their results.
        
        Args:
            proof_step: The proof step to record
        """
        with self._lock:
            if self._is_closed:
                raise RuntimeError("Cannot record to closed trace")
                
            self.proof_steps.append(proof_step)
            
            # Update statistics
            tactic_name = proof_step.tactic.tactic_type.value
            self.tactic_counts[tactic_name] = self.tactic_counts.get(tactic_name, 0) + 1
            
            if not proof_step.success and proof_step.error:
                self.error_counts[proof_step.error] = self.error_counts.get(proof_step.error, 0) + 1
            
            # Create event
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='proof_step',
                data=proof_step.to_dict(),
                thread_id=threading.get_ident()
            )
            self._add_event(event)
    
    def record_tactic_application(self, tactic: Tactic, before_state: ProofState, 
                                after_state: ProofState, success: bool) -> None:
        """
        Record a tactic application with before/after states.
        
        Args:
            tactic: The tactic that was applied
            before_state: The proof state before applying the tactic
            after_state: The proof state after applying the tactic
            success: Whether the tactic succeeded
        """
        with self._lock:
            if self._is_closed:
                raise RuntimeError("Cannot record to closed trace")
            
            # Create event with tactic details
            event_data = {
                'tactic': tactic.tactic_type.value,
                'tactic_type': tactic.tactic_type.value,
                'arguments': tactic.arguments,
                'success': success,
                'goal_before': before_state.current_goal,
                'goal_after': after_state.current_goal if after_state else None,
                'error': after_state.metadata.get('last_error') if after_state and not success else None
            }
            
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='tactic_apply',
                data=event_data,
                thread_id=threading.get_ident()
            )
            self._add_event(event)
            
            # Update tactic counts
            tactic_name = tactic.tactic_type.value
            self.tactic_counts[tactic_name] = self.tactic_counts.get(tactic_name, 0) + 1
    
    def record_tactic_attempt(self, tactic: Tactic, before_state: ProofState) -> None:
        """
        Record the start of a tactic application.
        
        Args:
            tactic: The tactic being applied
            before_state: The proof state before applying the tactic
        """
        with self._lock:
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='tactic_attempt',
                data={
                    'tactic': str(tactic),
                    'tactic_type': tactic.tactic_type.value,
                    'goals_count': len(before_state.goals),
                    'hypotheses_count': len(before_state.hypotheses)
                },
                thread_id=threading.get_ident()
            )
            self._add_event(event)
    
    def record_error(self, error_type: str, error_message: str, 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an error during proof attempt.
        
        Args:
            error_type: Type of error (e.g., 'tactic_failure', 'timeout')
            error_message: Detailed error message
            context: Optional additional context
        """
        with self._lock:
            data = {
                'error_type': error_type,
                'error_message': error_message,
                'elapsed_ms': self._get_elapsed_ms()
            }
            if context:
                data['context'] = context
                
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='error',
                data=data,
                thread_id=threading.get_ident()
            )
            self._add_event(event)
    
    def record_timeout(self, timeout_seconds: float, final_state: Optional[ProofState] = None) -> None:
        """
        Record that the proof attempt timed out.
        
        Args:
            timeout_seconds: The timeout limit that was exceeded
            final_state: The proof state when timeout occurred
        """
        with self._lock:
            data = {
                'timeout_seconds': timeout_seconds,
                'elapsed_ms': self._get_elapsed_ms(),
                'steps_completed': len(self.proof_steps)
            }
            
            if final_state:
                data['remaining_goals'] = len(final_state.goals)
                data['final_goals'] = [str(g) for g in final_state.goals]
                
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='timeout',
                data=data,
                thread_id=threading.get_ident()
            )
            self._add_event(event)
            
            self.final_status = 'timeout'
    
    def record_success(self, final_proof_length: int) -> None:
        """
        Record successful proof completion.
        
        Args:
            final_proof_length: Number of tactics in the final proof
        """
        with self._lock:
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type='proof_success',
                data={
                    'proof_length': final_proof_length,
                    'total_steps_tried': len(self.proof_steps),
                    'elapsed_ms': self._get_elapsed_ms()
                },
                thread_id=threading.get_ident()
            )
            self._add_event(event)
            
            self.final_status = 'success'
    
    def record_custom_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Record a custom event.
        
        Args:
            event_type: Type of the custom event
            data: Event data
        """
        with self._lock:
            event = TraceEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                data=data,
                thread_id=threading.get_ident()
            )
            self._add_event(event)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the recorded trace.
        
        Returns:
            Dictionary containing trace statistics and summary
        """
        with self._lock:
            return self._get_summary_unlocked()
    
    def _get_summary_unlocked(self) -> Dict[str, Any]:
        """Get summary without acquiring lock (must be called under lock)."""
        return {
            'theorem_name': self.theorem_name,
            'theorem_statement': self.theorem_statement,
            'final_status': self.final_status,
            'total_time_ms': self._get_elapsed_ms(),
            'total_steps': len(self.proof_steps),
            'successful_steps': sum(1 for s in self.proof_steps if s.success),
            'failed_steps': sum(1 for s in self.proof_steps if not s.success),
            'tactic_counts': dict(self.tactic_counts),
            'error_counts': dict(self.error_counts),
            'events_count': len(self.events),
            'thread_count': len(set(e.thread_id for e in self.events))
        }
    
    def close(self) -> None:
        """
        Close the trace recorder and write final summary.
        
        After closing, no more events can be recorded.
        """
        with self._lock:
            if self._is_closed:
                return
                
            self.total_time_ms = self._get_elapsed_ms()
            
            # Write final summary
            if self._file_handle:
                summary = self._get_summary_unlocked()
                self._write_event({
                    'event_type': 'trace_end',
                    'timestamp': datetime.now().isoformat(),
                    'summary': summary
                })
                
                # Flush any remaining buffer and close file
                self._flush_buffer()
                try:
                    self._file_handle.close()
                except Exception as e:
                    logger.error(f"Failed to close trace file: {e}")
                self._file_handle = None
                
            self._is_closed = True
            logger.info(f"Closed proof trace with {len(self.events)} events")
    
    def _add_event(self, event: TraceEvent) -> None:
        """Add an event to the trace (must be called under lock)."""
        self.events.append(event)
        
        if self.trace_file:
            self._write_event(event.to_dict())
    
    def _write_event(self, data: Dict[str, Any]) -> None:
        """Write an event to the trace file (must be called under lock)."""
        if not self._file_handle:
            return
            
        try:
            # Add to buffer
            self._write_buffer.append(json.dumps(data) + '\n')
            
            # Flush if buffer is full or it's been more than 1 second
            current_time = time.time()
            if (len(self._write_buffer) >= self._buffer_size or 
                current_time - self._last_flush_time > 1.0):
                self._flush_buffer()
                
        except Exception as e:
            logger.error(f"Failed to write trace event: {e}")
    
    def _flush_buffer(self) -> None:
        """Flush the write buffer to disk (must be called under lock)."""
        if not self._file_handle or not self._write_buffer:
            return
            
        try:
            self._file_handle.writelines(self._write_buffer)
            self._file_handle.flush()
            # Force OS to write to disk
            import os
            os.fsync(self._file_handle.fileno())
            self._write_buffer.clear()
            self._last_flush_time = time.time()
        except Exception as e:
            logger.error(f"Failed to flush trace buffer: {e}")
    
    def _get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds since recorder creation."""
        return (time.monotonic() - self._start_time) * 1000
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures trace is closed."""
        self.close()
        return False
    
    def __del__(self):
        """Destructor - ensures trace is properly closed.
        
        Note: This is a fallback safety measure. Always use close() or
        context manager for proper resource cleanup.
        """
        # Only attempt cleanup if not already closed
        if hasattr(self, '_is_closed') and not self._is_closed:
            try:
                self.close()
            except Exception:
                # Best effort in destructor - avoid raising exceptions
                pass


class ProofTraceAnalyzer:
    """
    Analyzer for proof traces.
    
    This class provides utilities for analyzing recorded proof traces
    to extract patterns, identify bottlenecks, and learn from failures.
    """
    
    @staticmethod
    def load_trace(trace_file: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load a trace file.
        
        Args:
            trace_file: Path to the JSONL trace file
            
        Returns:
            List of trace events
        """
        events = []
        with open(trace_file, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        return events
    
    @staticmethod
    def analyze_trace(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a trace to extract patterns and statistics.
        
        Args:
            events: List of trace events
            
        Returns:
            Analysis results
        """
        analysis = {
            'total_events': len(events),
            'event_types': {},
            'tactic_success_rates': {},
            'error_patterns': {},
            'time_per_step': []
        }
        
        # Count event types
        for event in events:
            event_type = event.get('event_type', 'unknown')
            analysis['event_types'][event_type] = analysis['event_types'].get(event_type, 0) + 1
        
        # Analyze proof steps
        tactic_attempts = {}
        tactic_successes = {}
        
        for event in events:
            if event.get('event_type') == 'proof_step':
                data = event.get('data', {})
                tactic_type = data.get('tactic_type', 'unknown')
                
                tactic_attempts[tactic_type] = tactic_attempts.get(tactic_type, 0) + 1
                if data.get('success', False):
                    tactic_successes[tactic_type] = tactic_successes.get(tactic_type, 0) + 1
                    
                if 'time_ms' in data:
                    analysis['time_per_step'].append(data['time_ms'])
        
        # Calculate success rates
        for tactic_type, attempts in tactic_attempts.items():
            successes = tactic_successes.get(tactic_type, 0)
            analysis['tactic_success_rates'][tactic_type] = {
                'attempts': attempts,
                'successes': successes,
                'success_rate': successes / attempts if attempts > 0 else 0
            }
        
        # Extract summary if present
        for event in reversed(events):
            if event.get('event_type') == 'trace_end':
                analysis['summary'] = event.get('summary', {})
                break
                
        return analysis