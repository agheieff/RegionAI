"""
Curriculum for teaching conditional transformations (if/else logic).
"""
import torch
from typing import List, Dict, Any
from .problem import Problem


class ConditionalBonusCurriculumGenerator:
    """
    Teaches the AI to apply different transformations based on conditions.
    Problem: Apply a 10% bonus to engineers, 3% to everyone else.
    Required Structure:
    IF (VALUE_EQUALS('role', 'engineer')):
        Apply 10% salary increase
    ELSE:
        Apply 3% salary increase
    """
    
    def generate_conditional_bonus_curriculum(self) -> List[Problem]:
        """Generates problems for learning conditional salary bonuses."""
        print("Generating curriculum for conditional transformations...")
        
        return [
            Problem(
                name="conditional_bonus_1",
                problem_type="transformation",
                input_data=[
                    {'name': 'Alice', 'role': 'engineer', 'salary': 100000},
                    {'name': 'Bob', 'role': 'sales', 'salary': 90000},
                    {'name': 'Charlie', 'role': 'engineer', 'salary': 120000},
                    {'name': 'David', 'role': 'support', 'salary': 60000},
                ],
                output_data=[
                    {'name': 'Alice', 'role': 'engineer', 'salary': 110000.0},
                    {'name': 'Bob', 'role': 'sales', 'salary': 92700.0},
                    {'name': 'Charlie', 'role': 'engineer', 'salary': 132000.0},
                    {'name': 'David', 'role': 'support', 'salary': 61800.0},
                ],
                description="Apply 10% bonus to engineers, 3% to others"
            ),
            Problem(
                name="conditional_bonus_2",
                problem_type="transformation",
                input_data=[
                    {'name': 'Eve', 'role': 'support', 'salary': 70000},
                    {'name': 'Frank', 'role': 'engineer', 'salary': 150000},
                    {'name': 'Grace', 'role': 'engineer', 'salary': 130000},
                    {'name': 'Henry', 'role': 'sales', 'salary': 85000},
                ],
                output_data=[
                    {'name': 'Eve', 'role': 'support', 'salary': 72100.0},
                    {'name': 'Frank', 'role': 'engineer', 'salary': 165000.0},
                    {'name': 'Grace', 'role': 'engineer', 'salary': 143000.0},
                    {'name': 'Henry', 'role': 'sales', 'salary': 87550.0},
                ],
                description="Apply 10% bonus to engineers, 3% to others (set 2)"
            ),
            Problem(
                name="conditional_bonus_all_engineers",
                problem_type="transformation",
                input_data=[
                    {'name': 'Ivan', 'role': 'engineer', 'salary': 110000},
                    {'name': 'Jane', 'role': 'engineer', 'salary': 140000},
                ],
                output_data=[
                    {'name': 'Ivan', 'role': 'engineer', 'salary': 121000.0},
                    {'name': 'Jane', 'role': 'engineer', 'salary': 154000.0},
                ],
                description="All engineers case"
            ),
            Problem(
                name="conditional_bonus_no_engineers",
                problem_type="transformation",
                input_data=[
                    {'name': 'Kate', 'role': 'sales', 'salary': 95000},
                    {'name': 'Liam', 'role': 'support', 'salary': 65000},
                ],
                output_data=[
                    {'name': 'Kate', 'role': 'sales', 'salary': 97850.0},
                    {'name': 'Liam', 'role': 'support', 'salary': 66950.0},
                ],
                description="No engineers case"
            ),
        ]
    
    def generate_manager_bonus_curriculum(self) -> List[Problem]:
        """Variation: 15% bonus for managers, 5% for others."""
        print("Generating curriculum for manager bonus transformations...")
        
        return [
            Problem(
                name="manager_bonus_1",
                problem_type="transformation",
                input_data=[
                    {'name': 'Mary', 'role': 'manager', 'salary': 120000},
                    {'name': 'Nick', 'role': 'developer', 'salary': 100000},
                    {'name': 'Olivia', 'role': 'manager', 'salary': 130000},
                ],
                output_data=[
                    {'name': 'Mary', 'role': 'manager', 'salary': 138000.0},
                    {'name': 'Nick', 'role': 'developer', 'salary': 105000.0},
                    {'name': 'Olivia', 'role': 'manager', 'salary': 149500.0},
                ],
                description="Apply 15% bonus to managers, 5% to others"
            ),
        ]