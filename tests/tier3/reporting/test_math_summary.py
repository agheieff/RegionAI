"""
Tests for the mathematical reasoning summary report generator.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from regionai.tools.reporting.math_summary import (
    generate_summary_report,
    generate_brief_summary,
    _format_duration,
    _percentage,
    _format_table_header,
    _format_result_row,
    _truncate_error
)


class TestMathSummary(unittest.TestCase):
    """Test the math summary report generation."""
    
    def setUp(self):
        """Create mock session and results for testing."""
        self.mock_session = Mock()
        self.mock_session.start_time = datetime.now() - timedelta(minutes=5)
        self.mock_session.config = Mock()
        self.mock_session.config.max_proof_sec = 600
        
        # Create mock results
        self.success_result = Mock()
        self.success_result.theorem_name = "self_implication"
        self.success_result.status = "SUCCESS"
        self.success_result.steps_taken = 3
        self.success_result.time_seconds = 0.5
        self.success_result.error_message = None
        self.success_result.responsible_heuristic = None
        
        self.timeout_result = Mock()
        self.timeout_result.theorem_name = "complex_theorem"
        self.timeout_result.status = "TIMEOUT"
        self.timeout_result.steps_taken = 1000
        self.timeout_result.time_seconds = 600.0
        self.timeout_result.error_message = "Time budget exceeded: 600.5s > 600s"
        self.timeout_result.responsible_heuristic = "math.intro"
        
        self.no_progress_result = Mock()
        self.no_progress_result.theorem_name = "difficult_theorem"
        self.no_progress_result.status = "NO_PROGRESS"
        self.no_progress_result.steps_taken = 500
        self.no_progress_result.time_seconds = 45.2
        self.no_progress_result.error_message = "Insufficient progress: entropy trend 0.0012"
        self.no_progress_result.responsible_heuristic = "math.apply"
        
        self.error_result = Mock()
        self.error_result.theorem_name = "broken_theorem"
        self.error_result.status = "ERROR"
        self.error_result.steps_taken = 0
        self.error_result.time_seconds = 0.1
        self.error_result.error_message = "Unexpected error: Division by zero"
        self.error_result.responsible_heuristic = None
        
    def test_generate_summary_report_all_success(self):
        """Test report generation with all successful proofs."""
        # Setup session with only successes
        self.mock_session.results = [self.success_result] * 3
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 3,
            'success': 3,
            'timeout': 0,
            'no_progress': 0,
            'error': 0
        })
        
        report = generate_summary_report(self.mock_session)
        
        # Check key elements
        self.assertIn("Mathematical Reasoning Bootstrap Report", report)
        self.assertIn("Total Theorems: 3", report)
        self.assertIn("Successes: 3 (100.0%)", report)
        self.assertIn("Timeouts: 0 (0.0%)", report)
        self.assertIn("Successfully Proved Theorems", report)
        self.assertIn("✓ self_implication", report)
        
    def test_generate_summary_report_mixed_results(self):
        """Test report generation with mixed results."""
        # Setup session with mixed results
        self.mock_session.results = [
            self.success_result,
            self.timeout_result,
            self.no_progress_result,
            self.error_result
        ]
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 4,
            'success': 1,
            'timeout': 1,
            'no_progress': 1,
            'error': 1
        })
        
        report = generate_summary_report(self.mock_session)
        
        # Check statistics
        self.assertIn("Total Theorems: 4", report)
        self.assertIn("Successes: 1 (25.0%)", report)
        self.assertIn("Timeouts: 1 (25.0%)", report)
        self.assertIn("No Progress: 1 (25.0%)", report)
        self.assertIn("Errors: 1 (25.0%)", report)
        
        # Check failure analysis
        self.assertIn("Failure Analysis", report)
        self.assertIn("Timeouts (Exponential Safety Net Triggered):", report)
        self.assertIn("complex_theorem", report)
        self.assertIn("Responsible heuristic: math.intro", report)
        
        self.assertIn("No Progress (Insufficient Entropy Reduction):", report)
        self.assertIn("difficult_theorem", report)
        self.assertIn("Responsible heuristic: math.apply", report)
        
        self.assertIn("Errors:", report)
        self.assertIn("broken_theorem", report)
        self.assertIn("Division by zero", report)
        
        # Check heuristic failures
        self.assertIn("Heuristic Failure Count", report)
        self.assertIn("math.intro: 1 failures", report)
        self.assertIn("math.apply: 1 failures", report)
        
    def test_generate_summary_report_table_format(self):
        """Test that the theorem breakdown table is properly formatted."""
        self.mock_session.results = [self.success_result, self.timeout_result]
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 2,
            'success': 1,
            'timeout': 1,
            'no_progress': 0,
            'error': 0
        })
        
        report = generate_summary_report(self.mock_session)
        
        # Check table header and content
        self.assertIn("Theorem Breakdown", report)
        self.assertIn("Theorem Name", report)
        self.assertIn("Status", report)
        self.assertIn("Steps", report)
        self.assertIn("Time (s)", report)
        
        # Check specific rows
        self.assertIn("self_implication", report)
        self.assertIn("✓ SUCCESS", report)
        self.assertIn("     3", report)  # Steps right-aligned
        self.assertIn("    0.50", report)  # Time right-aligned
        
        self.assertIn("complex_theorem", report)
        self.assertIn("⏱ TIMEOUT", report)
        self.assertIn("  1000", report)
        self.assertIn("  600.00", report)
        
    def test_generate_brief_summary(self):
        """Test brief summary generation."""
        self.mock_session.results = [self.success_result, self.timeout_result]
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 2,
            'success': 1,
            'timeout': 1,
            'no_progress': 0,
            'error': 0
        })
        self.mock_session.start_time = datetime.now() - timedelta(seconds=30)
        
        summary = generate_brief_summary(self.mock_session)
        
        self.assertIn("Proved 1/2 theorems", summary)
        self.assertIn("(50.0%)", summary)
        self.assertIn("in", summary)  # Duration included
        
    def test_format_duration(self):
        """Test duration formatting."""
        start = datetime.now()
        
        # Test seconds
        end = start + timedelta(seconds=45)
        self.assertEqual(_format_duration(start, end), "45s")
        
        # Test minutes and seconds
        end = start + timedelta(seconds=125)
        self.assertEqual(_format_duration(start, end), "2m 5s")
        
        # Test hours and minutes
        end = start + timedelta(seconds=7320)
        self.assertEqual(_format_duration(start, end), "2h 2m")
        
    def test_percentage(self):
        """Test percentage formatting."""
        self.assertEqual(_percentage(0, 10), "0.0%")
        self.assertEqual(_percentage(5, 10), "50.0%")
        self.assertEqual(_percentage(10, 10), "100.0%")
        self.assertEqual(_percentage(1, 3), "33.3%")
        self.assertEqual(_percentage(0, 0), "0%")  # Edge case
        
    def test_format_table_header(self):
        """Test table header formatting."""
        header = _format_table_header()
        self.assertIn("Theorem Name", header)
        self.assertIn("Status", header)
        self.assertIn("Steps", header)
        self.assertIn("Time (s)", header)
        self.assertIn("|", header)  # Column separators
        
    def test_format_result_row(self):
        """Test result row formatting."""
        # Test success row
        row = _format_result_row(self.success_result)
        self.assertIn("self_implication", row)
        self.assertIn("✓ SUCCESS", row)
        self.assertIn("3", row)
        self.assertIn("0.50", row)
        
        # Test timeout row
        row = _format_result_row(self.timeout_result)
        self.assertIn("complex_theorem", row)
        self.assertIn("⏱ TIMEOUT", row)
        self.assertIn("1000", row)
        self.assertIn("600.00", row)
        
        # Test long theorem name truncation
        long_result = Mock()
        long_result.theorem_name = "a_very_long_theorem_name_that_exceeds_thirty_characters"
        long_result.status = "SUCCESS"
        long_result.steps_taken = 5
        long_result.time_seconds = 1.0
        
        row = _format_result_row(long_result)
        # Should be truncated to 30 chars
        self.assertIn("a_very_long_theorem_name_that_", row)
        self.assertNotIn("exceeds_thirty_characters", row)
        
    def test_truncate_error(self):
        """Test error message truncation."""
        # Short message should not be truncated
        short_msg = "Short error"
        self.assertEqual(_truncate_error(short_msg), short_msg)
        
        # Long message should be truncated
        long_msg = "A" * 100
        truncated = _truncate_error(long_msg, max_length=20)
        self.assertEqual(len(truncated), 20)
        self.assertTrue(truncated.endswith("..."))
        self.assertEqual(truncated, "A" * 17 + "...")
        
    def test_empty_session(self):
        """Test report generation with empty session."""
        self.mock_session.results = []
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 0,
            'success': 0,
            'timeout': 0,
            'no_progress': 0,
            'error': 0
        })
        
        report = generate_summary_report(self.mock_session)
        
        # Should still generate a valid report
        self.assertIn("Mathematical Reasoning Bootstrap Report", report)
        self.assertIn("Total Theorems: 0", report)
        self.assertIn("Theorem Breakdown", report)
        
    def test_performance_metrics(self):
        """Test performance metrics calculation."""
        # Create multiple results with different times
        results = []
        for i in range(5):
            result = Mock()
            result.theorem_name = f"theorem_{i}"
            result.status = "SUCCESS" if i < 3 else "TIMEOUT"
            result.steps_taken = (i + 1) * 10
            result.time_seconds = (i + 1) * 0.5
            result.error_message = None
            result.responsible_heuristic = None
            results.append(result)
            
        self.mock_session.results = results
        self.mock_session.get_summary_stats = Mock(return_value={
            'total': 5,
            'success': 3,
            'timeout': 2,
            'no_progress': 0,
            'error': 0
        })
        
        report = generate_summary_report(self.mock_session)
        
        # Check performance metrics section
        self.assertIn("Performance Metrics", report)
        self.assertIn("Average Success Time:", report)
        self.assertIn("Fastest Success:", report)
        self.assertIn("Slowest Success:", report)
        self.assertIn("Average Attempt Time:", report)
        self.assertIn("Average Steps:", report)


if __name__ == '__main__':
    unittest.main()