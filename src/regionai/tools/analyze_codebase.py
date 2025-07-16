"""
Analyze Codebase - Tool for analyzing entire codebases.

This module provides functionality to analyze multiple files and
generate comprehensive reports.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Import from new structure
from ..api.analysis_api import AnalysisAPI
from ..api.knowledge_api import KnowledgeAPI


class CodebaseAnalyzer:
    """Analyzes entire codebases."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.analysis_api = AnalysisAPI(config)
        self.knowledge_api = KnowledgeAPI(config)
        self.results = defaultdict(dict)
        
    def analyze_codebase(self, root_path: Path,
                        file_pattern: str = "*.py",
                        analyses: Optional[List[str]] = None,
                        parallel: bool = True,
                        max_workers: int = 4) -> Dict[str, Any]:
        """
        Analyze all matching files in a codebase.
        
        Args:
            root_path: Root directory to analyze
            file_pattern: File pattern to match
            analyses: Analyses to run
            parallel: Use parallel processing
            max_workers: Maximum parallel workers
            
        Returns:
            Codebase analysis results
        """
        # Find all matching files
        files = list(root_path.rglob(file_pattern))
        
        if not files:
            return {
                "error": f"No files matching '{file_pattern}' found in {root_path}"
            }
            
        print(f"Found {len(files)} files to analyze")
        
        start_time = time.time()
        
        if parallel and len(files) > 1:
            # Parallel analysis
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(
                        self._analyze_file, file, analyses
                    ): file for file in files
                }
                
                for future in as_completed(future_to_file):
                    file = future_to_file[future]
                    try:
                        result = future.result()
                        self.results[str(file)] = result
                        print(f"✓ Analyzed {file.name}")
                    except Exception as e:
                        print(f"✗ Failed {file.name}: {e}")
                        self.results[str(file)] = {"error": str(e)}
        else:
            # Sequential analysis
            for file in files:
                try:
                    result = self._analyze_file(file, analyses)
                    self.results[str(file)] = result
                    print(f"✓ Analyzed {file.name}")
                except Exception as e:
                    print(f"✗ Failed {file.name}: {e}")
                    self.results[str(file)] = {"error": str(e)}
                    
        end_time = time.time()
        
        # Generate summary
        summary = self._generate_summary(len(files), end_time - start_time)
        
        return {
            "summary": summary,
            "files": dict(self.results)
        }
        
    def _analyze_file(self, file_path: Path,
                     analyses: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze a single file."""
        code = file_path.read_text()
        
        # Run analysis
        result = self.analysis_api.analyze_code(
            code,
            analyses=analyses
        )
        
        # Extract knowledge
        knowledge_result = self.knowledge_api.learn_from_text(
            code,
            source=str(file_path)
        )
        
        # Get metrics
        metrics = self.analysis_api.get_metrics(code)
        
        return {
            "analysis": result.to_dict() if result.success else None,
            "metrics": metrics,
            "knowledge_extracted": knowledge_result.get("facts_added", 0),
            "size": len(code),
            "lines": code.count('\n') + 1
        }
        
    def _generate_summary(self, total_files: int,
                         elapsed_time: float) -> Dict[str, Any]:
        """Generate codebase summary."""
        successful = sum(
            1 for r in self.results.values()
            if "error" not in r
        )
        
        # Aggregate metrics
        total_lines = 0
        total_functions = 0
        total_classes = 0
        total_complexity = 0
        complexity_count = 0
        
        safety_issues = []
        patterns_found = defaultdict(int)
        
        for file_path, result in self.results.items():
            if "error" in result:
                continue
                
            if "metrics" in result:
                metrics = result["metrics"]
                total_lines += metrics.get("lines_of_code", 0)
                total_functions += metrics.get("functions", 0)
                total_classes += metrics.get("classes", 0)
                
                if "average_complexity" in metrics:
                    total_complexity += metrics["average_complexity"]
                    complexity_count += 1
                    
            if "analysis" in result and result["analysis"]:
                analysis = result["analysis"]
                
                # Collect safety issues
                if "errors" in analysis:
                    for error in analysis["errors"]:
                        safety_issues.append({
                            "file": Path(file_path).name,
                            "issue": error
                        })
                        
        average_complexity = (
            total_complexity / complexity_count
            if complexity_count > 0 else 0
        )
        
        return {
            "files_analyzed": successful,
            "files_failed": total_files - successful,
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "average_complexity": round(average_complexity, 2),
            "analysis_time": round(elapsed_time, 2),
            "files_per_second": round(total_files / elapsed_time, 2),
            "safety_issues": len(safety_issues),
            "top_issues": safety_issues[:5]  # Top 5 issues
        }
        
    def generate_report(self, output_format: str = "text") -> str:
        """Generate analysis report."""
        if not self.results:
            return "No analysis results available"
            
        if output_format == "json":
            return json.dumps(dict(self.results), indent=2)
            
        elif output_format == "html":
            return self._generate_html_report()
            
        else:  # text format
            return self._generate_text_report()
            
    def _generate_text_report(self) -> str:
        """Generate text format report."""
        lines = ["=== Codebase Analysis Report ===\n"]
        
        # Summary section
        summary = self._generate_summary(len(self.results), 0)
        
        lines.append(f"Files analyzed: {summary['files_analyzed']}")
        lines.append(f"Files failed: {summary['files_failed']}")
        lines.append(f"Total lines: {summary['total_lines']:,}")
        lines.append(f"Total functions: {summary['total_functions']}")
        lines.append(f"Total classes: {summary['total_classes']}")
        lines.append(f"Average complexity: {summary['average_complexity']}")
        
        if summary['safety_issues'] > 0:
            lines.append(f"\n⚠️  Safety Issues: {summary['safety_issues']}")
            for issue in summary['top_issues']:
                lines.append(f"  - {issue['file']}: {issue['issue']}")
                
        # Per-file details
        lines.append("\n=== File Details ===")
        
        for file_path, result in sorted(self.results.items()):
            file_name = Path(file_path).name
            
            if "error" in result:
                lines.append(f"\n{file_name}: ERROR - {result['error']}")
            else:
                lines.append(f"\n{file_name}:")
                lines.append(f"  Lines: {result.get('lines', 0)}")
                
                if "metrics" in result:
                    metrics = result["metrics"]
                    lines.append(f"  Functions: {metrics.get('functions', 0)}")
                    lines.append(f"  Classes: {metrics.get('classes', 0)}")
                    
                    if "average_complexity" in metrics:
                        lines.append(f"  Avg complexity: {metrics['average_complexity']:.2f}")
                        
        return "\n".join(lines)
        
    def _generate_html_report(self) -> str:
        """Generate HTML format report."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Codebase Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f0f0f0; padding: 15px; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }
        .error { color: red; }
        .warning { color: orange; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Codebase Analysis Report</h1>
"""
        
        # Summary
        summary = self._generate_summary(len(self.results), 0)
        
        html += '<div class="summary">'
        html += f'<div class="metric">Files Analyzed: <strong>{summary["files_analyzed"]}</strong></div>'
        html += f'<div class="metric">Total Lines: <strong>{summary["total_lines"]:,}</strong></div>'
        html += f'<div class="metric">Functions: <strong>{summary["total_functions"]}</strong></div>'
        html += f'<div class="metric">Classes: <strong>{summary["total_classes"]}</strong></div>'
        html += f'<div class="metric">Avg Complexity: <strong>{summary["average_complexity"]}</strong></div>'
        
        if summary["safety_issues"] > 0:
            html += f'<div class="metric warning">⚠️ Safety Issues: <strong>{summary["safety_issues"]}</strong></div>'
            
        html += '</div>'
        
        # File details table
        html += '<h2>File Details</h2>'
        html += '<table>'
        html += '<tr><th>File</th><th>Lines</th><th>Functions</th><th>Classes</th><th>Complexity</th><th>Status</th></tr>'
        
        for file_path, result in sorted(self.results.items()):
            file_name = Path(file_path).name
            
            if "error" in result:
                html += f'<tr>'
                html += f'<td>{file_name}</td>'
                html += f'<td colspan="4" class="error">Error: {result["error"]}</td>'
                html += f'<td class="error">Failed</td>'
                html += f'</tr>'
            else:
                metrics = result.get("metrics", {})
                html += f'<tr>'
                html += f'<td>{file_name}</td>'
                html += f'<td>{result.get("lines", 0)}</td>'
                html += f'<td>{metrics.get("functions", 0)}</td>'
                html += f'<td>{metrics.get("classes", 0)}</td>'
                html += f'<td>{metrics.get("average_complexity", 0):.2f}</td>'
                html += f'<td>✓</td>'
                html += f'</tr>'
                
        html += '</table>'
        html += '</body></html>'
        
        return html


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze entire codebases with RegionAI"
    )
    
    parser.add_argument(
        "path",
        type=Path,
        help="Path to codebase root directory"
    )
    
    parser.add_argument(
        "--pattern",
        "-p",
        default="*.py",
        help="File pattern to analyze (default: *.py)"
    )
    
    parser.add_argument(
        "--analyses",
        "-a",
        nargs="+",
        choices=["cfg", "fixpoint", "alias", "safety", "metrics", "patterns"],
        help="Analyses to run (default: all)"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file for report"
    )
    
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "html"],
        default="text",
        help="Output format"
    )
    
    parser.add_argument(
        "--parallel",
        "-P",
        action="store_true",
        help="Use parallel processing"
    )
    
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check path exists
    if not args.path.exists():
        print(f"Error: Path '{args.path}' not found", file=sys.stderr)
        sys.exit(1)
        
    if not args.path.is_dir():
        print(f"Error: '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)
        
    # Create analyzer
    analyzer = CodebaseAnalyzer()
    
    # Run analysis
    print(f"Analyzing codebase at: {args.path}")
    print(f"File pattern: {args.pattern}")
    
    results = analyzer.analyze_codebase(
        args.path,
        file_pattern=args.pattern,
        analyses=args.analyses,
        parallel=args.parallel,
        max_workers=args.workers
    )
    
    # Generate report
    if "error" in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        sys.exit(1)
        
    report = analyzer.generate_report(args.format)
    
    # Output report
    if args.output:
        try:
            args.output.write_text(report)
            print(f"\nReport written to: {args.output}")
        except Exception as e:
            print(f"Error writing report: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n" + report)
        
    # Print summary
    summary = results["summary"]
    print(f"\n✓ Analysis complete: {summary['files_analyzed']} files in {summary['analysis_time']:.2f}s")
    
    if summary["safety_issues"] > 0:
        print(f"⚠️  Found {summary['safety_issues']} safety issues")
        sys.exit(2)  # Exit with warning code


if __name__ == "__main__":
    main()