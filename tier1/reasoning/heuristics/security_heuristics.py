"""
Security-focused heuristics for vulnerability detection.

This module contains heuristics that identify security vulnerabilities,
insecure configurations, and potential attack vectors in code.
"""
import ast
from typing import Dict, Optional, Any
import logging

from tier1.knowledge.infrastructure.hub_v1 import KnowledgeHub
from tier1.knowledge.infrastructure.reasoning_graph import FunctionArtifact
from tier1.knowledge.actions import FixSuggestion
from tier1.heuristic_registry import heuristic_registry

logger = logging.getLogger(__name__)


@heuristic_registry.register("security.check_insecure_ssl_config",
                           description="Check for insecure SSL/TLS configurations",
                           applicability_conditions=("security", "ssl", "vulnerability"),
                           expected_utility=0.95)
def check_insecure_ssl_config(hub: KnowledgeHub, context: Dict[str, Any]) -> Optional[FixSuggestion]:
    """
    Heuristic: Check for insecure SSL/TLS configurations.
    
    This heuristic looks for HTTP requests with SSL verification disabled
    (verify=False) and returns a FixSuggestion to fix the vulnerability.
    
    Args:
        hub: The KnowledgeHub containing both world and reasoning graphs
        context: Additional context including:
            - code: The source code to analyze
            - function_name: Name of the function being analyzed
            - function_artifact: The FunctionArtifact being analyzed
    
    Returns:
        FixSuggestion if vulnerability found, None otherwise
    """
    code = context.get('code', '')
    function_name = context.get('function_name', 'unknown')
    function_artifact = context.get('function_artifact')
    
    if not code:
        # No code provided, check if we have source_code in the artifact
        if function_artifact and hasattr(function_artifact, 'source_code') and function_artifact.source_code:
            code = function_artifact.source_code
        else:
            logger.warning("No code provided for check_insecure_ssl_config heuristic")
            return None
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        logger.error(f"Failed to parse code for {function_name}")
        return None
    
    # Look for insecure SSL configurations
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if this is an HTTP request call
            func_name = _get_call_name(node)
            if func_name and any(method in func_name for method in ['get', 'post', 'put', 'delete', 'request', 'send']):
                # Check for verify=False
                for keyword in node.keywords:
                    if keyword.arg == 'verify':
                        if (isinstance(keyword.value, ast.Constant) and 
                            keyword.value.value is False):
                            # Found insecure SSL configuration!
                            
                            # Create FunctionArtifact if not provided
                            if not function_artifact:
                                function_artifact = FunctionArtifact(
                                    function_name=function_name,
                                    file_path="unknown",
                                    source_code=code
                                )
                            
                            # Create and return FixSuggestion
                            return FixSuggestion(
                                vulnerability_id="INSECURE_SSL_VERIFICATION",
                                description=f"SSL verification is disabled in {func_name} call, making the connection vulnerable to MITM attacks",
                                target_artifact=function_artifact,
                                context_data={
                                    'parameter_name': 'verify',
                                    'safe_value': True,
                                    'function_call': func_name
                                }
                            )
    
    return None


def _get_call_name(node: ast.Call) -> Optional[str]:
    """Extract the function/method name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        # Handle chained calls like requests.get or self.session.post
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))
    return None