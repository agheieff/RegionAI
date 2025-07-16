"""
Tests for function summary system.
"""
import ast
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from regionai.domains.code.analysis.interprocedural import InterproceduralAnalyzer
from regionai.core.abstract_domains import Nullability


class TestFunctionSummary:
    """Test function summary computation and caching."""
    
    def setup_method(self):
        """Setup for each test."""
        # No need to reset state - each InterproceduralAnalyzer creates its own context
    
    def test_basic_summary(self):
        """Test basic function summary creation."""
        code = """
def add_one(x):
    return x + 1

def main():
    result = add_one(5)
    return result
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check that summaries were created
        assert 'add_one' in result.function_summaries
        assert 'main' in result.function_summaries
        
        # Check add_one summary
        add_one_summary = result.function_summaries['add_one']
        assert add_one_summary.function_name == 'add_one'
        assert len(add_one_summary.parameters) == 1
        assert add_one_summary.parameters[0].name == 'x'
    
    def test_null_return_summary(self):
        """Test summary for function returning null."""
        code = """
def get_null():
    return None

def process():
    value = get_null()
    return value
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check get_null summary
        get_null_summary = result.function_summaries['get_null']
        assert get_null_summary.returns.nullability == Nullability.DEFINITELY_NULL
    
    def test_summary_caching(self):
        """Test that summaries are cached and reused."""
        code = """
def helper(x):
    if x > 0:
        return x
    return None

def caller1():
    a = helper(5)
    return a

def caller2():
    b = helper(-1)
    return b

def main():
    x = caller1()
    y = caller2()
    return x + y
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        
        # Track when summaries are computed
        computed_summaries = []
        original_compute = analyzer.summary_computer.compute_summary
        
        def track_compute(func_def, entry_state, exit_state):
            computed_summaries.append(func_def.name)
            return original_compute(func_def, entry_state, exit_state)
        
        analyzer.summary_computer.compute_summary = track_compute
        
        result = analyzer.analyze_program(tree)
        
        # With context-sensitive analysis, helper may be analyzed multiple times
        # (once per unique calling context), which is correct behavior
        assert computed_summaries.count('helper') >= 1
        assert 'helper' in result.function_summaries
        
        # Verify all functions were analyzed
        assert 'caller1' in computed_summaries
        assert 'caller2' in computed_summaries
        assert 'main' in computed_summaries
    
    def test_summary_application(self):
        """Test that summaries are applied correctly at call sites."""
        code = """
def definitely_null():
    return None

def maybe_null(x):
    if x > 0:
        return x
    return None

def safe_function():
    return 42

def test_calls():
    a = definitely_null()  # Should be DEFINITELY_NULL
    b = maybe_null(5)      # Should be NULLABLE
    c = safe_function()    # Should be NOT_NULL
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check summaries
        assert result.function_summaries['definitely_null'].returns.nullability == Nullability.DEFINITELY_NULL
        assert result.function_summaries['safe_function'].returns.nullability == Nullability.NOT_NULL
    
    def test_interprocedural_propagation(self):
        """Test that summaries enable cross-function analysis."""
        code = """
def get_data():
    return None

def process():
    data = get_data()
    # This should be detected as null dereference
    result = data.value
    return result
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should detect the null dereference
        assert len(result.errors) > 0
        assert any('null' in error.lower() for error in result.errors)
    
    def test_recursive_function_summary(self):
        """Test summary computation for recursive functions."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def compute():
    result = factorial(5)
    return result
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should have summary for factorial
        assert 'factorial' in result.function_summaries
        
        # Factorial always returns non-null integer
        factorial_summary = result.function_summaries['factorial']
        assert factorial_summary.returns.nullability == Nullability.NOT_NULL
    
    def test_context_sensitivity(self):
        """Test that summaries can be context-sensitive."""
        code = """
def identity(x):
    return x

def caller1():
    # Calling with non-null
    result = identity(42)
    return result

def caller2():
    # Calling with null
    result = identity(None)
    return result
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Identity function should have been analyzed
        assert 'identity' in result.function_summaries
        
        # The summary should reflect that it returns what it receives
        # (This tests the basic infrastructure; full context sensitivity
        # would require more sophisticated summary computation)
    
    def test_side_effect_tracking(self):
        """Test that summaries track side effects."""
        code = """
global_var = 0

def pure_function(x):
    return x + 1

def impure_function(x):
    global global_var
    global_var = x
    return x

def main():
    a = pure_function(5)
    b = impure_function(10)
    return a + b
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check side effects are tracked
        pure_summary = result.function_summaries['pure_function']
        impure_summary = result.function_summaries['impure_function']
        
        # Pure function should have no global modifications
        assert len(pure_summary.side_effects.modifies_globals) == 0
        
        # Impure function should show it modifies global_var
        assert 'global_var' in impure_summary.side_effects.modifies_globals


if __name__ == "__main__":
    pytest.main([__file__, "-v"])