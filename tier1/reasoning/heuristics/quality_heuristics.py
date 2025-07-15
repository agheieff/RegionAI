"""
Quality-related heuristics for the RegionAI reasoning engine.

This module contains heuristics that analyze code quality aspects such as
documentation completeness and code complexity. These heuristics help identify
areas for improvement in code maintainability and readability.
"""
import ast
from typing import Dict, List, Any, Tuple, Set
import logging

from tier1.knowledge.infrastructure.hub_v1 import KnowledgeHub
from tier1.knowledge.discoveries import Discovery, Severity, FindingID
from tier1.knowledge.actions import FixSuggestion
from tier1.heuristic_registry import heuristic_registry

logger = logging.getLogger(__name__)

__all__ = [
    'documentation_checker',
    'complexity_analyzer',
    '_calculate_cyclomatic_complexity',
    '_calculate_cyclomatic_complexity_detailed',
    '_identify_extractable_blocks',
    '_analyze_block_variables',
    '_calculate_max_nesting_depth'
]


@heuristic_registry.register("DOCUMENTATION_CHECKER")
def documentation_checker(hub: KnowledgeHub, context: Dict[str, Any]) -> Any:
    """
    Real documentation analysis heuristic that identifies missing, incomplete,
    or unclear documentation in functions.
    
    Returns FixSuggestion for missing docstrings, Discovery objects for other issues.
    """
    function_artifact = context.get('function_artifact')
    if not function_artifact:
        return None
    
    code = function_artifact.source_code
    if not code:
        return None
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Invalid Python code
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing code for quality analysis: {e}")
        return None
    
    # Find the main function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for docstring
            docstring = ast.get_docstring(node)
            
            if not docstring:
                # Missing docstring - return FixSuggestion for automatic fix
                return FixSuggestion(
                    vulnerability_id='MISSING_DOCSTRING',
                    description=f"Function '{function_artifact.function_name}' has no docstring",
                    target_artifact=function_artifact,
                    context_data={
                        'line_number': node.lineno,
                        'function_name': node.name,
                        'parameters': [arg.arg for arg in node.args.args],
                        'has_return': any(isinstance(n, ast.Return) and n.value is not None 
                                        for n in ast.walk(node))
                    }
                )
            
            # Check docstring quality
            docstring_lines = docstring.strip().split('\n')
            
            # Check if it's too short/unclear
            if len(docstring_lines) == 1 and len(docstring) < 20:
                return Discovery(
                    finding_id=FindingID.UNCLEAR_DOCSTRING,
                    description=f"Function '{function_artifact.function_name}' has unclear/minimal docstring: '{docstring}'",
                    target_artifact=function_artifact,
                    severity=Severity.LOW,
                    metadata={
                        'line_number': node.lineno,
                        'docstring_length': len(docstring)
                    }
                )
            
            # Check for parameter documentation
            has_params = len(node.args.args) > 0
            has_param_docs = any('Args:' in line or 'Parameters:' in line or ':param' in line 
                               for line in docstring_lines)
            
            if has_params and not has_param_docs:
                param_names = [arg.arg for arg in node.args.args if arg.arg != 'self']
                if param_names:  # Only report if there are non-self parameters
                    return Discovery(
                        finding_id=FindingID.INCOMPLETE_PARAMETER_DOCS,
                        description=f"Function '{function_artifact.function_name}' has parameters {param_names} but no parameter documentation",
                        target_artifact=function_artifact,
                        severity=Severity.MEDIUM,
                        metadata={
                            'line_number': node.lineno,
                            'parameters': param_names
                        }
                    )
            
            # Check for return documentation if function returns something
            has_return = any(isinstance(n, ast.Return) and n.value is not None 
                           for n in ast.walk(node))
            has_return_docs = any('Returns:' in line or ':return:' in line 
                                for line in docstring_lines)
            
            if has_return and not has_return_docs:
                return Discovery(
                    finding_id=FindingID.MISSING_RETURN_DOC,
                    description=f"Function '{function_artifact.function_name}' returns a value but has no return documentation",
                    target_artifact=function_artifact,
                    severity=Severity.LOW,
                    metadata={
                        'line_number': node.lineno
                    }
                )
            
            break  # Only check the first function
    
    return None


@heuristic_registry.register("COMPLEXITY_ANALYZER",
                           description="Identify overly complex functions",
                           applicability_conditions=("complexity", "quality"),
                           expected_utility=0.85)
def complexity_analyzer(hub: KnowledgeHub, context: Dict[str, Any]) -> Any:
    """
    Enhanced complexity analysis heuristic that calculates cyclomatic complexity
    and identifies overly complex functions.
    
    Returns FixSuggestion for high complexity functions that can be refactored,
    or Discovery objects for other complexity issues.
    """
    function_artifact = context.get('function_artifact')
    if not function_artifact:
        return None
    
    code = function_artifact.source_code
    if not code:
        return None
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Invalid Python code
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing code for quality analysis: {e}")
        return None
    
    # Find the main function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Calculate cyclomatic complexity with detailed analysis
            complexity, complexity_nodes = _calculate_cyclomatic_complexity_detailed(node)
            
            # Count lines
            line_count = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
            
            # Count parameters
            param_count = len(node.args.args)
            
            # Check for high complexity - now returns FixSuggestion
            if complexity > 10:
                # Identify the most complex blocks for potential extraction
                extractable_blocks = _identify_extractable_blocks(node, complexity_nodes)
                
                return FixSuggestion(
                    vulnerability_id='HIGH_COMPLEXITY',
                    description=f"Function '{function_artifact.function_name}' has high cyclomatic complexity: {complexity}",
                    target_artifact=function_artifact,
                    context_data={
                        'complexity': complexity,
                        'line_number': node.lineno,
                        'threshold': 10,
                        'complexity_nodes': complexity_nodes,
                        'extractable_blocks': extractable_blocks,
                        'function_ast': node  # Include the AST for the decomposer
                    }
                )
            
            # Check for long functions
            if line_count > 50:
                severity = Severity.MEDIUM if line_count > 100 else Severity.LOW
                return Discovery(
                    finding_id=FindingID.LONG_FUNCTION,
                    description=f"Function '{function_artifact.function_name}' is too long: {line_count} lines",
                    target_artifact=function_artifact,
                    severity=severity,
                    metadata={
                        'line_count': line_count,
                        'line_number': node.lineno,
                        'threshold': 50
                    }
                )
            
            # Check for too many parameters
            if param_count > 5:
                severity = Severity.MEDIUM if param_count > 7 else Severity.LOW
                param_names = [arg.arg for arg in node.args.args]
                return Discovery(
                    finding_id=FindingID.TOO_MANY_PARAMETERS,
                    description=f"Function '{function_artifact.function_name}' has too many parameters: {param_count}",
                    target_artifact=function_artifact,
                    severity=severity,
                    metadata={
                        'param_count': param_count,
                        'param_names': param_names,
                        'line_number': node.lineno,
                        'threshold': 5
                    }
                )
            
            # Check for deep nesting
            max_depth = _calculate_max_nesting_depth(node)
            if max_depth > 3:
                severity = Severity.MEDIUM if max_depth > 4 else Severity.LOW
                return Discovery(
                    finding_id=FindingID.DEEPLY_NESTED_CODE,
                    description=f"Function '{function_artifact.function_name}' has deeply nested code: max depth {max_depth}",
                    target_artifact=function_artifact,
                    severity=severity,
                    metadata={
                        'max_depth': max_depth,
                        'line_number': node.lineno,
                        'threshold': 3
                    }
                )
            
            break  # Only check the first function
    
    return None


def _calculate_cyclomatic_complexity(node: ast.FunctionDef) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1  # Base complexity
    
    # Walk through all nodes in the function
    for child in ast.walk(node):
        # Decision points increase complexity
        if isinstance(child, (ast.If, ast.While, ast.For)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each and/or adds a branch
            complexity += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            # List/dict/set comprehensions with conditions
            complexity += len(child.ifs)
    
    return complexity


def _calculate_cyclomatic_complexity_detailed(node: ast.FunctionDef) -> Tuple[int, List[Dict[str, Any]]]:
    """Calculate cyclomatic complexity with detailed node information."""
    complexity = 1  # Base complexity
    complexity_nodes = []
    
    # Walk through all nodes in the function
    for child in ast.walk(node):
        # Decision points increase complexity
        if isinstance(child, ast.If):
            complexity += 1
            complexity_nodes.append({
                'type': 'if',
                'node': child,
                'line': child.lineno if hasattr(child, 'lineno') else None,
                'contribution': 1
            })
        elif isinstance(child, ast.While):
            complexity += 1
            complexity_nodes.append({
                'type': 'while',
                'node': child,
                'line': child.lineno if hasattr(child, 'lineno') else None,
                'contribution': 1
            })
        elif isinstance(child, ast.For):
            complexity += 1
            complexity_nodes.append({
                'type': 'for',
                'node': child,
                'line': child.lineno if hasattr(child, 'lineno') else None,
                'contribution': 1
            })
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
            complexity_nodes.append({
                'type': 'except',
                'node': child,
                'line': child.lineno if hasattr(child, 'lineno') else None,
                'contribution': 1
            })
        elif isinstance(child, ast.BoolOp):
            # Each and/or adds a branch
            contribution = len(child.values) - 1
            complexity += contribution
            complexity_nodes.append({
                'type': 'boolop',
                'node': child,
                'line': child.lineno if hasattr(child, 'lineno') else None,
                'contribution': contribution
            })
        elif isinstance(child, ast.comprehension):
            # List/dict/set comprehensions with conditions
            contribution = len(child.ifs)
            if contribution > 0:
                complexity += contribution
                complexity_nodes.append({
                    'type': 'comprehension',
                    'node': child,
                    'line': None,  # Comprehensions don't have line numbers
                    'contribution': contribution
                })
    
    return complexity, complexity_nodes


def _identify_extractable_blocks(func_node: ast.FunctionDef, complexity_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify blocks of code that can be extracted into helper methods."""
    extractable_blocks = []
    
    # Look for large if/for/while blocks that contribute to complexity
    for item in complexity_nodes:
        node = item['node']
        
        # Check if this is a substantial block worth extracting
        if isinstance(node, (ast.If, ast.For, ast.While)):
            # Count the lines in this block
            if hasattr(node, 'body') and len(node.body) > 3:  # More than 3 statements
                # Analyze variable usage in this block
                used_vars, assigned_vars = _analyze_block_variables(node)
                
                extractable_blocks.append({
                    'node': node,
                    'type': item['type'],
                    'line': item['line'],
                    'size': len(node.body),
                    'used_variables': used_vars,
                    'assigned_variables': assigned_vars,
                    'complexity_contribution': item['contribution']
                })
    
    # Sort by size and complexity contribution to prioritize extraction
    extractable_blocks.sort(key=lambda x: (x['size'], x['complexity_contribution']), reverse=True)
    
    return extractable_blocks


def _analyze_block_variables(node: ast.AST) -> Tuple[Set[str], Set[str]]:
    """Analyze which variables are used and assigned in a block."""
    used_vars = set()
    assigned_vars = set()
    
    class VariableAnalyzer(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used_vars.add(node.id)
            elif isinstance(node.ctx, ast.Store):
                assigned_vars.add(node.id)
            self.generic_visit(node)
        
        def visit_FunctionDef(self, node):
            # Don't analyze nested function definitions
            pass
        
        def visit_ClassDef(self, node):
            # Don't analyze nested class definitions
            pass
    
    analyzer = VariableAnalyzer()
    analyzer.visit(node)
    
    # Remove variables that are both used and assigned (likely local to the block)
    # But keep them in used_vars as they might need initial values
    return used_vars, assigned_vars


def _calculate_max_nesting_depth(node: ast.FunctionDef, current_depth: int = 0) -> int:
    """Calculate maximum nesting depth in a function."""
    max_depth = current_depth
    
    for child in ast.iter_child_nodes(node):
        child_depth = current_depth
        
        # These nodes increase nesting depth
        if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
            child_depth += 1
        
        # Recursively check children
        if hasattr(child, 'body'):
            for body_node in child.body:
                depth = _calculate_max_nesting_depth(body_node, child_depth)
                max_depth = max(max_depth, depth)
        
        if hasattr(child, 'orelse'):
            for else_node in child.orelse:
                depth = _calculate_max_nesting_depth(else_node, child_depth)
                max_depth = max(max_depth, depth)
        
        if hasattr(child, 'finalbody'):
            for final_node in child.finalbody:
                depth = _calculate_max_nesting_depth(final_node, child_depth)
                max_depth = max(max_depth, depth)
    
    return max_depth