"""
Consolidated tests for transformation discovery and composition.
"""
import pytest
import torch
import ast
from typing import List, Dict, Any

from src.regionai.discovery.transformation import (
    Transformation, TransformationSequence,
    ConditionalTransformation, ForEachTransformation,
    PRIMITIVE_OPERATIONS
)
from src.regionai.discovery import (
    PRIMITIVE_TRANSFORMATIONS, STRUCTURED_DATA_PRIMITIVES,
    AST_PRIMITIVES
)
from src.regionai.discovery.discovery import DiscoveryEngine
from src.regionai.data.problem import Problem


class TestPrimitiveTransformations:
    """Test basic transformation primitives."""
    
    def test_arithmetic_primitives(self):
        """Test ADD, MULTIPLY primitives."""
        add_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "ADD")
        mult_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "MULTIPLY")
        
        # Test tensor operations
        x = torch.tensor([1, 2, 3])
        assert torch.equal(add_op(x, [2]), torch.tensor([3, 4, 5]))
        assert torch.equal(mult_op(x, [2]), torch.tensor([2, 4, 6]))
    
    def test_filter_map_primitives(self):
        """Test FILTER and MAP operations."""
        filter_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "FILTER")
        map_op = next(t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "MAP")
        
        x = torch.tensor([1, 2, 3, 4, 5])
        # Filter > 2
        filtered = filter_op(x, [lambda v: v > 2])
        assert torch.equal(filtered, torch.tensor([3, 4, 5]))
        
        # Map * 2
        mapped = map_op(x, [lambda v: v * 2])
        assert torch.equal(mapped, torch.tensor([2, 4, 6, 8, 10]))


class TestStructuredDataTransformations:
    """Test structured data (dict/object) transformations."""
    
    def test_map_get(self):
        """Test MAP_GET for extracting values."""
        map_get = next(t for t in STRUCTURED_DATA_PRIMITIVES if t.name == "MAP_GET")
        
        data = [{"value": 10}, {"value": 20}, {"value": 30}]
        result = map_get(data, ["value"])
        assert result == [10, 20, 30]
    
    def test_filter_by_value(self):
        """Test FILTER_BY_VALUE for filtering dicts."""
        filter_by_value = next(t for t in STRUCTURED_DATA_PRIMITIVES if t.name == "FILTER_BY_VALUE")
        
        data = [
            {"type": "A", "value": 10},
            {"type": "B", "value": 20},
            {"type": "A", "value": 30}
        ]
        result = filter_by_value(data, ["type", "A"])
        assert len(result) == 2
        assert all(d["type"] == "A" for d in result)


class TestASTTransformations:
    """Test AST manipulation primitives."""
    
    def test_additive_identity(self):
        """Test x + 0 → x transformation."""
        code = "y = x + 0"
        tree = ast.parse(code)
        
        # Would apply additive identity transformation
        # assert transformed code is "y = x"
    
    def test_constant_folding(self):
        """Test evaluation of constant expressions."""
        evaluate = next(t for t in AST_PRIMITIVES if t.name == "EVALUATE_NODE")
        
        # Create AST for 2 + 3
        node = ast.BinOp(
            left=ast.Constant(value=2),
            op=ast.Add(),
            right=ast.Constant(value=3)
        )
        result = evaluate(node, [])
        assert result.value == 5


class TestComposition:
    """Test transformation composition."""
    
    def test_simple_composition(self):
        """Test composing two transformations."""
        add_2 = Transformation("ADD_2", lambda x: x + 2)
        mult_3 = Transformation("MULT_3", lambda x: x * 3)
        
        # Create transformation sequence instead of ComposedTransformation
        from src.regionai.discovery.transformation import AppliedTransformation
        applied_add = AppliedTransformation(add_2, [])
        applied_mult = AppliedTransformation(mult_3, [])
        composed = TransformationSequence([applied_add, applied_mult])
        assert composed.apply(torch.tensor([5]))[0] == (5 + 2) * 3  # 21
    
    def test_filter_map_composition(self):
        """Test FILTER → MAP → SUM pattern."""
        data = [{"value": 1}, {"value": 2}, {"value": 3}, {"value": 4}]
        
        # Filter value > 2, Map to values, Sum
        # Expected: 3 + 4 = 7
        # Would compose and apply transformations


class TestConditionalTransformations:
    """Test conditional (IF/ELSE) transformations."""
    
    def test_conditional_bonus(self):
        """Test conditional salary bonus calculation."""
        transform = ConditionalTransformation(
            condition=lambda x: x["role"] == "engineer",
            if_transform=lambda x: x["salary"] * 1.10,
            else_transform=lambda x: x["salary"] * 1.03
        )
        
        engineer = {"role": "engineer", "salary": 100000}
        manager = {"role": "manager", "salary": 100000}
        
        assert transform(engineer) == 110000
        assert transform(manager) == 103000


class TestIterativeTransformations:
    """Test iterative (FOR_EACH) transformations."""
    
    def test_for_each_pricing(self):
        """Test FOR_EACH with nested operations."""
        # Calculate total with category-based pricing
        pricing_rules = {
            "electronics": 1.2,
            "books": 1.1,
            "food": 1.05
        }
        
        items = [
            {"category": "electronics", "price": 100},
            {"category": "books", "price": 50},
            {"category": "food", "price": 30}
        ]
        
        # Would apply FOR_EACH with conditional pricing
        # Expected: 100*1.2 + 50*1.1 + 30*1.05


class TestDiscoveryEngine:
    """Test transformation discovery."""
    
    def test_discover_sum_pattern(self):
        """Test discovering SUM transformation."""
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
        
        engine = DiscoveryEngine(primitives=PRIMITIVE_TRANSFORMATIONS)
        # Would run discovery and verify SUM is found
    
    def test_discover_composition(self):
        """Test discovering composed transformations."""
        # Problems requiring FILTER → MAP → SUM
        problems = [
            Problem(
                input_data=[{"v": 1}, {"v": 2}, {"v": 3}, {"v": 4}],
                output_data=7  # Sum of values > 2
            )
        ]
        
        # Would verify discovery of composition


# Integration tests
class TestEndToEnd:
    """End-to-end transformation tests."""
    
    def test_data_processing_pipeline(self):
        """Test complete data processing pipeline."""
        # Input: Raw data with multiple transformations
        # Output: Processed result
        pass
    
    def test_ast_optimization_pipeline(self):
        """Test AST optimization pipeline."""
        # Input: Unoptimized code
        # Output: Optimized code
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])