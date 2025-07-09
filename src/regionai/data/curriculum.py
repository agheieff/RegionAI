import torch
from typing import List
from .problem import Problem

class CurriculumGenerator:
    """
    A curriculum generator that loads a pre-defined set of problems.
    """

    def generate_reverse_curriculum(self) -> List[Problem]:
        """
        Generates a curriculum for list reversal problems.
        """
        return [
            Problem(
                name="reverse_list_1",
                problem_type="transformation",
                input_data=torch.tensor([1, 2, 3]),
                output_data=torch.tensor([3, 2, 1]),
                description="Reverse a list of 3 unique elements.",
            ),
            Problem(
                name="reverse_list_2",
                problem_type="transformation",
                input_data=torch.tensor([10, 20]),
                output_data=torch.tensor([20, 10]),
                description="Reverse a list of 2 unique elements.",
            ),
            Problem(
                name="reverse_list_3",
                problem_type="transformation",
                input_data=torch.tensor([5, 5, 6]),
                output_data=torch.tensor([6, 5, 5]),
                description="Reverse a list with duplicate elements.",
            ),
        ]
    
    def generate_sum_curriculum(self) -> List[Problem]:
        """Generates a curriculum for learning the SUM operation."""
        print("Generating curriculum for 'SUM' operation...")
        return [
            Problem(
                name="sum_1",
                problem_type="transformation",
                input_data=torch.tensor([1, 1, 1], dtype=torch.float32),
                output_data=torch.tensor([3], dtype=torch.float32),
                description="1 + 1 + 1 = 3"
            ),
            Problem(
                name="sum_2",
                problem_type="transformation",
                input_data=torch.tensor([10, 5, 2], dtype=torch.float32),
                output_data=torch.tensor([17], dtype=torch.float32),
                description="10 + 5 + 2 = 17"
            ),
            Problem(
                name="sum_3",
                problem_type="transformation",
                input_data=torch.tensor([100], dtype=torch.float32),
                output_data=torch.tensor([100], dtype=torch.float32),
                description="Sum of a single element is the element itself."
            ),
            Problem(
                name="sum_4_negatives",
                problem_type="transformation",
                input_data=torch.tensor([-5, 5, -10], dtype=torch.float32),
                output_data=torch.tensor([-10], dtype=torch.float32),
                description="Sum with negative numbers."
            ),
        ]
