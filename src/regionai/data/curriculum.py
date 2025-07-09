import torch
from .problem import Problem

class CurriculumGenerator:
    """
    A curriculum generator that loads a pre-defined set of problems.
    """

    def generate_reverse_curriculum(self) -> list[Problem]:
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
