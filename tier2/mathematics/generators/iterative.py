"""
Iterative Curriculum Generator - Learning through repetition and refinement.

This module generates curricula that use iterative refinement and
spaced repetition for deep learning.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import random
import logging

logger = logging.getLogger(__name__)


@dataclass
class IterationCycle:
    """Represents one iteration cycle in learning."""
    cycle_number: int
    focus_concepts: List[str]
    depth_level: int  # 1-5, increasing depth
    variation_type: str  # "context", "complexity", "abstraction"
    exercises: List[Dict[str, Any]]
    review_items: List[str]
    
    
@dataclass
class SpacedRepetitionItem:
    """Item for spaced repetition scheduling."""
    concept: str
    last_reviewed: datetime
    next_review: datetime
    review_count: int
    ease_factor: float  # 1.3 to 2.5
    interval_days: float
    performance_history: List[float] = field(default_factory=list)
    
    def update_schedule(self, performance: float):
        """Update spaced repetition schedule based on performance."""
        # SuperMemo 2 algorithm adaptation
        if performance >= 0.6:
            if self.review_count == 0:
                self.interval_days = 1
            elif self.review_count == 1:
                self.interval_days = 6
            else:
                self.interval_days *= self.ease_factor
                
            # Update ease factor
            self.ease_factor += (0.1 - (5 - performance * 5) * (0.08 + (5 - performance * 5) * 0.02))
            self.ease_factor = max(1.3, self.ease_factor)
        else:
            # Failed - reset interval
            self.interval_days = 1
            self.review_count = 0
            
        self.last_reviewed = datetime.now()
        self.next_review = self.last_reviewed + timedelta(days=self.interval_days)
        self.review_count += 1
        self.performance_history.append(performance)


@dataclass
class IterativeLesson:
    """A lesson designed for iterative learning."""
    id: str
    iteration: int
    concepts: List[str]
    content: Dict[str, Any]
    exercises: List[Dict[str, Any]]
    connections_to_previous: List[str]
    estimated_time: float  # minutes
    mastery_criteria: Dict[str, float]


class IterativeCurriculumGenerator:
    """
    Generates curricula based on iterative refinement principles.
    
    This generator creates learning cycles that revisit concepts with
    increasing depth and different perspectives.
    """
    
    def __init__(self):
        self.repetition_schedule: Dict[str, SpacedRepetitionItem] = {}
        self.concept_iterations: Dict[str, int] = {}
        self.variation_strategies = self._init_variation_strategies()
        
    def _init_variation_strategies(self) -> Dict[str, callable]:
        """Initialize strategies for varying content across iterations."""
        return {
            "context": self._vary_by_context,
            "complexity": self._vary_by_complexity,
            "abstraction": self._vary_by_abstraction,
            "application": self._vary_by_application,
            "integration": self._vary_by_integration
        }
        
    def generate_iterative_curriculum(self, concepts: List[str],
                                    num_iterations: int = 3,
                                    days_total: int = 30) -> List[IterativeLesson]:
        """
        Generate curriculum with iterative cycles.
        
        Args:
            concepts: Concepts to learn
            num_iterations: Number of iteration cycles
            days_total: Total days for curriculum
            
        Returns:
            List of iterative lessons
        """
        lessons = []
        
        # Initialize spaced repetition for all concepts
        for concept in concepts:
            self.repetition_schedule[concept] = SpacedRepetitionItem(
                concept=concept,
                last_reviewed=datetime.now(),
                next_review=datetime.now(),
                review_count=0,
                ease_factor=2.5,
                interval_days=0
            )
            
        # Generate iteration cycles
        for iteration in range(num_iterations):
            cycle = self._generate_iteration_cycle(
                concepts, iteration, num_iterations
            )
            
            # Convert cycle to lessons
            cycle_lessons = self._cycle_to_lessons(cycle, iteration)
            lessons.extend(cycle_lessons)
            
        # Add spaced repetition reviews
        review_lessons = self._generate_review_lessons(days_total)
        lessons.extend(review_lessons)
        
        # Sort by optimal learning order
        lessons = self._optimize_lesson_order(lessons)
        
        return lessons
        
    def generate_spiral_curriculum(self, concepts: List[str],
                                 spirals: int = 4) -> List[IterativeLesson]:
        """
        Generate spiral curriculum that revisits topics with increasing sophistication.
        
        Args:
            concepts: Core concepts
            spirals: Number of spiral iterations
            
        Returns:
            Spiral curriculum lessons
        """
        lessons = []
        
        for spiral in range(spirals):
            # Each spiral covers all concepts at increasing depth
            spiral_depth = (spiral + 1) / spirals
            
            for i, concept in enumerate(concepts):
                # Determine prerequisites from previous spirals
                prereqs = []
                if spiral > 0:
                    prereqs = [f"{c}_spiral_{spiral-1}" for c in concepts[:i]]
                    
                lesson = self._create_spiral_lesson(
                    concept, spiral, spiral_depth, prereqs
                )
                lessons.append(lesson)
                
        return lessons
        
    def generate_mastery_cycles(self, skill: str,
                              target_mastery: float = 0.9) -> List[IterativeLesson]:
        """
        Generate focused cycles for mastering a specific skill.
        
        Args:
            skill: Skill to master
            target_mastery: Target mastery level
            
        Returns:
            Mastery-focused lessons
        """
        lessons = []
        current_mastery = 0.0
        cycle = 0
        
        while current_mastery < target_mastery and cycle < 10:
            # Estimate current mastery
            current_mastery = self._estimate_mastery(skill, cycle)
            
            # Generate appropriate exercises
            if current_mastery < 0.3:
                lesson_type = "foundational"
            elif current_mastery < 0.6:
                lesson_type = "practice"
            elif current_mastery < 0.8:
                lesson_type = "application"
            else:
                lesson_type = "mastery"
                
            lesson = self._create_mastery_lesson(
                skill, cycle, lesson_type, current_mastery
            )
            lessons.append(lesson)
            
            cycle += 1
            
        return lessons
        
    def update_performance(self, concept: str, performance: float):
        """Update performance for spaced repetition."""
        if concept in self.repetition_schedule:
            self.repetition_schedule[concept].update_schedule(performance)
            
    def get_due_reviews(self, date: Optional[datetime] = None) -> List[str]:
        """Get concepts due for review."""
        check_date = date or datetime.now()
        due_concepts = []
        
        for concept, item in self.repetition_schedule.items():
            if item.next_review <= check_date:
                due_concepts.append(concept)
                
        return due_concepts
        
    def _generate_iteration_cycle(self, concepts: List[str],
                                iteration: int,
                                total_iterations: int) -> IterationCycle:
        """Generate one iteration cycle."""
        # Determine focus based on iteration
        if iteration == 0:
            # First iteration: basics
            focus = concepts[:len(concepts)//2]
            depth = 1
            variation = "context"
        elif iteration < total_iterations - 1:
            # Middle iterations: building
            focus = concepts
            depth = 2 + iteration
            variation = random.choice(["complexity", "abstraction"])
        else:
            # Final iteration: integration
            focus = concepts
            depth = 5
            variation = "integration"
            
        # Generate exercises with appropriate difficulty
        exercises = self._generate_cycle_exercises(focus, depth, variation)
        
        # Determine review items
        review_items = self._select_review_items(concepts, iteration)
        
        return IterationCycle(
            cycle_number=iteration,
            focus_concepts=focus,
            depth_level=depth,
            variation_type=variation,
            exercises=exercises,
            review_items=review_items
        )
        
    def _cycle_to_lessons(self, cycle: IterationCycle,
                        iteration: int) -> List[IterativeLesson]:
        """Convert iteration cycle to lessons."""
        lessons = []
        
        # Group concepts for lessons
        concept_groups = self._group_concepts_for_lessons(
            cycle.focus_concepts, cycle.depth_level
        )
        
        for i, concept_group in enumerate(concept_groups):
            # Create lesson content
            content = self._create_lesson_content(
                concept_group, cycle.depth_level, cycle.variation_type
            )
            
            # Select exercises for this lesson
            num_exercises = min(5, len(cycle.exercises) // len(concept_groups))
            lesson_exercises = cycle.exercises[i*num_exercises:(i+1)*num_exercises]
            
            # Determine connections
            connections = []
            if iteration > 0:
                connections = [f"iteration_{iteration-1}_lesson_{i}"]
                
            lesson = IterativeLesson(
                id=f"iter_{iteration}_lesson_{i}",
                iteration=iteration,
                concepts=concept_group,
                content=content,
                exercises=lesson_exercises,
                connections_to_previous=connections,
                estimated_time=self._estimate_lesson_time(concept_group, cycle.depth_level),
                mastery_criteria=self._define_mastery_criteria(cycle.depth_level)
            )
            
            lessons.append(lesson)
            
        return lessons
        
    def _generate_cycle_exercises(self, concepts: List[str],
                                depth: int,
                                variation: str) -> List[Dict[str, Any]]:
        """Generate exercises for a cycle."""
        exercises = []
        
        # Base number of exercises increases with depth
        num_exercises = 3 + depth * 2
        
        for i in range(num_exercises):
            concept = random.choice(concepts)
            
            # Vary exercise type by depth
            if depth <= 2:
                exercise_types = ["recognition", "recall", "basic_application"]
            elif depth <= 4:
                exercise_types = ["application", "analysis", "synthesis"]
            else:
                exercise_types = ["synthesis", "evaluation", "creation"]
                
            exercise = {
                "id": f"exercise_{i}",
                "concept": concept,
                "type": random.choice(exercise_types),
                "variation": variation,
                "difficulty": 0.2 + (depth / 5) * 0.6,
                "estimated_time": 5 + depth * 2,
                "content": self._generate_exercise_content(concept, variation)
            }
            
            exercises.append(exercise)
            
        return exercises
        
    def _select_review_items(self, all_concepts: List[str],
                           iteration: int) -> List[str]:
        """Select items for review in this iteration."""
        if iteration == 0:
            return []  # No review in first iteration
            
        # Select concepts based on spaced repetition
        due_concepts = self.get_due_reviews()
        
        # Also include some random review
        other_concepts = [c for c in all_concepts if c not in due_concepts]
        num_random = min(2, len(other_concepts))
        random_review = random.sample(other_concepts, num_random) if other_concepts else []
        
        return due_concepts + random_review
        
    def _group_concepts_for_lessons(self, concepts: List[str],
                                  depth: int) -> List[List[str]]:
        """Group concepts into lessons."""
        # Fewer concepts per lesson at higher depth
        concepts_per_lesson = max(1, 5 - depth)
        
        groups = []
        for i in range(0, len(concepts), concepts_per_lesson):
            groups.append(concepts[i:i+concepts_per_lesson])
            
        return groups
        
    def _create_lesson_content(self, concepts: List[str],
                             depth: int,
                             variation: str) -> Dict[str, Any]:
        """Create content for a lesson."""
        # Apply variation strategy
        variation_func = self.variation_strategies.get(variation, self._vary_by_context)
        
        base_content = {
            "concepts": concepts,
            "depth": depth,
            "objectives": [f"Understand {c} at level {depth}" for c in concepts],
            "key_points": [f"Key point about {c}" for c in concepts]
        }
        
        # Apply variation
        varied_content = variation_func(base_content, concepts, depth)
        
        return varied_content
        
    def _vary_by_context(self, content: Dict[str, Any],
                       concepts: List[str], depth: int) -> Dict[str, Any]:
        """Vary content by changing context."""
        contexts = ["academic", "practical", "creative", "analytical"]
        content["context"] = contexts[depth % len(contexts)]
        content["examples"] = [
            f"{concept} in {content['context']} context"
            for concept in concepts
        ]
        return content
        
    def _vary_by_complexity(self, content: Dict[str, Any],
                          concepts: List[str], depth: int) -> Dict[str, Any]:
        """Vary content by increasing complexity."""
        content["complexity_level"] = depth
        content["composite_problems"] = depth > 2
        content["edge_cases"] = depth > 3
        content["optimization_required"] = depth > 4
        return content
        
    def _vary_by_abstraction(self, content: Dict[str, Any],
                           concepts: List[str], depth: int) -> Dict[str, Any]:
        """Vary content by level of abstraction."""
        if depth <= 2:
            content["level"] = "concrete"
            content["use_examples"] = True
            content["use_visualizations"] = True
        elif depth <= 4:
            content["level"] = "semi-abstract"
            content["use_patterns"] = True
            content["generalize"] = True
        else:
            content["level"] = "abstract"
            content["use_proofs"] = True
            content["theoretical"] = True
        return content
        
    def _vary_by_application(self, content: Dict[str, Any],
                           concepts: List[str], depth: int) -> Dict[str, Any]:
        """Vary content by application domain."""
        domains = ["games", "data_analysis", "web", "science", "art"]
        content["application_domain"] = domains[depth % len(domains)]
        content["real_world_project"] = depth > 2
        return content
        
    def _vary_by_integration(self, content: Dict[str, Any],
                           concepts: List[str], depth: int) -> Dict[str, Any]:
        """Vary content by integrating concepts."""
        content["integration_required"] = True
        content["cross_concept_problems"] = True
        content["synthesis_tasks"] = [
            f"Combine {concepts[i]} with {concepts[(i+1)%len(concepts)]}"
            for i in range(len(concepts))
        ]
        return content
        
    def _generate_exercise_content(self, concept: str,
                                 variation: str) -> Dict[str, Any]:
        """Generate exercise content."""
        templates = {
            "context": {
                "prompt": f"Apply {concept} in a new context",
                "scaffold": "Consider how this works differently here"
            },
            "complexity": {
                "prompt": f"Solve this complex {concept} problem",
                "scaffold": "Break it down into steps"
            },
            "abstraction": {
                "prompt": f"Generalize {concept} to abstract case",
                "scaffold": "What patterns do you see?"
            },
            "application": {
                "prompt": f"Build something using {concept}",
                "scaffold": "Start with the requirements"
            },
            "integration": {
                "prompt": f"Combine {concept} with other concepts",
                "scaffold": "How do they work together?"
            }
        }
        
        return templates.get(variation, templates["context"])
        
    def _estimate_lesson_time(self, concepts: List[str], depth: int) -> float:
        """Estimate time for lesson in minutes."""
        base_time = 15
        time_per_concept = 10
        depth_multiplier = 1 + (depth - 1) * 0.3
        
        return (base_time + len(concepts) * time_per_concept) * depth_multiplier
        
    def _define_mastery_criteria(self, depth: int) -> Dict[str, float]:
        """Define mastery criteria for depth level."""
        base_criteria = 0.6 + depth * 0.08  # Higher criteria for deeper content
        
        return {
            "exercises": min(0.95, base_criteria),
            "concepts": min(0.9, base_criteria - 0.05),
            "integration": min(0.85, base_criteria - 0.1) if depth > 3 else 0.0
        }
        
    def _generate_review_lessons(self, days_total: int) -> List[IterativeLesson]:
        """Generate spaced review lessons."""
        review_lessons = []
        
        for day in range(days_total):
            current_date = datetime.now() + timedelta(days=day)
            due_concepts = self.get_due_reviews(current_date)
            
            if due_concepts:
                # Group into review session
                lesson = IterativeLesson(
                    id=f"review_day_{day}",
                    iteration=-1,  # Special marker for review
                    concepts=due_concepts[:5],  # Max 5 per session
                    content={
                        "type": "review",
                        "quick_recall": True,
                        "mixed_practice": True
                    },
                    exercises=self._generate_review_exercises(due_concepts[:5]),
                    connections_to_previous=[],
                    estimated_time=5.0 * len(due_concepts[:5]),
                    mastery_criteria={"recall": 0.8}
                )
                
                review_lessons.append(lesson)
                
        return review_lessons
        
    def _generate_review_exercises(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Generate review exercises."""
        exercises = []
        
        for concept in concepts:
            exercise = {
                "id": f"review_{concept}",
                "concept": concept,
                "type": "quick_recall",
                "difficulty": 0.5,
                "estimated_time": 5,
                "content": {
                    "prompt": f"Quick review of {concept}",
                    "format": random.choice(["multiple_choice", "fill_blank", "short_answer"])
                }
            }
            exercises.append(exercise)
            
        return exercises
        
    def _optimize_lesson_order(self, lessons: List[IterativeLesson]) -> List[IterativeLesson]:
        """Optimize order of lessons for learning."""
        # Separate regular and review lessons
        regular_lessons = [l for l in lessons if l.iteration >= 0]
        review_lessons = [l for l in lessons if l.iteration < 0]
        
        # Sort regular lessons by iteration and complexity
        regular_lessons.sort(key=lambda l: (l.iteration, len(l.concepts)))
        
        # Interleave review lessons
        optimized = []
        review_index = 0
        
        for i, lesson in enumerate(regular_lessons):
            optimized.append(lesson)
            
            # Add review lessons at appropriate intervals
            if i % 3 == 2 and review_index < len(review_lessons):
                optimized.append(review_lessons[review_index])
                review_index += 1
                
        # Add remaining review lessons
        optimized.extend(review_lessons[review_index:])
        
        return optimized
        
    def _create_spiral_lesson(self, concept: str, spiral: int,
                            depth: float, prerequisites: List[str]) -> IterativeLesson:
        """Create lesson for spiral curriculum."""
        # Content increases in sophistication
        if depth < 0.25:
            content_type = "introduction"
        elif depth < 0.5:
            content_type = "exploration"
        elif depth < 0.75:
            content_type = "application"
        else:
            content_type = "mastery"
            
        return IterativeLesson(
            id=f"{concept}_spiral_{spiral}",
            iteration=spiral,
            concepts=[concept],
            content={
                "type": content_type,
                "spiral_level": spiral,
                "builds_on": prerequisites,
                "depth": depth,
                "approach": self._get_spiral_approach(spiral)
            },
            exercises=self._generate_spiral_exercises(concept, spiral, depth),
            connections_to_previous=prerequisites,
            estimated_time=20 + spiral * 10,
            mastery_criteria={
                "understanding": 0.7 + depth * 0.2,
                "application": 0.6 + depth * 0.3
            }
        )
        
    def _get_spiral_approach(self, spiral: int) -> str:
        """Get teaching approach for spiral."""
        approaches = ["concrete", "representational", "abstract", "integrated"]
        return approaches[min(spiral, len(approaches) - 1)]
        
    def _generate_spiral_exercises(self, concept: str, spiral: int,
                                 depth: float) -> List[Dict[str, Any]]:
        """Generate exercises for spiral curriculum."""
        num_exercises = 2 + spiral
        exercises = []
        
        for i in range(num_exercises):
            exercise_depth = depth * (0.8 + i * 0.2 / num_exercises)
            
            exercise = {
                "id": f"{concept}_spiral_{spiral}_ex_{i}",
                "concept": concept,
                "spiral": spiral,
                "type": self._get_exercise_type_for_depth(exercise_depth),
                "difficulty": exercise_depth,
                "builds_on_previous": spiral > 0,
                "content": {
                    "prompt": f"Exercise for {concept} at spiral {spiral}",
                    "scaffolding": 1 - exercise_depth  # More help at lower depths
                }
            }
            
            exercises.append(exercise)
            
        return exercises
        
    def _get_exercise_type_for_depth(self, depth: float) -> str:
        """Get appropriate exercise type for depth."""
        if depth < 0.3:
            return "identification"
        elif depth < 0.5:
            return "explanation"
        elif depth < 0.7:
            return "application"
        elif depth < 0.9:
            return "analysis"
        else:
            return "creation"
            
    def _estimate_mastery(self, skill: str, cycle: int) -> float:
        """Estimate current mastery level."""
        # Simple model: logarithmic growth with diminishing returns
        base_growth = 0.3
        growth_rate = 0.7
        
        estimated = base_growth * (1 - math.exp(-growth_rate * cycle))
        
        # Add some randomness
        estimated += random.uniform(-0.05, 0.05)
        
        return max(0.0, min(1.0, estimated))
        
    def _create_mastery_lesson(self, skill: str, cycle: int,
                             lesson_type: str,
                             current_mastery: float) -> IterativeLesson:
        """Create lesson focused on mastery."""
        content_map = {
            "foundational": {
                "focus": "basics",
                "repetition": "high",
                "variation": "low"
            },
            "practice": {
                "focus": "fluency",
                "repetition": "medium",
                "variation": "medium"
            },
            "application": {
                "focus": "transfer",
                "repetition": "low",
                "variation": "high"
            },
            "mastery": {
                "focus": "expertise",
                "repetition": "spaced",
                "variation": "creative"
            }
        }
        
        content = content_map.get(lesson_type, content_map["practice"])
        content["skill"] = skill
        content["current_mastery"] = current_mastery
        
        return IterativeLesson(
            id=f"mastery_{skill}_cycle_{cycle}",
            iteration=cycle,
            concepts=[skill],
            content=content,
            exercises=self._generate_mastery_exercises(skill, lesson_type, cycle),
            connections_to_previous=[f"mastery_{skill}_cycle_{cycle-1}"] if cycle > 0 else [],
            estimated_time=30 + cycle * 5,
            mastery_criteria={
                "accuracy": 0.9,
                "speed": 0.8,
                "retention": 0.85
            }
        )
        
    def _generate_mastery_exercises(self, skill: str, lesson_type: str,
                                   cycle: int) -> List[Dict[str, Any]]:
        """Generate exercises for mastery lesson."""
        exercise_counts = {
            "foundational": 10,
            "practice": 15,
            "application": 8,
            "mastery": 5
        }
        
        num_exercises = exercise_counts.get(lesson_type, 10)
        exercises = []
        
        for i in range(num_exercises):
            exercise = {
                "id": f"mastery_{skill}_{cycle}_{i}",
                "skill": skill,
                "type": lesson_type,
                "variation": i,  # Each exercise is slightly different
                "difficulty": 0.5 + (cycle * 0.1),
                "timed": lesson_type in ["practice", "mastery"],
                "adaptive": True  # Adjusts based on performance
            }
            
            exercises.append(exercise)
            
        return exercises