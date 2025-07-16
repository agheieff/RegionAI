"""
Basic Curriculum Generator - Simple learning sequences.

This module generates basic curricula for fundamental concepts
and transformations.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random


@dataclass
class BasicLesson:
    """A basic lesson in the curriculum."""
    id: str
    title: str
    concept: str
    difficulty: float
    prerequisites: List[str]
    content: Dict[str, Any]
    exercises: List[Dict[str, Any]]
    
    
class BasicCurriculumGenerator:
    """
    Generates basic curricula for foundational learning.
    
    This generator creates simple, sequential lessons that build
    up from fundamental concepts to more complex ideas.
    """
    
    def __init__(self):
        self.concept_graph = self._build_concept_graph()
        self.lessons: Dict[str, BasicLesson] = {}
        
    def _build_concept_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph of concepts."""
        return {
            # Fundamental concepts
            "identity": [],
            "constant": [],
            "variable": [],
            
            # Basic operations
            "assignment": ["variable"],
            "arithmetic": ["constant", "variable"],
            "comparison": ["constant", "variable"],
            
            # Control flow
            "conditional": ["comparison"],
            "loop": ["comparison", "assignment"],
            "function": ["variable", "assignment"],
            
            # Data structures
            "list": ["variable"],
            "dictionary": ["variable"],
            "iteration": ["list", "loop"],
            
            # Advanced concepts
            "recursion": ["function", "conditional"],
            "higher_order": ["function", "list"],
            "composition": ["function"],
        }
        
    def generate_curriculum(self, target_concepts: List[str],
                          max_lessons: int = 20) -> List[BasicLesson]:
        """
        Generate a curriculum to learn target concepts.
        
        Args:
            target_concepts: Concepts to learn
            max_lessons: Maximum number of lessons
            
        Returns:
            Ordered list of lessons
        """
        # Find all required concepts (including prerequisites)
        required_concepts = self._find_required_concepts(target_concepts)
        
        # Order by dependencies
        ordered_concepts = self._topological_sort(required_concepts)
        
        # Generate lessons
        lessons = []
        for i, concept in enumerate(ordered_concepts[:max_lessons]):
            lesson = self._generate_lesson(concept, i)
            lessons.append(lesson)
            self.lessons[lesson.id] = lesson
            
        return lessons
        
    def generate_remedial_lessons(self, failed_concept: str,
                                num_lessons: int = 3) -> List[BasicLesson]:
        """
        Generate remedial lessons for a concept that wasn't mastered.
        
        Args:
            failed_concept: Concept that needs reinforcement
            num_lessons: Number of remedial lessons
            
        Returns:
            List of remedial lessons
        """
        remedial_lessons = []
        
        # Generate variations focusing on the difficult concept
        for i in range(num_lessons):
            lesson = self._generate_remedial_lesson(failed_concept, i)
            remedial_lessons.append(lesson)
            
        return remedial_lessons
        
    def generate_practice_set(self, concepts: List[str],
                            num_exercises: int = 10) -> List[Dict[str, Any]]:
        """
        Generate practice exercises for concepts.
        
        Args:
            concepts: Concepts to practice
            num_exercises: Number of exercises
            
        Returns:
            List of practice exercises
        """
        exercises = []
        
        for i in range(num_exercises):
            concept = random.choice(concepts)
            exercise = self._generate_exercise(concept, difficulty=random.random())
            exercises.append(exercise)
            
        return exercises
        
    def _find_required_concepts(self, targets: List[str]) -> set:
        """Find all concepts required (including prerequisites)."""
        required = set()
        to_process = list(targets)
        
        while to_process:
            concept = to_process.pop()
            if concept not in required:
                required.add(concept)
                prerequisites = self.concept_graph.get(concept, [])
                to_process.extend(prerequisites)
                
        return required
        
    def _topological_sort(self, concepts: set) -> List[str]:
        """Sort concepts by dependencies."""
        # Simple DFS-based topological sort
        visited = set()
        stack = []
        
        def visit(concept):
            if concept in visited:
                return
            visited.add(concept)
            
            for prereq in self.concept_graph.get(concept, []):
                if prereq in concepts:
                    visit(prereq)
                    
            stack.append(concept)
            
        for concept in concepts:
            visit(concept)
            
        return stack
        
    def _generate_lesson(self, concept: str, index: int) -> BasicLesson:
        """Generate a lesson for a concept."""
        prerequisites = self.concept_graph.get(concept, [])
        
        # Generate lesson content based on concept
        content = self._generate_content(concept)
        exercises = [self._generate_exercise(concept, 0.3 + i*0.1) 
                    for i in range(3)]
        
        return BasicLesson(
            id=f"basic_{index:03d}_{concept}",
            title=f"Introduction to {concept.replace('_', ' ').title()}",
            concept=concept,
            difficulty=0.1 + (index * 0.05),  # Gradually increase difficulty
            prerequisites=prerequisites,
            content=content,
            exercises=exercises
        )
        
    def _generate_content(self, concept: str) -> Dict[str, Any]:
        """Generate lesson content for a concept."""
        content_templates = {
            "identity": {
                "explanation": "The identity transformation returns its input unchanged",
                "example": "identity(x) = x",
                "code": "def identity(x): return x"
            },
            "constant": {
                "explanation": "Constants are fixed values that don't change",
                "example": "PI = 3.14159",
                "code": "CONSTANT_VALUE = 42"
            },
            "variable": {
                "explanation": "Variables store values that can change",
                "example": "x = 10; x = x + 1",
                "code": "count = 0\ncount += 1"
            },
            "assignment": {
                "explanation": "Assignment stores a value in a variable",
                "example": "x = 5",
                "code": "name = 'Alice'\nage = 30"
            },
            "arithmetic": {
                "explanation": "Arithmetic operations perform mathematical calculations",
                "example": "result = (a + b) * c",
                "code": "sum = 10 + 20\nproduct = sum * 2"
            },
            "comparison": {
                "explanation": "Comparisons test relationships between values",
                "example": "x > y",
                "code": "if age >= 18:\n    print('Adult')"
            },
            "conditional": {
                "explanation": "Conditionals execute code based on conditions",
                "example": "if condition then action",
                "code": "if score > 90:\n    grade = 'A'\nelse:\n    grade = 'B'"
            },
            "loop": {
                "explanation": "Loops repeat code multiple times",
                "example": "for each item in list",
                "code": "for i in range(5):\n    print(i)"
            },
            "function": {
                "explanation": "Functions encapsulate reusable code",
                "example": "f(x) = x * 2",
                "code": "def double(x):\n    return x * 2"
            },
            "list": {
                "explanation": "Lists store ordered collections of items",
                "example": "[1, 2, 3, 4, 5]",
                "code": "numbers = [1, 2, 3]\nnumbers.append(4)"
            },
            "dictionary": {
                "explanation": "Dictionaries store key-value pairs",
                "example": "{'name': 'Bob', 'age': 25}",
                "code": "person = {'name': 'Bob'}\nperson['age'] = 25"
            },
            "iteration": {
                "explanation": "Iteration processes each item in a collection",
                "example": "for each x in list: process(x)",
                "code": "for item in items:\n    process(item)"
            },
            "recursion": {
                "explanation": "Recursion is when a function calls itself",
                "example": "factorial(n) = n * factorial(n-1)",
                "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
            },
            "higher_order": {
                "explanation": "Higher-order functions operate on other functions",
                "example": "map(f, list)",
                "code": "doubled = list(map(lambda x: x*2, [1,2,3]))"
            },
            "composition": {
                "explanation": "Composition combines functions to create new ones",
                "example": "h(x) = f(g(x))",
                "code": "def compose(f, g):\n    return lambda x: f(g(x))"
            }
        }
        
        return content_templates.get(concept, {
            "explanation": f"Learn about {concept}",
            "example": f"Example of {concept}",
            "code": f"# Code for {concept}"
        })
        
    def _generate_exercise(self, concept: str, difficulty: float) -> Dict[str, Any]:
        """Generate an exercise for a concept."""
        exercise_types = ["implement", "trace", "debug", "extend"]
        exercise_type = random.choice(exercise_types)
        
        return {
            "type": exercise_type,
            "concept": concept,
            "difficulty": difficulty,
            "prompt": self._generate_exercise_prompt(concept, exercise_type),
            "starter_code": self._generate_starter_code(concept, exercise_type),
            "test_cases": self._generate_test_cases(concept, difficulty)
        }
        
    def _generate_exercise_prompt(self, concept: str, exercise_type: str) -> str:
        """Generate exercise prompt."""
        prompts = {
            "implement": f"Implement a function that demonstrates {concept}",
            "trace": f"Trace through this code and predict the output",
            "debug": f"Fix the bug in this {concept} implementation",
            "extend": f"Extend this code to handle additional cases"
        }
        return prompts.get(exercise_type, f"Practice {concept}")
        
    def _generate_starter_code(self, concept: str, exercise_type: str) -> str:
        """Generate starter code for exercise."""
        if exercise_type == "implement":
            return f"def {concept}_example(x):\n    # TODO: Implement {concept}\n    pass"
        elif exercise_type == "debug":
            return f"def buggy_{concept}(x):\n    # This code has a bug\n    return None"
        else:
            return f"# Code for {concept} exercise"
            
    def _generate_test_cases(self, concept: str, difficulty: float) -> List[Dict]:
        """Generate test cases for exercise."""
        num_tests = int(3 + difficulty * 5)
        return [
            {
                "input": f"test_input_{i}",
                "expected": f"expected_output_{i}",
                "description": f"Test case {i+1}"
            }
            for i in range(num_tests)
        ]
        
    def _generate_remedial_lesson(self, concept: str, variation: int) -> BasicLesson:
        """Generate a remedial lesson for a concept."""
        # Different approaches for the same concept
        approaches = ["visual", "concrete", "step_by_step", "analogy"]
        approach = approaches[variation % len(approaches)]
        
        content = {
            "approach": approach,
            "explanation": f"Let's try understanding {concept} with a {approach} approach",
            "extra_examples": [f"Example {i+1}" for i in range(5)],
            "common_mistakes": [f"Mistake {i+1}" for i in range(3)]
        }
        
        exercises = [
            self._generate_exercise(concept, 0.2)  # Easier exercises
            for _ in range(5)
        ]
        
        return BasicLesson(
            id=f"remedial_{concept}_{variation}",
            title=f"Remedial: {concept} ({approach} approach)",
            concept=concept,
            difficulty=0.1,  # Keep it simple
            prerequisites=self.concept_graph.get(concept, []),
            content=content,
            exercises=exercises
        )