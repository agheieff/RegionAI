"""
Consolidated tests for all abstract domains and analysis features.
"""
import pytest
import ast
from typing import Dict, Any

from src.regionai.discovery.abstract_domains import (
    Sign, Nullability, 
    sign_add, sign_multiply, nullability_join,
    reset_abstract_state, update_sign_state, update_nullability_state,
    check_null_dereference, prove_property
)
from src.regionai.discovery.range_domain import (
    Range, range_add, range_widen, check_array_bounds
)
from src.regionai.analysis import (
    build_cfg, analyze_with_fixpoint,
    build_call_graph, analyze_interprocedural
)


class TestSignDomain:
    """Test cases for sign abstract domain."""
    
    def test_sign_algebra(self):
        """Test basic sign operations."""
        assert sign_add(Sign.POSITIVE, Sign.POSITIVE) == Sign.POSITIVE
        assert sign_add(Sign.POSITIVE, Sign.NEGATIVE) == Sign.TOP
        assert sign_add(Sign.NEGATIVE, Sign.NEGATIVE) == Sign.NEGATIVE
        assert sign_multiply(Sign.POSITIVE, Sign.NEGATIVE) == Sign.NEGATIVE
        assert sign_multiply(Sign.NEGATIVE, Sign.NEGATIVE) == Sign.POSITIVE
    
    def test_sign_propagation(self):
        """Test sign tracking through program."""
        code = """
x = 5
y = -3
z = x + y
"""
        tree = ast.parse(code)
        result = prove_property(tree, {'x': Sign.POSITIVE, 'y': Sign.NEGATIVE})
        assert result['x'] == True  # x is positive
        assert result['y'] == True  # y is negative
    
    def test_sign_proofs(self):
        """Test proving sign properties."""
        code = """
x = input_positive_integer()
y = x * -1
z = y + -5
"""
        # Would need to mock input_positive_integer
        # This demonstrates the testing pattern


class TestNullabilityDomain:
    """Test cases for nullability domain."""
    
    def test_nullability_join(self):
        """Test nullability lattice operations."""
        assert nullability_join(Nullability.NOT_NULL, Nullability.NOT_NULL) == Nullability.NOT_NULL
        assert nullability_join(Nullability.NOT_NULL, Nullability.DEFINITELY_NULL) == Nullability.NULLABLE
        assert nullability_join(Nullability.NULLABLE, Nullability.NOT_NULL) == Nullability.NULLABLE
    
    def test_null_detection(self):
        """Test null pointer detection."""
        code = """
obj = None
value = obj.field
"""
        tree = ast.parse(code)
        # Would analyze and check for null dereference
        # assert "Null pointer exception" in errors
    
    def test_safe_null_handling(self):
        """Test recognition of safe null checks."""
        code = """
obj = get_object()
if obj is not None:
    value = obj.field
else:
    value = None
"""
        # Would verify no errors with proper null check


class TestRangeDomain:
    """Test cases for range domain."""
    
    def test_range_arithmetic(self):
        """Test range operations."""
        r1 = Range(0, 10)
        r2 = Range(5, 15)
        assert range_add(r1, r2) == Range(5, 25)
        
        r3 = Range(10, 10)
        r4 = Range(20, 20)
        assert range_add(r3, r4) == Range(30, 30)
    
    def test_array_bounds(self):
        """Test array bounds checking."""
        # Safe access
        assert check_array_bounds(Range(0, 5), 10) == ""
        
        # Out of bounds
        assert "out of bounds" in check_array_bounds(Range(10, 15), 10)
        
        # Negative index
        assert "negative" in check_array_bounds(Range(-5, -1), 10)
    
    def test_widening(self):
        """Test widening for termination."""
        old = Range(0, 0)
        for i in range(1, 5):
            new = Range(0, i)
            widened = range_widen(old, new, i)
            if i >= 3:
                assert widened.max == float('inf')
            old = widened


class TestFixpointAnalysis:
    """Test cases for fixpoint computation."""
    
    def test_simple_loop(self):
        """Test analysis of simple counting loop."""
        code = """
i = 0
while i < 10:
    i = i + 1
"""
        tree = ast.parse(code)
        cfg = build_cfg(tree)
        
        # Verify loop detection
        loop_headers = [b for b in cfg.blocks.values() if b.is_loop_header]
        assert len(loop_headers) > 0
    
    def test_nested_loops(self):
        """Test analysis of nested loops."""
        code = """
for i in range(10):
    for j in range(5):
        x = i + j
"""
        tree = ast.parse(code)
        cfg = build_cfg(tree)
        # Would verify nested structure


class TestInterproceduralAnalysis:
    """Test cases for whole-program analysis."""
    
    def test_call_graph(self):
        """Test call graph construction."""
        code = """
def foo():
    return bar()

def bar():
    return 42

def main():
    x = foo()
"""
        tree = ast.parse(code)
        cg = build_call_graph(tree)
        
        assert 'foo' in cg.functions
        assert 'bar' in cg.functions
        assert 'bar' in cg.functions['foo'].calls
        assert 'main' in cg.entry_points
    
    def test_function_summaries(self):
        """Test function summary computation."""
        code = """
def get_null():
    return None

def get_positive():
    return 42
"""
        tree = ast.parse(code)
        result = analyze_interprocedural(tree)
        
        # Verify summaries computed
        assert 'get_null' in result.function_summaries
        assert 'get_positive' in result.function_summaries


# Parametrized tests for curriculum problems
@pytest.mark.parametrize("problem_type,expected", [
    ("sign_analysis", {"x": Sign.POSITIVE}),
    ("null_safety", {"errors": 1}),
    ("range_bounds", {"safe": True}),
])
def test_curriculum_problems(problem_type, expected):
    """Test various curriculum problem types."""
    # Would load and test curriculum problems
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])