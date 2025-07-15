"""
Parse CLI - Command-line interface for code parsing and analysis.

This module provides CLI commands for parsing and analyzing code files.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List
import json

# Import from new structure
from ..api.analysis_api import AnalysisAPI
from tier2.computer_science.cfg import build_cfg


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegionAI Code Parser CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a Python file and show CFG
  regionai-parse file.py --cfg
  
  # Analyze with specific domain
  regionai-parse file.py --analyze --domain range
  
  # Check safety properties
  regionai-parse file.py --check-safety
  
  # Get code metrics
  regionai-parse file.py --metrics
"""
    )
    
    # Main argument
    parser.add_argument(
        "file",
        type=Path,
        help="Python file to parse"
    )
    
    # Analysis options
    parser.add_argument(
        "--cfg",
        action="store_true",
        help="Generate control flow graph"
    )
    
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run full analysis"
    )
    
    parser.add_argument(
        "--domain",
        choices=["sign", "range", "nullability"],
        default="sign",
        help="Abstract domain for analysis"
    )
    
    parser.add_argument(
        "--check-safety",
        action="store_true",
        help="Check safety properties"
    )
    
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Calculate code metrics"
    )
    
    parser.add_argument(
        "--patterns",
        action="store_true",
        help="Detect code patterns"
    )
    
    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: stdout)"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json", "dot"],
        default="text",
        help="Output format"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check file exists
    if not args.file.exists():
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        sys.exit(1)
        
    # Read file
    try:
        code = args.file.read_text()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Initialize API
    api = AnalysisAPI()
    
    # Determine what analyses to run
    if not any([args.cfg, args.analyze, args.check_safety, args.metrics, args.patterns]):
        # Default to showing CFG
        args.cfg = True
        
    results = {}
    
    # Run requested analyses
    if args.cfg or args.analyze:
        analyses = []
        if args.cfg:
            analyses.append("cfg")
        if args.analyze:
            analyses.extend(["cfg", "fixpoint", "alias"])
            
        analysis_result = api.analyze_code(
            code,
            analyses=analyses,
            options={"fixpoint": {"domain": args.domain}}
        )
        
        if not analysis_result.success:
            print(f"Analysis failed: {analysis_result.errors}", file=sys.stderr)
            sys.exit(1)
            
        results["analysis"] = analysis_result.to_dict()
        
    if args.check_safety:
        safety_results = api.check_safety(code)
        results["safety"] = safety_results
        
    if args.metrics:
        metrics = api.get_metrics(code)
        results["metrics"] = metrics
        
    if args.patterns:
        patterns = api.detect_patterns(code)
        results["patterns"] = patterns
        
    # Format output
    output = format_results(results, args.format, args.verbose)
    
    # Write output
    if args.output:
        try:
            args.output.write_text(output)
            if args.verbose:
                print(f"Output written to {args.output}")
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


def format_results(results: dict, format: str, verbose: bool) -> str:
    """Format analysis results."""
    if format == "json":
        return json.dumps(results, indent=2)
        
    elif format == "dot":
        # Generate DOT format for CFG
        if "analysis" in results and results["analysis"].get("cfg"):
            return cfg_to_dot(results["analysis"]["cfg"])
        else:
            return "// No CFG available"
            
    else:  # text format
        lines = []
        
        if "analysis" in results:
            analysis = results["analysis"]
            lines.append("=== Analysis Results ===")
            
            if analysis.get("cfg"):
                lines.append(f"Functions: {len(analysis['cfg']['functions'])}")
                
            if analysis.get("fixpoint_results"):
                lines.append("\nFixpoint Analysis:")
                for func, result in analysis["fixpoint_results"].items():
                    lines.append(f"  {func}: {len(result)} states")
                    
            if analysis.get("warnings"):
                lines.append(f"\nWarnings: {len(analysis['warnings'])}")
                if verbose:
                    for warning in analysis["warnings"]:
                        lines.append(f"  - {warning}")
                        
        if "safety" in results:
            safety = results["safety"]
            lines.append("\n=== Safety Check ===")
            lines.append(f"Safe: {safety['safe']}")
            if safety.get("violations"):
                lines.append(f"Violations: {len(safety['violations'])}")
                if verbose:
                    for violation in safety["violations"]:
                        lines.append(f"  - {violation['property']}: {violation['description']}")
                        
        if "metrics" in results:
            metrics = results["metrics"]
            lines.append("\n=== Code Metrics ===")
            lines.append(f"Lines of code: {metrics['lines_of_code']}")
            lines.append(f"Functions: {metrics['functions']}")
            lines.append(f"Classes: {metrics['classes']}")
            if metrics.get("average_complexity"):
                lines.append(f"Average complexity: {metrics['average_complexity']:.2f}")
                
        if "patterns" in results:
            patterns = results["patterns"]
            lines.append(f"\n=== Patterns Detected ===")
            lines.append(f"Total: {len(patterns)}")
            if verbose and patterns:
                for pattern in patterns[:10]:  # Show first 10
                    lines.append(f"  - {pattern['pattern']} at line {pattern.get('line', '?')}")
                    
        return "\n".join(lines)


def cfg_to_dot(cfg: dict) -> str:
    """Convert CFG to DOT format."""
    lines = ["digraph CFG {"]
    lines.append('  node [shape=box];')
    
    for func_name, func_data in cfg.get("functions", {}).items():
        lines.append(f'  subgraph cluster_{func_name} {{')
        lines.append(f'    label="{func_name}";')
        
        # Add nodes
        for block_id, block in func_data.get("blocks", {}).items():
            label = f"{block_id}"
            if block.get("statements"):
                # Show first statement
                label += f"\\n{str(block['statements'][0])[:20]}..."
            lines.append(f'    "{func_name}_{block_id}" [label="{label}"];')
            
        # Add edges
        for block_id, block in func_data.get("blocks", {}).items():
            for succ in block.get("successors", []):
                lines.append(f'    "{func_name}_{block_id}" -> "{func_name}_{succ}";')
                
        lines.append("  }")
        
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()