#!/usr/bin/env python3
"""
Test the CodeGenerator service for autonomous fix creation.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import ast
from regionai.actions.code_generator import CodeGenerator, SslFixerTransformer
from tier2.knowledge.actions import FixSuggestion
from tier3.world_contexts.knowledge.models import FunctionArtifact


def test_fix_suggestion_creation():
    """Test creating FixSuggestion objects."""
    artifact = FunctionArtifact(
        function_name="test_func",
        file_path="test.py",
        source_code="def test_func(): pass"
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="TEST_VULN",
        description="Test vulnerability",
        target_artifact=artifact,
        context_data={"key": "value"}
    )
    
    assert suggestion.vulnerability_id == "TEST_VULN"
    assert suggestion.description == "Test vulnerability"
    assert suggestion.target_artifact == artifact
    assert suggestion.context_data == {"key": "value"}
    
    # Test validation
    with pytest.raises(ValueError, match="must have a vulnerability_id"):
        FixSuggestion("", "desc", artifact)
    
    with pytest.raises(ValueError, match="must have a description"):
        FixSuggestion("ID", "", artifact)
    
    # Test missing source code
    artifact_no_code = FunctionArtifact("func", "file.py")
    with pytest.raises(ValueError, match="must have source code"):
        FixSuggestion("ID", "desc", artifact_no_code)


def test_ssl_fixer_transformer():
    """Test the SSL fixer transformer directly."""
    # Create a simple AST with verify=False
    code = """
def make_request(url):
    response = requests.get(url, verify=False)
    return response
"""
    tree = ast.parse(code)
    
    # Apply transformer
    transformer = SslFixerTransformer({})
    modified_tree = transformer.visit(tree)
    
    # Check that the transformer made changes
    assert len(transformer.changes_made) == 1
    assert "verify=False to verify=True" in transformer.changes_made[0]
    
    # Verify the AST was actually modified
    # Find the Call node
    for node in ast.walk(modified_tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == 'verify':
                    assert isinstance(keyword.value, ast.Constant)
                    assert keyword.value.value is True


def test_code_generator_ssl_fix():
    """Test the complete CodeGenerator fixing SSL verification."""
    generator = CodeGenerator()
    
    # Create a function with insecure SSL verification
    source_code = """
def fetch_data(api_url):
    '''Fetch data from the API endpoint.'''
    # Make request with SSL verification disabled
    response = requests.get(api_url, verify=False, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API error: {response.status_code}")
"""
    
    artifact = FunctionArtifact(
        function_name="fetch_data",
        file_path="api_client.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="INSECURE_SSL_VERIFICATION",
        description="SSL verification is disabled in requests.get call",
        target_artifact=artifact,
        context_data={'parameter_name': 'verify'}
    )
    
    # Generate the fix
    fixed_code = generator.generate_fix(suggestion)
    
    # Verify the fix
    assert "verify=True" in fixed_code or "verify = True" in fixed_code
    assert "verify=False" not in fixed_code and "verify = False" not in fixed_code
    
    # Parse the fixed code to ensure it's valid Python
    try:
        ast.parse(fixed_code)
    except SyntaxError:
        pytest.fail("Generated code is not valid Python")
    
    # Check that the function structure is preserved
    assert "def fetch_data(api_url):" in fixed_code
    assert "Fetch data from the API endpoint" in fixed_code
    assert "response.json()" in fixed_code


def test_multiple_ssl_issues_in_one_function():
    """Test fixing multiple SSL issues in a single function."""
    generator = CodeGenerator()
    
    source_code = """
def multi_request_function():
    # First request
    r1 = requests.get("https://api1.com", verify=False)
    
    # Second request
    r2 = session.post("https://api2.com", data=data, verify=False)
    
    # Third request with verify=True (should not be changed)
    r3 = requests.delete("https://api3.com", verify=True)
    
    return r1, r2, r3
"""
    
    artifact = FunctionArtifact(
        function_name="multi_request_function",
        file_path="multi_api.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="INSECURE_SSL_VERIFICATION",
        description="Multiple SSL verification disabled",
        target_artifact=artifact
    )
    
    fixed_code = generator.generate_fix(suggestion)
    
    # Count occurrences
    assert fixed_code.count("verify=True") >= 3 or fixed_code.count("verify = True") >= 3
    assert "verify=False" not in fixed_code and "verify = False" not in fixed_code
    
    # Verify the AST is valid
    ast.parse(fixed_code)


def test_nested_calls_with_ssl():
    """Test fixing SSL in nested function calls."""
    generator = CodeGenerator()
    
    source_code = """
def process_api_response(url):
    return json.loads(
        requests.get(
            url,
            headers={'Accept': 'application/json'},
            verify=False
        ).text
    )
"""
    
    artifact = FunctionArtifact(
        function_name="process_api_response",
        file_path="nested.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="INSECURE_SSL_VERIFICATION",
        description="SSL verification disabled in nested call",
        target_artifact=artifact
    )
    
    fixed_code = generator.generate_fix(suggestion)
    
    # Check the fix
    assert "verify=True" in fixed_code or "verify = True" in fixed_code
    assert "verify=False" not in fixed_code
    
    # Ensure structure is preserved
    assert "json.loads" in fixed_code
    assert "requests.get" in fixed_code


def test_unsupported_vulnerability_type():
    """Test handling of unsupported vulnerability types."""
    generator = CodeGenerator()
    
    artifact = FunctionArtifact(
        function_name="func",
        file_path="file.py",
        source_code="def func(): pass"
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="UNKNOWN_VULNERABILITY",
        description="Unknown issue",
        target_artifact=artifact
    )
    
    with pytest.raises(ValueError, match="No transformer available"):
        generator.generate_fix(suggestion)


def test_invalid_source_code():
    """Test handling of syntactically invalid source code."""
    generator = CodeGenerator()
    
    artifact = FunctionArtifact(
        function_name="bad_func",
        file_path="bad.py",
        source_code="def bad_func( invalid syntax here"
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="INSECURE_SSL_VERIFICATION",
        description="SSL issue",
        target_artifact=artifact
    )
    
    with pytest.raises(SyntaxError, match="Failed to parse source code"):
        generator.generate_fix(suggestion)


def test_docstring_generator():
    """Test the complete CodeGenerator adding missing docstrings."""
    generator = CodeGenerator()
    
    # Create a function without a docstring
    source_code = """
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    if count == 0:
        return 0
    return total / count
"""
    
    artifact = FunctionArtifact(
        function_name="calculate_average",
        file_path="math_utils.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="MISSING_DOCSTRING",
        description="Function 'calculate_average' has no docstring",
        target_artifact=artifact,
        context_data={
            'function_name': 'calculate_average',
            'parameters': ['numbers'],
            'has_return': True
        }
    )
    
    # Generate the fix
    fixed_code = generator.generate_fix(suggestion)
    
    # Verify the fix
    assert '"""TODO: Add a docstring.' in fixed_code
    assert 'Args:' in fixed_code
    assert 'numbers: TODO: Describe this parameter.' in fixed_code
    assert 'Returns:' in fixed_code
    assert 'TODO: Describe the return value.' in fixed_code
    
    # Parse the fixed code to ensure it's valid Python
    try:
        tree = ast.parse(fixed_code)
        # Find the function and verify it has a docstring
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'calculate_average':
                docstring = ast.get_docstring(node)
                assert docstring is not None
                assert 'TODO: Add a docstring' in docstring
    except SyntaxError:
        pytest.fail("Generated code is not valid Python")
    
    # Check that the function logic is preserved
    assert "total = sum(numbers)" in fixed_code
    assert "return total / count" in fixed_code


def test_docstring_generator_with_self_parameter():
    """Test docstring generation for methods with self parameter."""
    generator = CodeGenerator()
    
    source_code = """
def process_data(self, data, threshold=0.5):
    filtered = [x for x in data if x > threshold]
    return filtered
"""
    
    artifact = FunctionArtifact(
        function_name="process_data",
        file_path="processor.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="MISSING_DOCSTRING",
        description="Method 'process_data' has no docstring",
        target_artifact=artifact,
        context_data={
            'function_name': 'process_data',
            'parameters': ['self', 'data', 'threshold'],
            'has_return': True
        }
    )
    
    fixed_code = generator.generate_fix(suggestion)
    
    # Verify self is not included in parameter docs
    assert 'self: TODO' not in fixed_code
    assert 'data: TODO: Describe this parameter.' in fixed_code
    assert 'threshold: TODO: Describe this parameter.' in fixed_code


def test_docstring_generator_no_params_no_return():
    """Test docstring generation for simple functions."""
    generator = CodeGenerator()
    
    source_code = """
def print_hello():
    print("Hello, World!")
"""
    
    artifact = FunctionArtifact(
        function_name="print_hello",
        file_path="hello.py",
        source_code=source_code
    )
    
    suggestion = FixSuggestion(
        vulnerability_id="MISSING_DOCSTRING",
        description="Function 'print_hello' has no docstring",
        target_artifact=artifact,
        context_data={
            'function_name': 'print_hello',
            'parameters': [],
            'has_return': False
        }
    )
    
    fixed_code = generator.generate_fix(suggestion)
    
    # Should have simple docstring without Args or Returns sections
    assert '"""TODO: Add a docstring.' in fixed_code
    assert 'Args:' not in fixed_code
    assert 'Returns:' not in fixed_code
    assert '"""' in fixed_code  # Closing quotes


def test_get_last_fix_summary():
    """Test getting a summary of the last generated fix."""
    generator = CodeGenerator()
    
    # Initially no summary
    assert generator.get_last_fix_summary() is None
    
    # Generate a fix
    source_code = "def f(): requests.get('http://api.com', verify=False)"
    artifact = FunctionArtifact("f", "f.py", source_code=source_code)
    suggestion = FixSuggestion(
        "INSECURE_SSL_VERIFICATION",
        "SSL disabled",
        artifact
    )
    
    generator.generate_fix(suggestion)
    
    # Now we should have a summary
    summary = generator.get_last_fix_summary()
    assert summary is not None
    assert "Generated fix for f" in summary


if __name__ == "__main__":
    # Run tests
    test_fix_suggestion_creation()
    print("✓ FixSuggestion creation tests passed")
    
    test_ssl_fixer_transformer()
    print("✓ SSL fixer transformer tests passed")
    
    test_code_generator_ssl_fix()
    print("✓ CodeGenerator SSL fix tests passed")
    
    test_multiple_ssl_issues_in_one_function()
    print("✓ Multiple SSL issues tests passed")
    
    test_nested_calls_with_ssl()
    print("✓ Nested calls tests passed")
    
    test_unsupported_vulnerability_type()
    print("✓ Unsupported vulnerability tests passed")
    
    test_invalid_source_code()
    print("✓ Invalid source code tests passed")
    
    test_get_last_fix_summary()
    print("✓ Fix summary tests passed")
    
    test_docstring_generator()
    print("✓ Docstring generator tests passed")
    
    test_docstring_generator_with_self_parameter()
    print("✓ Docstring generator with self parameter tests passed")
    
    test_docstring_generator_no_params_no_return()
    print("✓ Docstring generator simple function tests passed")
    
    print("\nAll CodeGenerator tests passed!")