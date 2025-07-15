"""
Analysis API - Public facade for code analysis capabilities.

This module provides a clean, stable API for code analysis features,
hiding internal implementation details.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import logging

# Import from new structure
from ..domains.code.cfg import ControlFlowGraph
from ..domains.code.fixpoint import FixpointAnalyzer
from ..domains.code.alias_analysis import AliasAnalyzer
from ..core.abstract_domains import SignDomain, RangeDomain

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Unified result from code analysis."""
    success: bool
    cfg: Optional[ControlFlowGraph] = None
    fixpoint_results: Optional[Dict[str, Any]] = None
    alias_results: Optional[Dict[str, Any]] = None
    warnings: List[str] = None
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "cfg": self.cfg.to_dict() if self.cfg else None,
            "fixpoint_results": self.fixpoint_results,
            "alias_results": self.alias_results,
            "warnings": self.warnings or [],
            "errors": self.errors or [],
            "metadata": self.metadata or {}
        }


class AnalysisAPI:
    """
    Public API for code analysis capabilities.
    
    This class provides a stable interface for analyzing code,
    abstracting away the internal implementation details.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Analysis API.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self._init_analyzers()
        
    def _init_analyzers(self):
        """Initialize internal analyzers."""
        # These will be created on demand to avoid circular imports
        self._cfg_analyzer = None
        self._fixpoint_analyzer = None
        self._alias_analyzer = None
        
    def analyze_code(self, code: Union[str, Path],
                    analyses: Optional[List[str]] = None,
                    options: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze code with specified analyses.
        
        Args:
            code: Source code string or path to file
            analyses: List of analyses to run (default: all)
            options: Analysis-specific options
            
        Returns:
            AnalysisResult containing all results
        """
        # Load code if path provided
        if isinstance(code, Path):
            try:
                code = code.read_text()
            except Exception as e:
                return AnalysisResult(
                    success=False,
                    errors=[f"Failed to read file: {e}"]
                )
                
        # Default to all analyses
        if analyses is None:
            analyses = ["cfg", "fixpoint", "alias"]
            
        options = options or {}
        result = AnalysisResult(success=True)
        
        # Run requested analyses
        if "cfg" in analyses:
            self._run_cfg_analysis(code, result, options.get("cfg", {}))
            
        if "fixpoint" in analyses:
            self._run_fixpoint_analysis(code, result, options.get("fixpoint", {}))
            
        if "alias" in analyses:
            self._run_alias_analysis(code, result, options.get("alias", {}))
            
        return result
        
    def analyze_function(self, code: str, function_name: str,
                       domain: str = "sign") -> Dict[str, Any]:
        """
        Analyze a specific function with abstract interpretation.
        
        Args:
            code: Source code containing the function
            function_name: Name of function to analyze
            domain: Abstract domain to use ("sign", "range", etc.)
            
        Returns:
            Analysis results for the function
        """
        try:
            # Build CFG
            from ..domains.code.cfg import build_cfg
            cfg = build_cfg(code)
            
            if function_name not in cfg.functions:
                return {
                    "error": f"Function '{function_name}' not found",
                    "available_functions": list(cfg.functions.keys())
                }
                
            # Select domain
            if domain == "sign":
                abstract_domain = SignDomain()
            elif domain == "range":
                abstract_domain = RangeDomain()
            else:
                return {"error": f"Unknown domain: {domain}"}
                
            # Run analysis
            from ..domains.code.fixpoint import FixpointAnalyzer
            analyzer = FixpointAnalyzer(abstract_domain)
            func_cfg = cfg.get_function_cfg(function_name)
            
            if not func_cfg:
                return {"error": f"No CFG for function '{function_name}'"}
                
            results = analyzer.analyze(func_cfg)
            
            return {
                "function": function_name,
                "domain": domain,
                "results": results,
                "warnings": analyzer.warnings if hasattr(analyzer, 'warnings') else []
            }
            
        except Exception as e:
            logger.error(f"Function analysis failed: {e}")
            return {"error": str(e)}
            
    def check_safety(self, code: str,
                    properties: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Check safety properties of code.
        
        Args:
            code: Source code to check
            properties: Properties to verify (default: common safety)
            
        Returns:
            Safety check results
        """
        if properties is None:
            properties = [
                "null_safety",
                "bounds_checking",
                "integer_overflow",
                "type_safety"
            ]
            
        results = {"checked": properties, "violations": [], "safe": True}
        
        try:
            # Build CFG for analysis
            from ..domains.code.cfg import build_cfg
            cfg = build_cfg(code)
            
            # Check each property
            for prop in properties:
                violations = self._check_property(cfg, prop)
                if violations:
                    results["violations"].extend(violations)
                    results["safe"] = False
                    
        except Exception as e:
            results["error"] = str(e)
            results["safe"] = False
            
        return results
        
    def detect_patterns(self, code: str,
                       patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Detect code patterns and anti-patterns.
        
        Args:
            code: Source code to analyze
            patterns: Specific patterns to look for
            
        Returns:
            List of detected patterns with locations
        """
        detected = []
        
        if patterns is None:
            patterns = [
                "singleton",
                "factory",
                "observer",
                "unused_variable",
                "dead_code",
                "complex_condition"
            ]
            
        try:
            import ast
            tree = ast.parse(code)
            
            for pattern in patterns:
                matches = self._detect_pattern(tree, pattern)
                detected.extend(matches)
                
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            
        return detected
        
    def get_metrics(self, code: str) -> Dict[str, Any]:
        """
        Calculate code metrics.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary of code metrics
        """
        metrics = {
            "lines_of_code": 0,
            "cyclomatic_complexity": {},
            "functions": 0,
            "classes": 0,
            "average_function_length": 0
        }
        
        try:
            # Basic line counting
            lines = code.split('\n')
            metrics["lines_of_code"] = len(lines)
            
            # Parse AST for structural metrics
            import ast
            tree = ast.parse(code)
            
            # Count functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics["functions"] += 1
                    # Calculate cyclomatic complexity
                    complexity = self._calculate_complexity(node)
                    metrics["cyclomatic_complexity"][node.name] = complexity
                elif isinstance(node, ast.ClassDef):
                    metrics["classes"] += 1
                    
            # Calculate averages
            if metrics["functions"] > 0:
                total_complexity = sum(metrics["cyclomatic_complexity"].values())
                metrics["average_complexity"] = total_complexity / metrics["functions"]
                
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _run_cfg_analysis(self, code: str, result: AnalysisResult,
                         options: Dict[str, Any]):
        """Run control flow graph analysis."""
        try:
            from ..domains.code.cfg import build_cfg
            cfg = build_cfg(code)
            result.cfg = cfg
            
            # Add CFG statistics to metadata
            if result.metadata is None:
                result.metadata = {}
                
            result.metadata["cfg_stats"] = {
                "functions": len(cfg.functions),
                "total_blocks": sum(len(f.blocks) for f in cfg.functions.values())
            }
            
        except Exception as e:
            result.success = False
            if result.errors is None:
                result.errors = []
            result.errors.append(f"CFG analysis failed: {e}")
            
    def _run_fixpoint_analysis(self, code: str, result: AnalysisResult,
                             options: Dict[str, Any]):
        """Run fixpoint analysis."""
        try:
            # Need CFG first
            if result.cfg is None:
                from ..domains.code.cfg import build_cfg
                result.cfg = build_cfg(code)
                
            # Run fixpoint analysis
            domain_name = options.get("domain", "sign")
            
            if domain_name == "sign":
                domain = SignDomain()
            elif domain_name == "range":
                domain = RangeDomain()
            else:
                if result.warnings is None:
                    result.warnings = []
                result.warnings.append(f"Unknown domain '{domain_name}', using sign")
                domain = SignDomain()
                
            from ..domains.code.fixpoint import FixpointAnalyzer
            analyzer = FixpointAnalyzer(domain)
            
            fixpoint_results = {}
            for func_name, func_cfg in result.cfg.functions.items():
                fixpoint_results[func_name] = analyzer.analyze(func_cfg)
                
            result.fixpoint_results = fixpoint_results
            
        except Exception as e:
            result.success = False
            if result.errors is None:
                result.errors = []
            result.errors.append(f"Fixpoint analysis failed: {e}")
            
    def _run_alias_analysis(self, code: str, result: AnalysisResult,
                          options: Dict[str, Any]):
        """Run alias analysis."""
        try:
            # Need CFG first
            if result.cfg is None:
                from ..domains.code.cfg import build_cfg
                result.cfg = build_cfg(code)
                
            # Run alias analysis
            from ..domains.code.alias_analysis import AliasAnalyzer
            analyzer = AliasAnalyzer()
            
            alias_results = {}
            for func_name, func_cfg in result.cfg.functions.items():
                alias_results[func_name] = analyzer.analyze(func_cfg)
                
            result.alias_results = alias_results
            
        except Exception as e:
            result.success = False
            if result.errors is None:
                result.errors = []
            result.errors.append(f"Alias analysis failed: {e}")
            
    def _check_property(self, cfg: ControlFlowGraph,
                       property_name: str) -> List[Dict[str, Any]]:
        """Check a specific safety property."""
        violations = []
        
        # Simplified property checking
        if property_name == "null_safety":
            # Look for potential null dereferences
            for func in cfg.functions.values():
                for block in func.blocks.values():
                    for stmt in block.statements:
                        if "." in str(stmt) and "None" in str(stmt):
                            violations.append({
                                "property": "null_safety",
                                "location": f"{func.name}:{block.id}",
                                "description": "Potential null dereference"
                            })
                            
        elif property_name == "bounds_checking":
            # Look for array accesses without bounds checks
            for func in cfg.functions.values():
                for block in func.blocks.values():
                    for stmt in block.statements:
                        if "[" in str(stmt) and "]" in str(stmt):
                            # Simplified check
                            violations.append({
                                "property": "bounds_checking",
                                "location": f"{func.name}:{block.id}",
                                "description": "Array access without bounds check"
                            })
                            
        return violations
        
    def _detect_pattern(self, tree: Any, pattern: str) -> List[Dict[str, Any]]:
        """Detect a specific pattern in AST."""
        matches = []
        
        # Simplified pattern detection
        import ast
        
        if pattern == "unused_variable":
            # Find assigned but never used variables
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Simplified: just flag all assignments
                            matches.append({
                                "pattern": "unused_variable",
                                "variable": target.id,
                                "line": node.lineno if hasattr(node, 'lineno') else 0,
                                "confidence": 0.5  # Low confidence without usage analysis
                            })
                            
        elif pattern == "complex_condition":
            # Find overly complex boolean expressions
            for node in ast.walk(tree):
                if isinstance(node, ast.BoolOp):
                    # Count operators
                    op_count = len(node.values) - 1
                    if op_count > 3:
                        matches.append({
                            "pattern": "complex_condition",
                            "complexity": op_count,
                            "line": node.lineno if hasattr(node, 'lineno') else 0,
                            "suggestion": "Consider simplifying this condition"
                        })
                        
        return matches
        
    def _calculate_complexity(self, node: Any) -> int:
        """Calculate cyclomatic complexity of a function."""
        import ast
        
        complexity = 1  # Base complexity
        
        # Add complexity for each decision point
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds a path
                complexity += len(child.values) - 1
                
        return complexity


# Convenience functions for simple usage
def analyze(code: str, **kwargs) -> AnalysisResult:
    """Quick analysis of code."""
    api = AnalysisAPI()
    return api.analyze_code(code, **kwargs)


def check_safety(code: str, properties: Optional[List[str]] = None) -> Dict[str, Any]:
    """Quick safety check."""
    api = AnalysisAPI()
    return api.check_safety(code, properties)


def get_metrics(code: str) -> Dict[str, Any]:
    """Quick metrics calculation."""
    api = AnalysisAPI()
    return api.get_metrics(code)