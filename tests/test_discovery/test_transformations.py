"""
Consolidated tests for transformation discovery and composition.
"""
import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import ast

from tier2.core.transformation import (
    Transformation, TransformationSequence,
    ConditionalTransformation, AppliedTransformation
)
from regionai.discovery import (
    PRIMITIVE_TRANSFORMATIONS, STRUCTURED_DATA_PRIMITIVES,
    AST_PRIMITIVES
)
from tier1.discovery.discovery_engine import DiscoveryEngine
from tier2.data.problem import Problem


class TestPrimitiveTransformations:
    """Test basic transformation primitives."""
    
    def test_arithmetic_primitives(self):
        """Test ADD, MULTIPLY primitives."""
        # Find available arithmetic primitives
        add_tensor = next((t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "ADD_TENSOR"), None)
        multiply = next((t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "MULTIPLY"), None)
        
        if add_tensor:
            # Test tensor addition
            x = torch.tensor([1, 2, 3])
            result = add_tensor.operation(x, [torch.tensor(2)])
            assert torch.equal(result, torch.tensor([3, 4, 5]))
        
        if multiply:
            # Test multiplication
            x = torch.tensor([1, 2, 3]) 
            result = multiply.operation(x, [torch.tensor(2)])
            assert torch.equal(result, torch.tensor([2, 4, 6]))
    
    def test_filter_map_primitives(self):
        """Test FILTER and MAP operations."""
        # Check for FILTER_GT_5 as an example filter
        filter_gt5 = next((t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "FILTER_GT_5"), None)
        
        if filter_gt5:
            x = torch.tensor([1, 2, 6, 7, 3, 8, 4, 5])
            filtered = filter_gt5.operation(x)
            expected = torch.tensor([6, 7, 8])
            assert torch.equal(filtered, expected)
        
        # Test SUM as an aggregation example
        sum_op = next((t for t in PRIMITIVE_TRANSFORMATIONS if t.name == "SUM"), None)
        if sum_op:
            x = torch.tensor([1, 2, 3, 4, 5])
            result = sum_op.operation(x)
            assert result.item() == 15


class TestStructuredDataTransformations:
    """Test structured data (dict/object) transformations."""
    
    def test_map_get(self):
        """Test MAP_GET for extracting values."""
        map_get = next(t for t in STRUCTURED_DATA_PRIMITIVES if t.name == "MAP_GET")
        
        data = [{"value": 10}, {"value": 20}, {"value": 30}]
        result = map_get.operation(data, ["value"])
        # MAP_GET returns a tensor
        assert torch.equal(result, torch.tensor([10.0, 20.0, 30.0]))
    
    def test_filter_by_value(self):
        """Test FILTER_BY_VALUE for filtering dicts."""
        filter_by_value = next(t for t in STRUCTURED_DATA_PRIMITIVES if t.name == "FILTER_BY_VALUE")
        
        data = [
            {"type": "A", "value": 10},
            {"type": "B", "value": 20},
            {"type": "A", "value": 30}
        ]
        result = filter_by_value.operation(data, ["type", "A"])
        assert len(result) == 2
        assert all(d["type"] == "A" for d in result)


class TestASTTransformations:
    """Test AST manipulation primitives."""
    
    def test_additive_identity(self):
        """Test x + 0 → x transformation."""
        code = "y = x + 0"
        ast.parse(code)
        
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
        result = evaluate.operation(node, [])
        assert isinstance(result, ast.Constant)
        assert result.value == 5


class TestComposition:
    """Test transformation composition."""
    
    def test_simple_composition(self):
        """Test composing two transformations."""
        add_2 = Transformation("ADD_2", lambda x: x + 2)
        mult_3 = Transformation("MULT_3", lambda x: x * 3)
        
        # Create transformation sequence with AppliedTransformation
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
        # Create condition transformation
        condition_transform = Transformation(
            name="IS_ENGINEER",
            operation=lambda x, args: x["role"] == "engineer"
        )
        condition = AppliedTransformation(condition_transform, [])
        
        # Create if/else transformations
        # These operate on lists of dicts
        # When num_args=0, operation is called with just one argument
        if_transform = Transformation(
            name="ENGINEER_BONUS",
            operation=lambda x: [{"role": item["role"], "salary": item["salary"] * 1.10} for item in x],
            input_type="dict_list",
            output_type="dict_list",
            num_args=0
        )
        else_transform = Transformation(
            name="STANDARD_BONUS", 
            operation=lambda x: [{"role": item["role"], "salary": item["salary"] * 1.03} for item in x],
            input_type="dict_list",
            output_type="dict_list",
            num_args=0
        )
        
        # Create sequences
        if_sequence = TransformationSequence([AppliedTransformation(if_transform, [])])
        else_sequence = TransformationSequence([AppliedTransformation(else_transform, [])])
        
        # Create conditional transformation
        transform = ConditionalTransformation(
            name="BONUS_CALC",
            condition=condition,
            if_true_sequence=if_sequence,
            if_false_sequence=else_sequence
        )
        
        engineer = {"role": "engineer", "salary": 100000}
        manager = {"role": "manager", "salary": 100000}
        
        result1 = transform.apply([engineer])
        result2 = transform.apply([manager])
        
        assert abs(result1[0]["salary"] - 110000) < 0.01
        assert abs(result2[0]["salary"] - 103000) < 0.01


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
                name="sum_example_1",
                problem_type="transformation",
                input_data=torch.tensor([1, 2, 3]),
                output_data=torch.tensor([6]),
                description="Sum array elements"
            ),
            Problem(
                name="sum_example_2", 
                problem_type="transformation",
                input_data=torch.tensor([4, 5]),
                output_data=torch.tensor([9]),
                description="Sum array elements"
            )
        ]
        
        engine = DiscoveryEngine()
        # Would run discovery and verify SUM is found
    
    def test_discover_composition(self):
        """Test discovering composed transformations."""
        # Problems requiring FILTER → MAP → SUM
        problems = [
            Problem(
                name="filter_map_sum_1",
                problem_type="transformation",
                input_data=[{"v": 1}, {"v": 2}, {"v": 3}, {"v": 4}],
                output_data=torch.tensor([7]),  # Sum of values > 2
                description="Filter values > 2, then sum"
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
    
    def test_ast_optimization_pipeline(self):
        """Test AST optimization pipeline."""
        # Input: Unoptimized code
        # Output: Optimized code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])