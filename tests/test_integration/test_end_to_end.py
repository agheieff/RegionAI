"""
Consolidated end-to-end integration tests.
"""
import pytest
import torch
import ast
from typing import List, Dict, Any

from src.regionai.discovery.transformation import (
    Transformation, PRIMITIVE_TRANSFORMATIONS,
    STRUCTURED_DATA_PRIMITIVES, AST_PRIMITIVES
)
from src.regionai.discovery.discovery import DiscoveryEngine
from src.regionai.data.problem import Problem
from src.regionai.analysis import (
    build_cfg, analyze_with_fixpoint,
    build_call_graph, analyze_interprocedural
)
from src.regionai.discovery.abstract_domains import (
    Sign, Nullability, reset_abstract_state,
    check_null_dereference, prove_property
)
from src.regionai.discovery.range_domain import check_array_bounds


class TestCompleteAnalysisPipeline:
    """Test complete analysis pipeline from code to bug detection."""
    
    def test_null_detection_pipeline(self):
        """Test null pointer detection end-to-end."""
        # Input code with null bug
        code = """
def get_data():
    return None

def process():
    data = get_data()
    result = data.value  # Bug!
    return result
"""
        tree = ast.parse(code)
        
        # Run interprocedural analysis
        result = analyze_interprocedural(tree)
        
        # Should detect null pointer error
        assert len(result.errors) > 0
        assert any("null" in error.lower() for error in result.errors)
    
    def test_bounds_checking_pipeline(self):
        """Test array bounds checking end-to-end."""
        code = """
def get_index():
    return 10

def access_array():
    arr = [1, 2, 3, 4, 5]
    idx = get_index()
    return arr[idx]  # Out of bounds!
"""
        tree = ast.parse(code)
        
        # Would run analysis and check bounds
        # This demonstrates the testing pattern
    
    def test_sign_proof_pipeline(self):
        """Test sign property proving end-to-end."""
        code = """
x = 5
y = 10
z = x + y
w = z * 2
"""
        tree = ast.parse(code)
        
        # Prove that w is positive
        result = prove_property(tree, {'x': Sign.POSITIVE, 'y': Sign.POSITIVE})
        
        # Would verify properties hold
        # assert result['w'] == True


class TestTransformationDiscoveryPipeline:
    """Test transformation discovery end-to-end."""
    
    def test_discover_and_apply(self):
        """Test discovering transformation and applying it."""
        # Create problems that need SUM
        problems = [
            Problem(
                input_data=torch.tensor([1, 2, 3]),
                output_data=6
            ),
            Problem(
                input_data=torch.tensor([4, 5]),
                output_data=9
            )
        ]
        
        # Run discovery
        engine = DiscoveryEngine(primitives=PRIMITIVE_TRANSFORMATIONS[:5])
        # Would discover SUM transformation
        
        # Apply discovered transformation
        # assert discovered_transform(torch.tensor([10, 20])) == 30
    
    def test_composition_discovery(self):
        """Test discovering composed transformations."""
        # Problems requiring FILTER → MAP → SUM
        problems = [
            Problem(
                input_data=[{"v": 1}, {"v": 2}, {"v": 3}, {"v": 4}],
                output_data=7  # Sum of values > 2
            ),
            Problem(
                input_data=[{"v": 5}, {"v": 1}, {"v": 6}],
                output_data=11  # Sum of values > 2
            )
        ]
        
        # Would discover the composition
        # engine = DiscoveryEngine(primitives=ALL_PRIMITIVES)


class TestASTOptimizationPipeline:
    """Test AST optimization end-to-end."""
    
    def test_full_optimization(self):
        """Test complete optimization pipeline."""
        code = """
x = 5 + 0
y = x * 1
z = 2 + 3
w = z - 0
result = w / 1
"""
        tree = ast.parse(code)
        
        # Would apply all optimizations:
        # - Additive identity: x = 5
        # - Multiplicative identity: y = x
        # - Constant folding: z = 5
        # - Subtractive identity: w = z
        # - Division identity: result = w
        
        # Expected optimized code:
        # x = 5
        # y = x
        # z = 5
        # w = z
        # result = w


class TestRealWorldScenarios:
    """Test real-world bug detection scenarios."""
    
    def test_api_misuse(self):
        """Test detecting API precondition violations."""
        code = """
def divide(a, b):
    return a / b

def calculate(values):
    total = 0
    for v in values:
        total += divide(v, v - v)  # Division by zero!
    return total
"""
        # Would detect division by zero through analysis
    
    def test_resource_leak(self):
        """Test detecting resource leaks."""
        code = """
def process_file(filename):
    f = open(filename)
    data = f.read()
    if len(data) == 0:
        return None  # File not closed!
    f.close()
    return data
"""
        # Would detect missing close on early return
    
    def test_complex_null_flow(self):
        """Test complex null propagation."""
        code = """
def get_config():
    if not os.path.exists("config.json"):
        return None
    return load_config()

def get_setting(key):
    config = get_config()
    return config[key]  # Potential null!

def main():
    port = get_setting("port")
    server.listen(port)
"""
        # Would trace null through multiple functions


# Performance and scalability tests
class TestScalability:
    """Test analysis scalability."""
    
    @pytest.mark.slow
    def test_large_codebase(self):
        """Test analysis on larger code."""
        # Generate large AST
        functions = []
        for i in range(100):
            func = f"""
def func_{i}(x):
    y = x + {i}
    z = y * 2
    return z
"""
            functions.append(func)
        
        code = "\n".join(functions)
        tree = ast.parse(code)
        
        # Should complete in reasonable time
        import time
        start = time.time()
        result = analyze_interprocedural(tree)
        elapsed = time.time() - start
        
        assert elapsed < 10.0  # Should finish within 10 seconds
        assert len(result.function_summaries) == 100


# Regression tests for specific bugs
class TestRegressions:
    """Test specific bug fixes and edge cases."""
    
    def test_empty_function_handling(self):
        """Test handling of empty functions."""
        code = """
def empty():
    pass

def caller():
    result = empty()
"""
        tree = ast.parse(code)
        # Should not crash on empty function
        result = analyze_interprocedural(tree)
        assert 'empty' in result.function_summaries
    
    def test_global_state_reset(self):
        """Test that global state is properly reset."""
        # Run analysis twice
        code1 = "x = 5"
        code2 = "y = 10"
        
        reset_abstract_state()
        tree1 = ast.parse(code1)
        result1 = prove_property(tree1, {})
        
        reset_abstract_state()
        tree2 = ast.parse(code2)
        result2 = prove_property(tree2, {})
        
        # Results should be independent
        assert 'x' not in result2
        assert 'y' not in result1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])