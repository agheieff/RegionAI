"""
Mathematical reasoning summary report generator.

This module provides functionality to generate human-readable reports
from bootstrap session results, including detailed breakdowns and
failure analysis.
"""

from typing import Any
from datetime import datetime
import statistics


def generate_summary_report(session: Any) -> str:
    """
    Generate a comprehensive summary report from a bootstrap session.
    
    Args:
        session: BootstrapSession object containing results
        
    Returns:
        Formatted report string
    """
    lines = []
    
    # Header
    lines.append("Mathematical Reasoning Bootstrap Report")
    lines.append("=" * 50)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Session Duration: {_format_duration(session.start_time, datetime.now())}")
    lines.append("")
    
    # Overall statistics
    stats = session.get_summary_stats()
    lines.append("Overall Statistics")
    lines.append("-" * 30)
    lines.append(f"Total Theorems: {stats['total']}")
    lines.append(f"Successes: {stats['success']} ({_percentage(stats['success'], stats['total'])})")
    lines.append(f"Timeouts: {stats['timeout']} ({_percentage(stats['timeout'], stats['total'])})")
    lines.append(f"No Progress: {stats['no_progress']} ({_percentage(stats['no_progress'], stats['total'])})")
    lines.append(f"Errors: {stats['error']} ({_percentage(stats['error'], stats['total'])})")
    lines.append("")
    
    # Performance metrics
    if session.results:
        lines.append("Performance Metrics")
        lines.append("-" * 30)
        
        success_times = [r.time_seconds for r in session.results if r.status == "SUCCESS"]
        all_times = [r.time_seconds for r in session.results]
        all_steps = [r.steps_taken for r in session.results if r.steps_taken > 0]
        
        if success_times:
            lines.append(f"Average Success Time: {statistics.mean(success_times):.2f}s")
            lines.append(f"Fastest Success: {min(success_times):.2f}s")
            lines.append(f"Slowest Success: {max(success_times):.2f}s")
        
        if all_times:
            lines.append(f"Average Attempt Time: {statistics.mean(all_times):.2f}s")
            
        if all_steps:
            lines.append(f"Average Steps: {statistics.mean(all_steps):.1f}")
            
        lines.append("")
    
    # Detailed theorem breakdown
    lines.append("Theorem Breakdown")
    lines.append("-" * 80)
    lines.append(_format_table_header())
    lines.append("-" * 80)
    
    # Sort results by status (successes first) then by name
    sorted_results = sorted(
        session.results,
        key=lambda r: (0 if r.status == "SUCCESS" else 1, r.theorem_name)
    )
    
    for result in sorted_results:
        lines.append(_format_result_row(result))
    
    lines.append("-" * 80)
    lines.append("")
    
    # Failure analysis
    failures = [r for r in session.results if r.status != "SUCCESS"]
    if failures:
        lines.append("Failure Analysis")
        lines.append("-" * 50)
        
        # Group by failure type
        lines.append("\nTimeouts (Exponential Safety Net Triggered):")
        timeouts = [r for r in failures if r.status == "TIMEOUT"]
        if timeouts:
            for result in timeouts:
                lines.append(f"  • {result.theorem_name}")
                if result.responsible_heuristic:
                    lines.append(f"    Responsible heuristic: {result.responsible_heuristic}")
                if result.error_message:
                    lines.append(f"    Reason: {_truncate_error(result.error_message)}")
        else:
            lines.append("  None")
            
        lines.append("\nNo Progress (Insufficient Entropy Reduction):")
        no_progress = [r for r in failures if r.status == "NO_PROGRESS"]
        if no_progress:
            for result in no_progress:
                lines.append(f"  • {result.theorem_name}")
                if result.responsible_heuristic:
                    lines.append(f"    Responsible heuristic: {result.responsible_heuristic}")
                if result.error_message:
                    lines.append(f"    Reason: {_truncate_error(result.error_message)}")
        else:
            lines.append("  None")
            
        lines.append("\nErrors:")
        errors = [r for r in failures if r.status == "ERROR"]
        if errors:
            for result in errors:
                lines.append(f"  • {result.theorem_name}")
                if result.error_message:
                    lines.append(f"    Error: {_truncate_error(result.error_message)}")
        else:
            lines.append("  None")
            
        lines.append("")
    
    # Heuristic performance
    heuristic_failures = {}
    for result in failures:
        if result.responsible_heuristic:
            if result.responsible_heuristic not in heuristic_failures:
                heuristic_failures[result.responsible_heuristic] = 0
            heuristic_failures[result.responsible_heuristic] += 1
    
    if heuristic_failures:
        lines.append("Heuristic Failure Count")
        lines.append("-" * 30)
        for heuristic, count in sorted(heuristic_failures.items(), key=lambda x: -x[1]):
            lines.append(f"  {heuristic}: {count} failures")
        lines.append("")
    
    # Success highlights
    successes = [r for r in session.results if r.status == "SUCCESS"]
    if successes:
        lines.append("Successfully Proved Theorems")
        lines.append("-" * 30)
        for result in sorted(successes, key=lambda r: r.steps_taken):
            lines.append(f"  ✓ {result.theorem_name} ({result.steps_taken} steps, {result.time_seconds:.2f}s)")
        lines.append("")
    
    # Configuration used
    lines.append("Configuration")
    lines.append("-" * 30)
    lines.append(f"Max proof time: {session.config.max_proof_sec}s")
    lines.append(f"Mock executor used: {'Yes' if hasattr(session, 'use_mock_executor') else 'Unknown'}")
    
    return "\n".join(lines)


def _format_duration(start_time: datetime, end_time: datetime) -> str:
    """Format a duration in human-readable form."""
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def _percentage(value: int, total: int) -> str:
    """Format a percentage."""
    if total == 0:
        return "0%"
    return f"{(value / total * 100):.1f}%"


def _format_table_header() -> str:
    """Format the table header for theorem breakdown."""
    return f"{'Theorem Name':<30} | {'Status':<12} | {'Steps':>6} | {'Time (s)':>8}"


def _format_result_row(result: Any) -> str:
    """Format a single result row for the table."""
    status_icon = {
        "SUCCESS": "✓",
        "TIMEOUT": "⏱",
        "NO_PROGRESS": "↻",
        "ERROR": "✗"
    }.get(result.status, "?")
    
    status_str = f"{status_icon} {result.status}"
    
    return (f"{result.theorem_name[:30]:<30} | "
            f"{status_str:<12} | "
            f"{result.steps_taken:>6} | "
            f"{result.time_seconds:>8.2f}")


def _truncate_error(error_message: str, max_length: int = 60) -> str:
    """Truncate an error message to a reasonable length."""
    if len(error_message) <= max_length:
        return error_message
    return error_message[:max_length-3] + "..."


def generate_brief_summary(session: Any) -> str:
    """
    Generate a brief one-line summary of the session.
    
    Args:
        session: BootstrapSession object
        
    Returns:
        Brief summary string
    """
    stats = session.get_summary_stats()
    return (f"Proved {stats['success']}/{stats['total']} theorems "
            f"({_percentage(stats['success'], stats['total'])}) "
            f"in {_format_duration(session.start_time, datetime.now())}")


def export_results_json(session: Any, filepath: str) -> None:
    """
    Export session results to JSON format for further analysis.
    
    Args:
        session: BootstrapSession object
        filepath: Path to write JSON file
    """
    import json
    
    data = {
        'start_time': session.start_time.isoformat(),
        'config': {
            'max_proof_sec': session.config.max_proof_sec
        },
        'summary': session.get_summary_stats(),
        'results': [
            {
                'theorem_name': r.theorem_name,
                'status': r.status,
                'steps_taken': r.steps_taken,
                'time_seconds': r.time_seconds,
                'error_message': r.error_message,
                'responsible_heuristic': r.responsible_heuristic
            }
            for r in session.results
        ]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)