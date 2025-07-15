from dataclasses import dataclass
import torch
import ast
from typing import Union, List, Dict, Any

# A more flexible type for our problem inputs and outputs
ProblemDataType = Union[torch.Tensor, List[Dict[str, Any]], int, float, ast.AST]

@dataclass
class Problem:
    """
    A simple, structured container for a single task.
    """
    name: str
    problem_type: str
    input_data: ProblemDataType
    output_data: ProblemDataType
    description: str
