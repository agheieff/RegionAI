"""
Curriculum for teaching the AI to filter and aggregate structured data.
"""
import torch
from typing import List
from .problem import Problem


class StructuredSumCurriculumGenerator:
    """
    Teaches the AI to filter a list of objects and then aggregate a value from them.
    Problem: Find the total age of all 'admin' users.
    Required Composition: FILTER_BY_VALUE -> MAP_GET -> SUM
    """
    
    def generate_structured_sum_curriculum(self) -> List[Problem]:
        """Generates problems for learning structured data aggregation."""
        print("Generating curriculum for structured aggregation...")
        
        return [
            Problem(
                name="sum_admin_ages_1",
                problem_type="transformation",
                input_data=[
                    {'name': 'Alice', 'role': 'admin', 'age': 42},
                    {'name': 'Bob', 'role': 'user', 'age': 25},
                    {'name': 'Charlie', 'role': 'admin', 'age': 37},
                    {'name': 'David', 'role': 'user', 'age': 50},
                ],
                output_data=torch.tensor([79.0], dtype=torch.float32),  # 42 + 37
                description="Sum of ages for all admin users (set 1)"
            ),
            Problem(
                name="sum_admin_ages_2",
                problem_type="transformation",
                input_data=[
                    {'name': 'Eve', 'role': 'user', 'age': 21},
                    {'name': 'Frank', 'role': 'admin', 'age': 22},
                    {'name': 'Grace', 'role': 'user', 'age': 33},
                    {'name': 'Henry', 'role': 'admin', 'age': 58},
                ],
                output_data=torch.tensor([80.0], dtype=torch.float32),  # 22 + 58
                description="Sum of ages for all admin users (set 2)"
            ),
            Problem(
                name="sum_admin_ages_empty",
                problem_type="transformation",
                input_data=[
                    {'name': 'Ivan', 'role': 'user', 'age': 30},
                    {'name': 'Jane', 'role': 'user', 'age': 45},
                ],
                output_data=torch.tensor([0.0], dtype=torch.float32),  # No admins
                description="Sum of ages when no admin users exist"
            ),
        ]
    
    def generate_moderator_sum_curriculum(self) -> List[Problem]:
        """Variation: sum ages of moderators instead of admins."""
        print("Generating curriculum for moderator aggregation...")
        
        return [
            Problem(
                name="sum_moderator_ages_1",
                problem_type="transformation",
                input_data=[
                    {'name': 'Kate', 'role': 'moderator', 'age': 35},
                    {'name': 'Liam', 'role': 'admin', 'age': 45},
                    {'name': 'Mary', 'role': 'user', 'age': 25},
                    {'name': 'Nick', 'role': 'moderator', 'age': 40},
                ],
                output_data=torch.tensor([75.0], dtype=torch.float32),  # 35 + 40
                description="Sum of ages for all moderator users"
            ),
        ]