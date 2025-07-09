from dataclasses import dataclass
import torch

@dataclass
class Problem:
    """
    A simple, structured container for a single task.
    """
    name: str
    problem_type: str
    input_data: torch.Tensor
    output_data: torch.Tensor
    description: str
