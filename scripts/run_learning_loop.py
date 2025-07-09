#!/usr/bin/env python3
"""
This script runs the main concept discovery loop to test and demonstrate
the system's ability to learn from failure.
"""

import torch
import sys
import os
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from regionai.spaces.concept_space import ConceptSpaceND
from regionai.engine.main import ReasoningEngine
from regionai.data.curriculum import CurriculumGenerator
from regionai.discovery.discover import discover_concept_from_failures  # This file will be created next

def main():
    """Main function to run the learning loop."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run the RegionAI learning loop with different curricula."
    )
    parser.add_argument(
        "--curriculum",
        type=str,
        default="sum",
        choices=["reverse", "sum", "sort_desc", "sum_large"],
        help="Which curriculum to use for learning (default: sum)"
    )
    args = parser.parse_args()
    
    print("--- Initializing The Learning Environment ---")
    # 1. Initialize all components
    # For now, our space is empty of transformations
    concept_space = ConceptSpaceND()
    engine = ReasoningEngine(concept_space)
    curriculum_generator = CurriculumGenerator()
    
    # 2. Get the curriculum for a problem the system cannot solve yet
    curriculum_methods = {
        "reverse": curriculum_generator.generate_reverse_curriculum,
        "sum": curriculum_generator.generate_sum_curriculum,
        "sort_desc": curriculum_generator.generate_sort_desc_curriculum,
        "sum_large": curriculum_generator.generate_sum_of_large_elements_curriculum,
    }
    
    if args.curriculum not in curriculum_methods:
        print(f"Error: Unknown curriculum '{args.curriculum}'")
        print(f"Available curricula: {', '.join(curriculum_methods.keys())}")
        sys.exit(1)
    
    problem_curriculum = curriculum_methods[args.curriculum]()
    print(f"Loaded a curriculum of {len(problem_curriculum)} '{args.curriculum}' problems.")
    
    # 3. Create a list to store problems the engine fails to solve
    unsolved_problems = []
    
    # --- Phase 1: Initial Problem-Solving Attempt ---
    print("\n--- Phase 1: Attempting to solve problems with existing knowledge ---")
    for problem in problem_curriculum:
        solution = engine.solve_problem(problem)
        if solution is None:
            print(f"    [FAIL] Problem '{problem.name}'")
            unsolved_problems.append(problem)
        else:
            print(f"    [SUCCESS] Problem '{problem.name}' solved by {solution.solving_concept.name}")
    
    # 4. Summarize the initial failure
    print(f"\n--- Phase 1 Summary: {len(unsolved_problems)}/{len(problem_curriculum)} problems are unsolved. ---")
    
    if not unsolved_problems:
        print("No failures to learn from. Exiting.")
        return
    
    # --- Phase 2: Concept Discovery ---
    new_concept = discover_concept_from_failures(unsolved_problems)
    
    # 3. Add the new concept to the system's knowledge base
    if new_concept:
        concept_space.add_region(new_concept.name, new_concept)
        print(f">>> Aha! ✨ New concept '{new_concept.name}' was discovered and added to the Concept Space. <<<\n")
    else:
        print("\n--- No new concept was discovered. Learning cycle ends. ---")
        return
    
    # --- Phase 3: Second Attempt with New Knowledge ---
    print("--- Phase 3: Re-attempting previously unsolved problems ---")
    successfully_solved_after_learning = 0
    for problem in unsolved_problems:
        solution = engine.solve_problem(problem)
        if solution is not None:
            print(f"    [SUCCESS] Problem '{problem.name}' solved by new concept '{solution.solving_concept.name}'")
            successfully_solved_after_learning += 1
        else:
            print(f"    [FAIL] Problem '{problem.name}' still unsolved.")
    
    print(f"\n--- Final Summary: {successfully_solved_after_learning}/{len(unsolved_problems)} of the previously failed problems were solved. ---")

if __name__ == "__main__":
    main()