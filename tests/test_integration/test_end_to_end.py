"""
Consolidated end-to-end integration tests.
"""
import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import ast

from regionai.discovery import (
    PRIMITIVE_TRANSFORMATIONS,
    STRUCTURED_DATA_PRIMITIVES,
    AST_PRIMITIVES
)
from tier1.discovery.discovery_engine import DiscoveryEngine
from tier2.data.problem import Problem
from tier2.computer_science.analysis.interprocedural import analyze_interprocedural
from tier1.core.abstract_domains import (
    Sign, prove_property
)


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
        
        # Should detect exactly one null pointer error
        assert len(result.errors) == 1, f"Expected 1 error, got {len(result.errors)}: {result.errors}"
        
        # Check specific error details
        error = result.errors[0]
        assert "null pointer exception" in error.lower(), f"Error should mention 'null pointer exception', got: {error}"
        assert "data" in error, f"Error should mention variable 'data', got: {error}"
        assert "value" in error or "attribute" in error, f"Error should mention attribute access, got: {error}"
    
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
        
        # Run interprocedural analysis to get bounds information
        result = analyze_interprocedural(tree)
        
        # Check for bounds errors
        assert len(result.errors) >= 1, "Should detect at least one bounds error"
        
        # Verify the error is specifically about array bounds
        bounds_errors = [err for err in result.errors if "bounds" in err.lower() or "index" in err.lower()]
        assert len(bounds_errors) > 0, "Should detect array bounds violation"
        
        # Verify error mentions the specific issue
        error_text = ' '.join(result.errors).lower()
        assert "out of bounds" in error_text or "index 10" in error_text or "array" in error_text
    
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
        
        # Verify all intermediate variables are correctly inferred
        assert 'x' in result, "Should track variable x"
        assert 'y' in result, "Should track variable y"
        assert 'z' in result, "Should track variable z"
        assert 'w' in result, "Should track variable w"
        
        # Verify sign properties
        assert result.get('x') == Sign.POSITIVE, "x should be positive"
        assert result.get('y') == Sign.POSITIVE, "y should be positive"
        assert result.get('z') == Sign.POSITIVE, "z (x+y) should be positive"
        assert result.get('w') == Sign.POSITIVE, "w (z*2) should be positive"


class TestTransformationDiscoveryPipeline:
    """Test transformation discovery end-to-end."""
    
    def test_discover_and_apply(self):
        """Test discovering transformation and applying it."""
        # Create problems that need SUM
        problems = [
            Problem(
                name="sum_test_1",
                problem_type="transformation",
                input_data=torch.tensor([1, 2, 3]),
                output_data=torch.tensor([6]),
                description="Sum elements"
            ),
            Problem(
                name="sum_test_2",
                problem_type="transformation",
                input_data=torch.tensor([4, 5]),
                output_data=torch.tensor([9]),
                description="Sum elements"
            )
        ]
        
        # Run discovery
        engine = DiscoveryEngine(primitives=PRIMITIVE_TRANSFORMATIONS[:5])
        discovered = engine.discover_transformations(problems, max_iterations=10)
        
        # Verify we discovered at least one transformation
        assert len(discovered) > 0, "Should discover at least one transformation"
        
        # Find the SUM transformation (or equivalent)
        sum_transform = None
        for transform in discovered:
            # Test if it performs summation
            test_input = torch.tensor([10, 20])
            try:
                result = transform.apply(test_input)
                if isinstance(result, torch.Tensor) and result.item() == 30:
                    sum_transform = transform
                    break
            except:
                continue
        
        assert sum_transform is not None, "Should discover a sum transformation"
        
        # Apply discovered transformation to new data
        new_test = torch.tensor([100, 200, 300])
        result = sum_transform.apply(new_test)
        assert result.item() == 600, f"Expected 600, got {result.item()}"
    
    def test_composition_discovery(self):
        """Test discovering composed transformations."""
        # Problems requiring FILTER → MAP → SUM
        problems = [
            Problem(
                name="filter_sum_1",
                problem_type="transformation",
                input_data=[{"v": 1}, {"v": 2}, {"v": 3}, {"v": 4}],
                output_data=torch.tensor([7]),  # Sum of values > 2
                description="Filter and sum values > 2"
            ),
            Problem(
                name="filter_sum_2",
                problem_type="transformation",
                input_data=[{"v": 5}, {"v": 1}, {"v": 6}],
                output_data=torch.tensor([11]),  # Sum of values > 2
                description="Filter and sum values > 2"
            )
        ]
        
        # Combine all primitives for discovery
        all_primitives = PRIMITIVE_TRANSFORMATIONS + STRUCTURED_DATA_PRIMITIVES
        engine = DiscoveryEngine(primitives=all_primitives)
        
        # Discover transformations
        discovered = engine.discover_transformations(problems, max_iterations=20)
        
        # Should discover a transformation that filters and sums
        assert len(discovered) > 0, "Should discover at least one transformation"
        
        # Test the discovered transformation
        correct_transform = None
        for transform in discovered:
            # Test on first problem
            try:
                result = transform.apply(problems[0].input_data)
                if isinstance(result, torch.Tensor) and result.item() == 7:
                    # Verify on second problem
                    result2 = transform.apply(problems[1].input_data)
                    if isinstance(result2, torch.Tensor) and result2.item() == 11:
                        correct_transform = transform
                        break
            except:
                continue
        
        assert correct_transform is not None, "Should discover the correct filter+sum transformation"
        
        # Test on new data
        test_data = [{"v": 10}, {"v": 1}, {"v": 3}, {"v": 2}]
        result = correct_transform.apply(test_data)
        assert result.item() == 13, f"Expected 13 (10+3), got {result.item()}"


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
        
        # Apply all AST optimization primitives
        optimizations = [t for t in AST_PRIMITIVES if 'identity' in t.name.lower() or 'fold' in t.name.lower()]
        
        # Apply optimizations iteratively until no more changes
        optimized_tree = tree
        changes_made = True
        iterations = 0
        
        while changes_made and iterations < 10:
            changes_made = False
            for opt_transform in optimizations:
                try:
                    new_tree = opt_transform.apply(optimized_tree)
                    if ast.dump(new_tree) != ast.dump(optimized_tree):
                        optimized_tree = new_tree
                        changes_made = True
                except:
                    continue
            iterations += 1
        
        # Verify optimizations were applied
        optimized_code = ast.unparse(optimized_tree)
        
        # Check specific optimizations
        assert "5 + 0" not in optimized_code, "Should optimize away additive identity"
        assert "x * 1" not in optimized_code, "Should optimize away multiplicative identity"
        assert "2 + 3" not in optimized_code, "Should fold constants"
        assert "z - 0" not in optimized_code, "Should optimize away subtractive identity"
        assert "w / 1" not in optimized_code, "Should optimize away division identity"
        
        # Verify the semantics are preserved by executing both versions
        exec_globals_original = {}
        exec_globals_optimized = {}
        
        exec(code, exec_globals_original)
        exec(optimized_code, exec_globals_optimized)
        
        assert exec_globals_original['result'] == exec_globals_optimized['result'], "Optimization should preserve semantics"


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
        # This test is no longer relevant since we removed global state
        # Each analysis now uses its own AnalysisContext
        pytest.skip("Global state has been removed - each analysis uses its own context")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])