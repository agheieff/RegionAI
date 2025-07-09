"""
Curriculum for teaching iterative processing with nested conditionals.
"""
import torch
from typing import List, Dict, Any
from .problem import Problem


class IterativePricingCurriculumGenerator:
    """
    Teaches the AI to iterate over a collection and apply complex,
    conditional transformations to each item.
    Problem: Calculate final price based on category-specific discount and flat tax.
    Required Structure:
    FOR_EACH item IN products:
        IF item.category == 'electronics':
            discounted = item.base_price * 0.9
        ELSE IF item.category == 'apparel':
            discounted = item.base_price * 0.95
        ELSE:
            discounted = item.base_price * 0.98
        final_price = discounted + 5  # Add flat tax
        SET item.final_price = final_price
    """
    
    def generate_iterative_pricing_curriculum(self) -> List[Problem]:
        """Generates problems for learning iterative conditional pricing."""
        print("Generating curriculum for iterative pricing with conditionals...")
        
        return [
            Problem(
                name="iterative_pricing_1",
                problem_type="transformation",
                input_data=[
                    {'name': 'Laptop', 'category': 'electronics', 'base_price': 1200},
                    {'name': 'T-Shirt', 'category': 'apparel', 'base_price': 25},
                    {'name': 'Coffee Maker', 'category': 'electronics', 'base_price': 80},
                    {'name': 'Book', 'category': 'other', 'base_price': 15},
                ],
                output_data=[
                    {'name': 'Laptop', 'category': 'electronics', 'base_price': 1200, 'final_price': 1085.0},
                    {'name': 'T-Shirt', 'category': 'apparel', 'base_price': 25, 'final_price': 28.75},
                    {'name': 'Coffee Maker', 'category': 'electronics', 'base_price': 80, 'final_price': 77.0},
                    {'name': 'Book', 'category': 'other', 'base_price': 15, 'final_price': 19.7},
                ],
                description="Calculate final price: electronics -10%, apparel -5%, other -2%, then +$5 tax"
            ),
            Problem(
                name="iterative_pricing_2",
                problem_type="transformation",
                input_data=[
                    {'name': 'Phone', 'category': 'electronics', 'base_price': 800},
                    {'name': 'Jeans', 'category': 'apparel', 'base_price': 60},
                    {'name': 'Headphones', 'category': 'electronics', 'base_price': 150},
                ],
                output_data=[
                    {'name': 'Phone', 'category': 'electronics', 'base_price': 800, 'final_price': 725.0},
                    {'name': 'Jeans', 'category': 'apparel', 'base_price': 60, 'final_price': 62.0},
                    {'name': 'Headphones', 'category': 'electronics', 'base_price': 150, 'final_price': 140.0},
                ],
                description="Same pricing rules, different products"
            ),
            Problem(
                name="iterative_pricing_all_electronics",
                problem_type="transformation",
                input_data=[
                    {'name': 'Monitor', 'category': 'electronics', 'base_price': 300},
                    {'name': 'Keyboard', 'category': 'electronics', 'base_price': 50},
                ],
                output_data=[
                    {'name': 'Monitor', 'category': 'electronics', 'base_price': 300, 'final_price': 275.0},
                    {'name': 'Keyboard', 'category': 'electronics', 'base_price': 50, 'final_price': 50.0},
                ],
                description="All electronics case"
            ),
            Problem(
                name="iterative_pricing_mixed",
                problem_type="transformation",
                input_data=[
                    {'name': 'Sweater', 'category': 'apparel', 'base_price': 45},
                    {'name': 'Toy', 'category': 'other', 'base_price': 20},
                    {'name': 'Tablet', 'category': 'electronics', 'base_price': 400},
                ],
                output_data=[
                    {'name': 'Sweater', 'category': 'apparel', 'base_price': 45, 'final_price': 47.75},
                    {'name': 'Toy', 'category': 'other', 'base_price': 20, 'final_price': 24.6},
                    {'name': 'Tablet', 'category': 'electronics', 'base_price': 400, 'final_price': 365.0},
                ],
                description="Mixed categories"
            ),
        ]
    
    def generate_simple_iteration_curriculum(self) -> List[Problem]:
        """Simpler version: just add a fixed markup to each item."""
        print("Generating curriculum for simple iteration...")
        
        return [
            Problem(
                name="simple_markup_1",
                problem_type="transformation",
                input_data=[
                    {'product': 'A', 'cost': 10},
                    {'product': 'B', 'cost': 20},
                    {'product': 'C', 'cost': 15},
                ],
                output_data=[
                    {'product': 'A', 'cost': 10, 'price': 12},
                    {'product': 'B', 'cost': 20, 'price': 22},
                    {'product': 'C', 'cost': 15, 'price': 17},
                ],
                description="Add $2 markup to each product"
            ),
        ]