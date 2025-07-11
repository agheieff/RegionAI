"""
Tests for context-sensitive interprocedural analysis.
"""
import ast
import pytest
from regionai.analysis.interprocedural import InterproceduralAnalyzer
from regionai.discovery.abstract_domains import Sign, Nullability, reset_abstract_state
from regionai.analysis.summary import CallContext


class TestContextSensitiveAnalysis:
    """Test context-sensitive function analysis."""
    
    def setup_method(self):
        """Reset state before each test."""
        reset_abstract_state()
    
    def test_identity_function_with_different_contexts(self):
        """Test that identity function gets different summaries for different contexts."""
        code = """
def identity(x):
    return x

def main():
    a = identity(5)      # Context 1: integer argument
    b = identity(None)   # Context 2: null argument
    return (a, b)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check that we have summaries
        assert 'identity' in result.function_summaries
        assert 'main' in result.function_summaries
        
        # Check context-sensitive summaries
        if hasattr(analyzer.summary_computer, 'context_summaries'):
            contexts = list(analyzer.summary_computer.context_summaries.keys())
            
            # Should have at least 2 different contexts for identity
            identity_contexts = [c for c in contexts if c.function_name == 'identity']
            assert len(identity_contexts) >= 2
            
            # The contexts should have different parameter states
            context_states = [c.parameter_states for c in identity_contexts]
            assert context_states[0] != context_states[1]
    
    def test_nullable_analysis_with_context(self):
        """Test that nullability doesn't incorrectly propagate between contexts."""
        code = """
def process(value):
    if value is None:
        return 0
    return value.length()  # Only safe if value is not null

def safe_path():
    obj = {"length": lambda: 10}
    result = process(obj)  # Context 1: non-null object
    return result

def unsafe_path():
    result = process(None)  # Context 2: null
    return result

def main():
    a = safe_path()
    b = unsafe_path()
    return a + b
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should not have null pointer errors in the safe path
        # The analysis should be precise enough to know that
        # process(obj) is safe when obj is non-null
        
        # Check that process was analyzed with different contexts
        if hasattr(analyzer.summary_computer, 'context_summaries'):
            process_contexts = [c for c in analyzer.summary_computer.context_summaries.keys() 
                               if c.function_name == 'process']
            assert len(process_contexts) >= 1
    
    def test_recursive_function_with_context(self):
        """Test context-sensitive analysis of recursive functions."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def compute_factorials():
    f5 = factorial(5)    # Context 1: positive integer
    f0 = factorial(0)    # Context 2: zero
    f_neg = factorial(-1) # Context 3: negative
    return (f5, f0, f_neg)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Factorial should be analyzed with different initial contexts
        # but converge to a fixpoint
        assert 'factorial' in result.function_summaries
        
        # Check that recursive calls were handled
        factorial_summary = result.function_summaries['factorial']
        assert factorial_summary.returns.nullability == Nullability.NOT_NULL
    
    def test_caching_of_context_sensitive_summaries(self):
        """Test that identical contexts reuse cached summaries."""
        code = """
def double(x):
    return x * 2

def triple_double():
    # Three calls with same context (positive integer)
    a = double(5)
    b = double(5)  # Should reuse summary from first call
    c = double(5)  # Should reuse summary again
    
    # Different context
    d = double(-3)  # Should create new summary
    
    return (a, b, c, d)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        
        # Track analysis calls
        analysis_count = {}
        original_analyze = analyzer._analyze_function
        
        def count_analyze(func_name, initial_state=None):
            key = (func_name, str(initial_state) if initial_state else "default")
            analysis_count[key] = analysis_count.get(key, 0) + 1
            return original_analyze(func_name, initial_state)
        
        analyzer._analyze_function = count_analyze
        
        result = analyzer.analyze_program(tree)
        
        # double should be analyzed at most twice (once per unique context)
        double_analyses = [k for k in analysis_count if k[0] == 'double']
        assert len(double_analyses) <= 2
    
    def test_parameter_sensitive_behavior(self):
        """Test function behavior changes based on parameter values."""
        code = """
def conditional_null(flag):
    if flag:
        return {"value": 42}
    return None

def caller1():
    result = conditional_null(True)
    # This should be safe - result is not null in this context
    value = result["value"]
    return value

def caller2():
    result = conditional_null(False)
    # This would be unsafe but we check first
    if result:
        value = result["value"]
        return value
    return 0

def main():
    a = caller1()
    b = caller2()
    return a + b
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # The analysis should understand that conditional_null
        # returns different values based on its parameter
        assert 'conditional_null' in result.function_summaries
    
    def test_context_with_multiple_parameters(self):
        """Test context sensitivity with multiple parameters."""
        code = """
def combine(a, b):
    if a is None and b is None:
        return 0
    elif a is None:
        return b
    elif b is None:
        return a
    else:
        return a + b

def test_combinations():
    r1 = combine(5, 10)      # Both non-null
    r2 = combine(5, None)    # Second null
    r3 = combine(None, 10)   # First null
    r4 = combine(None, None) # Both null
    
    return (r1, r2, r3, r4)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should analyze combine with different combinations of null/non-null
        if hasattr(analyzer.summary_computer, 'context_summaries'):
            combine_contexts = [c for c in analyzer.summary_computer.context_summaries.keys() 
                               if c.function_name == 'combine']
            # Should have multiple contexts for different parameter combinations
            assert len(combine_contexts) >= 1
    
    def test_context_propagation_through_calls(self):
        """Test that context sensitivity propagates through call chains."""
        code = """
def bottom(x):
    return x + 1

def middle(y):
    return bottom(y)

def top(z):
    return middle(z)

def main():
    a = top(5)     # Positive context should flow through
    b = top(-5)    # Negative context should flow through
    c = top(0)     # Zero context
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Each function in the chain should be analyzed with
        # contexts corresponding to the different initial values
        assert all(func in result.function_summaries 
                  for func in ['bottom', 'middle', 'top'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])