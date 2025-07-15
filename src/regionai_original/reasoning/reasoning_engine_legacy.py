from dataclasses import dataclass
import torch
from ..data.problem import Problem
from ..geometry.region import RegionND
from ..spaces.concept_space import ConceptSpaceND

@dataclass
class Solution:
    """
    Represents a solution to a problem.
    """
    problem_solved: Problem
    solving_concept: RegionND


class ReasoningEngine:
    """
    The main reasoning engine.
    """

    def __init__(self, concept_space: ConceptSpaceND):
        self.concept_space = concept_space

    def solve_problem(self, problem: Problem) -> Solution | None:
        """
        Attempts to solve a given problem.
        """
        for concept_name, region in self.concept_space._regions.items():
            if region.region_type == "transformation":
                if region.transformation_function:
                    # Get the sequence from the concept
                    sequence = region.transformation_function
                    # Apply the full sequence of operations
                    result = sequence.apply(problem.input_data)
                    if torch.equal(result, problem.output_data):
                        return Solution(problem_solved=problem, solving_concept=region)
        return None
