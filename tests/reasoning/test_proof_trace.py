"""
Tests for proof trace recording functionality.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json
import tempfile
import threading
from pathlib import Path

from regionai.scenarios.proof_trace import (
    ProofTraceRecorder, ProofTraceAnalyzer
)
from regionai.linguistics.lean_ast import (
    ProofStep, Tactic, TacticType, ProofState, Hypothesis
)


class TestProofTraceRecorder:
    """Test the ProofTraceRecorder class."""
    
    def test_basic_creation(self):
        """Test creating a trace recorder."""
        recorder = ProofTraceRecorder()
        assert recorder.events == []
        assert recorder.proof_steps == []
        assert not recorder._is_closed
        assert recorder.trace_file is None
    
    def test_with_trace_file(self):
        """Test recorder with trace file."""
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as tmp:
            trace_path = Path(tmp.name)
        
        try:
            recorder = ProofTraceRecorder(trace_file=trace_path)
            assert recorder.trace_file == trace_path
            
            # Check that initial event was written
            recorder.close()
            
            with open(trace_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 2  # Start and end events
                first_event = json.loads(lines[0])
                assert first_event['event_type'] == 'trace_start'
        finally:
            trace_path.unlink(missing_ok=True)
    
    def test_set_theorem_info(self):
        """Test setting theorem information."""
        recorder = ProofTraceRecorder()
        recorder.set_theorem_info("test_theorem", "P → P")
        
        assert recorder.theorem_name == "test_theorem"
        assert recorder.theorem_statement == "P → P"
        assert len(recorder.events) == 1
        assert recorder.events[0].event_type == 'theorem_info'
    
    def test_record_proof_step(self):
        """Test recording a proof step."""
        recorder = ProofTraceRecorder()
        
        # Create a proof step
        tactic = Tactic(TacticType.INTRO, arguments=["h"])
        before = ProofState(goals=["P → Q"])
        after = ProofState(goals=["Q"], hypotheses=[Hypothesis("h", "P")])
        
        step = ProofStep(
            step_number=1,
            tactic=tactic,
            before_state=before,
            after_state=after,
            success=True,
            time_ms=10.5
        )
        
        recorder.record_step(step)
        
        assert len(recorder.proof_steps) == 1
        assert recorder.proof_steps[0] == step
        assert recorder.tactic_counts["intro"] == 1
        assert len(recorder.events) == 1
        assert recorder.events[0].event_type == 'proof_step'
    
    def test_record_error(self):
        """Test recording an error."""
        recorder = ProofTraceRecorder()
        
        recorder.record_error(
            error_type="tactic_failure",
            error_message="Tactic 'apply' failed",
            context={"tactic": "apply h"}
        )
        
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == 'error'
        assert event.data['error_type'] == 'tactic_failure'
        assert event.data['error_message'] == "Tactic 'apply' failed"
        assert event.data['context']['tactic'] == "apply h"
    
    def test_record_timeout(self):
        """Test recording a timeout."""
        recorder = ProofTraceRecorder()
        
        final_state = ProofState(goals=["Goal1", "Goal2"])
        recorder.record_timeout(600.0, final_state)
        
        assert recorder.final_status == 'timeout'
        assert len(recorder.events) == 1
        event = recorder.events[0]
        assert event.event_type == 'timeout'
        assert event.data['timeout_seconds'] == 600.0
        assert event.data['remaining_goals'] == 2
    
    def test_record_success(self):
        """Test recording successful proof completion."""
        recorder = ProofTraceRecorder()
        
        # Add some steps first
        for i in range(5):
            step = ProofStep(
                step_number=i+1,
                tactic=Tactic(TacticType.SIMP),
                before_state=ProofState(goals=[f"Goal{i}"]),
                success=True
            )
            recorder.record_step(step)
        
        recorder.record_success(final_proof_length=5)
        
        assert recorder.final_status == 'success'
        # Should have 5 step events + 1 success event
        assert len(recorder.events) == 6
        assert recorder.events[-1].event_type == 'proof_success'
    
    def test_thread_safety(self):
        """Test that recorder is thread-safe."""
        recorder = ProofTraceRecorder()
        
        def add_events(thread_id, count):
            for i in range(count):
                recorder.record_custom_event(
                    f"thread_{thread_id}_event",
                    {"index": i}
                )
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_events, args=(i, 10))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have 50 events total
        assert len(recorder.events) == 50
        
        # Check that all thread IDs are present
        thread_ids = set()
        for event in recorder.events:
            thread_ids.add(event.thread_id)
        assert len(thread_ids) == 5
    
    def test_get_summary(self):
        """Test getting trace summary."""
        recorder = ProofTraceRecorder()
        recorder.set_theorem_info("test", "P")
        
        # Add some successful and failed steps
        for i in range(3):
            step = ProofStep(
                step_number=i+1,
                tactic=Tactic(TacticType.INTRO),
                before_state=ProofState(goals=["G"]),
                success=True
            )
            recorder.record_step(step)
        
        # Add a failed step
        failed_step = ProofStep(
            step_number=4,
            tactic=Tactic(TacticType.APPLY),
            before_state=ProofState(goals=["G"]),
            success=False,
            error="Type mismatch"
        )
        recorder.record_step(failed_step)
        
        summary = recorder.get_summary()
        assert summary['theorem_name'] == "test"
        assert summary['total_steps'] == 4
        assert summary['successful_steps'] == 3
        assert summary['failed_steps'] == 1
        assert summary['tactic_counts']['intro'] == 3
        assert summary['tactic_counts']['apply'] == 1
        assert summary['error_counts']['Type mismatch'] == 1
    
    def test_context_manager(self):
        """Test using recorder as context manager."""
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as tmp:
            trace_path = Path(tmp.name)
        
        try:
            with ProofTraceRecorder(trace_file=trace_path) as recorder:
                recorder.record_custom_event("test", {"data": "value"})
                assert not recorder._is_closed
            
            # Should be closed after exiting context
            assert recorder._is_closed
            
            # Check file contains proper events
            with open(trace_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 3  # start, custom event, end
        finally:
            trace_path.unlink(missing_ok=True)
    
    def test_cannot_record_after_close(self):
        """Test that recording after close raises error."""
        recorder = ProofTraceRecorder()
        recorder.close()
        
        with pytest.raises(RuntimeError, match="Cannot record to closed trace"):
            step = ProofStep(1, Tactic(TacticType.SIMP), ProofState())
            recorder.record_step(step)


class TestProofTraceAnalyzer:
    """Test the ProofTraceAnalyzer class."""
    
    def test_load_trace(self):
        """Test loading a trace file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as tmp:
            # Write some test events
            json.dump({"event_type": "start", "data": {}}, tmp)
            tmp.write('\n')
            json.dump({"event_type": "proof_step", "data": {"success": True}}, tmp)
            tmp.write('\n')
            json.dump({"event_type": "end", "data": {}}, tmp)
            tmp.write('\n')
            trace_path = Path(tmp.name)
        
        try:
            events = ProofTraceAnalyzer.load_trace(trace_path)
            assert len(events) == 3
            assert events[0]['event_type'] == 'start'
            assert events[1]['event_type'] == 'proof_step'
            assert events[2]['event_type'] == 'end'
        finally:
            trace_path.unlink(missing_ok=True)
    
    def test_analyze_trace(self):
        """Test analyzing a trace."""
        events = [
            {
                'event_type': 'proof_step',
                'data': {
                    'tactic_type': 'intro',
                    'success': True,
                    'time_ms': 10.0
                }
            },
            {
                'event_type': 'proof_step',
                'data': {
                    'tactic_type': 'intro',
                    'success': True,
                    'time_ms': 15.0
                }
            },
            {
                'event_type': 'proof_step',
                'data': {
                    'tactic_type': 'apply',
                    'success': False,
                    'time_ms': 20.0
                }
            },
            {
                'event_type': 'trace_end',
                'summary': {
                    'total_steps': 3,
                    'theorem_name': 'test'
                }
            }
        ]
        
        analysis = ProofTraceAnalyzer.analyze_trace(events)
        
        assert analysis['total_events'] == 4
        assert analysis['event_types']['proof_step'] == 3
        assert analysis['event_types']['trace_end'] == 1
        
        # Check tactic success rates
        intro_stats = analysis['tactic_success_rates']['intro']
        assert intro_stats['attempts'] == 2
        assert intro_stats['successes'] == 2
        assert intro_stats['success_rate'] == 1.0
        
        apply_stats = analysis['tactic_success_rates']['apply']
        assert apply_stats['attempts'] == 1
        assert apply_stats['successes'] == 0
        assert apply_stats['success_rate'] == 0.0
        
        # Check timing
        assert analysis['time_per_step'] == [10.0, 15.0, 20.0]
        
        # Check summary extraction
        assert analysis['summary']['theorem_name'] == 'test'