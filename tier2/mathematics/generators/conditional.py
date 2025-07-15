"""
Conditional Curriculum Generator - Adaptive learning paths.

This module generates curricula that adapt based on learner performance
and conditions.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LearnerState(Enum):
    """States of learner progress."""
    BEGINNER = "beginner"
    STRUGGLING = "struggling"
    PROGRESSING = "progressing"
    ADVANCED = "advanced"
    MASTERED = "mastered"


class ConceptMastery(Enum):
    """Levels of concept mastery."""
    NONE = 0
    EXPOSURE = 1
    FAMILIARITY = 2
    COMPETENCE = 3
    PROFICIENCY = 4
    MASTERY = 5


@dataclass
class LearnerProfile:
    """Profile tracking learner progress."""
    id: str
    concept_mastery: Dict[str, ConceptMastery] = field(default_factory=dict)
    performance_history: List[float] = field(default_factory=list)
    preferred_difficulty: float = 0.5
    learning_speed: float = 1.0
    struggle_areas: List[str] = field(default_factory=list)
    
    @property
    def overall_state(self) -> LearnerState:
        """Determine overall learner state."""
        if not self.performance_history:
            return LearnerState.BEGINNER
            
        recent_performance = sum(self.performance_history[-5:]) / min(5, len(self.performance_history))
        
        if recent_performance < 0.3:
            return LearnerState.STRUGGLING
        elif recent_performance < 0.6:
            return LearnerState.PROGRESSING
        elif recent_performance < 0.85:
            return LearnerState.ADVANCED
        else:
            return LearnerState.MASTERED


@dataclass
class ConditionalLesson:
    """A lesson with conditional paths."""
    id: str
    concept: str
    base_content: Dict[str, Any]
    conditional_content: Dict[str, Dict[str, Any]]  # condition -> content
    success_threshold: float
    next_lessons: Dict[str, str]  # outcome -> next_lesson_id
    adaptations: List[Dict[str, Any]] = field(default_factory=list)


class ConditionalCurriculumGenerator:
    """
    Generates adaptive curricula based on conditions and performance.
    
    This generator creates branching paths that adapt to learner
    needs and performance.
    """
    
    def __init__(self):
        self.learner_profiles: Dict[str, LearnerProfile] = {}
        self.lesson_graph: Dict[str, ConditionalLesson] = {}
        self.adaptation_rules: List[Callable] = []
        self._initialize_adaptation_rules()
        
    def _initialize_adaptation_rules(self):
        """Initialize rules for adapting curriculum."""
        # Rule: If struggling, provide more examples
        self.adaptation_rules.append(
            lambda profile, lesson: {
                "add_examples": True,
                "simplify_language": True
            } if profile.overall_state == LearnerState.STRUGGLING else None
        )
        
        # Rule: If advanced, add challenges
        self.adaptation_rules.append(
            lambda profile, lesson: {
                "add_challenges": True,
                "increase_complexity": True
            } if profile.overall_state == LearnerState.ADVANCED else None
        )
        
        # Rule: If specific concept struggle, focus on prerequisites
        self.adaptation_rules.append(
            lambda profile, lesson: {
                "review_prerequisites": True,
                "slow_pace": True
            } if lesson.concept in profile.struggle_areas else None
        )
        
    def generate_adaptive_curriculum(self, learner_id: str,
                                   target_concepts: List[str],
                                   initial_assessment: Optional[Dict[str, float]] = None) -> List[ConditionalLesson]:
        """
        Generate curriculum that adapts to learner.
        
        Args:
            learner_id: Unique learner identifier
            target_concepts: Concepts to learn
            initial_assessment: Optional initial skill assessment
            
        Returns:
            List of conditional lessons
        """
        # Get or create learner profile
        profile = self._get_or_create_profile(learner_id, initial_assessment)
        
        # Build lesson graph
        lesson_graph = self._build_lesson_graph(target_concepts, profile)
        
        # Generate initial path
        path = self._generate_initial_path(lesson_graph, profile)
        
        # Apply adaptations
        adapted_path = self._apply_adaptations(path, profile)
        
        return adapted_path
        
    def update_learner_progress(self, learner_id: str, lesson_id: str,
                              performance: float, detailed_results: Optional[Dict] = None):
        """
        Update learner progress after completing a lesson.
        
        Args:
            learner_id: Learner identifier
            lesson_id: Completed lesson
            performance: Performance score [0, 1]
            detailed_results: Optional detailed performance data
        """
        if learner_id not in self.learner_profiles:
            logger.error(f"Unknown learner: {learner_id}")
            return
            
        profile = self.learner_profiles[learner_id]
        lesson = self.lesson_graph.get(lesson_id)
        
        # Update performance history
        profile.performance_history.append(performance)
        
        # Update concept mastery
        if lesson and lesson.concept:
            current_mastery = profile.concept_mastery.get(
                lesson.concept, ConceptMastery.NONE
            )
            
            # Increase mastery based on performance
            if performance >= 0.9:
                new_mastery = min(ConceptMastery.MASTERY.value, 
                                current_mastery.value + 2)
            elif performance >= 0.7:
                new_mastery = min(ConceptMastery.MASTERY.value,
                                current_mastery.value + 1)
            else:
                new_mastery = current_mastery.value  # No progress
                
            profile.concept_mastery[lesson.concept] = ConceptMastery(new_mastery)
            
        # Identify struggle areas
        if performance < 0.5 and lesson:
            if lesson.concept not in profile.struggle_areas:
                profile.struggle_areas.append(lesson.concept)
        elif performance > 0.8 and lesson and lesson.concept in profile.struggle_areas:
            profile.struggle_areas.remove(lesson.concept)
            
        # Adjust preferred difficulty
        if detailed_results and "perceived_difficulty" in detailed_results:
            perceived = detailed_results["perceived_difficulty"]
            if perceived > 0.8:  # Too hard
                profile.preferred_difficulty *= 0.9
            elif perceived < 0.3:  # Too easy
                profile.preferred_difficulty *= 1.1
                
        logger.info(f"Updated progress for {learner_id}: performance={performance:.2f}")
        
    def get_next_lesson(self, learner_id: str, current_lesson_id: str,
                       performance: float) -> Optional[ConditionalLesson]:
        """
        Determine next lesson based on performance.
        
        Args:
            learner_id: Learner identifier
            current_lesson_id: Just completed lesson
            performance: Performance on current lesson
            
        Returns:
            Next lesson or None
        """
        if current_lesson_id not in self.lesson_graph:
            return None
            
        current_lesson = self.lesson_graph[current_lesson_id]
        profile = self.learner_profiles.get(learner_id)
        
        if not profile:
            return None
            
        # Determine outcome
        if performance >= current_lesson.success_threshold:
            outcome = "success"
        elif performance < 0.3:
            outcome = "failure"
        else:
            outcome = "partial"
            
        # Check for conditional next lesson
        next_lesson_id = current_lesson.next_lessons.get(outcome)
        
        if next_lesson_id and next_lesson_id in self.lesson_graph:
            next_lesson = self.lesson_graph[next_lesson_id]
            
            # Apply adaptations
            adapted_lesson = self._adapt_lesson(next_lesson, profile)
            return adapted_lesson
            
        return None
        
    def generate_remediation_path(self, learner_id: str,
                                concept: str) -> List[ConditionalLesson]:
        """
        Generate remediation path for struggling concept.
        
        Args:
            learner_id: Learner identifier
            concept: Concept needing remediation
            
        Returns:
            Remediation lesson sequence
        """
        profile = self.learner_profiles.get(learner_id)
        if not profile:
            return []
            
        # Identify gaps
        gaps = self._identify_knowledge_gaps(profile, concept)
        
        # Generate targeted lessons
        remediation_lessons = []
        
        for gap in gaps:
            lesson = self._create_remediation_lesson(gap, profile)
            remediation_lessons.append(lesson)
            
        # Add practice for the target concept
        practice_lesson = self._create_practice_lesson(concept, profile)
        remediation_lessons.append(practice_lesson)
        
        return remediation_lessons
        
    def _get_or_create_profile(self, learner_id: str,
                             initial_assessment: Optional[Dict[str, float]] = None) -> LearnerProfile:
        """Get existing or create new learner profile."""
        if learner_id not in self.learner_profiles:
            profile = LearnerProfile(id=learner_id)
            
            # Apply initial assessment if provided
            if initial_assessment:
                for concept, score in initial_assessment.items():
                    mastery_level = int(score * 5)  # Convert to mastery enum
                    profile.concept_mastery[concept] = ConceptMastery(mastery_level)
                    
            self.learner_profiles[learner_id] = profile
            
        return self.learner_profiles[learner_id]
        
    def _build_lesson_graph(self, concepts: List[str],
                          profile: LearnerProfile) -> Dict[str, ConditionalLesson]:
        """Build graph of conditional lessons."""
        graph = {}
        
        for i, concept in enumerate(concepts):
            # Check if learner already has some mastery
            mastery = profile.concept_mastery.get(concept, ConceptMastery.NONE)
            
            # Create appropriate lesson
            if mastery.value < ConceptMastery.FAMILIARITY.value:
                lesson = self._create_introductory_lesson(concept, i)
            elif mastery.value < ConceptMastery.PROFICIENCY.value:
                lesson = self._create_practice_lesson(concept, profile, i)
            else:
                lesson = self._create_advanced_lesson(concept, i)
                
            graph[lesson.id] = lesson
            self.lesson_graph[lesson.id] = lesson
            
        # Link lessons
        self._link_lessons(graph, profile)
        
        return graph
        
    def _create_introductory_lesson(self, concept: str, index: int) -> ConditionalLesson:
        """Create introductory lesson for concept."""
        return ConditionalLesson(
            id=f"intro_{concept}_{index}",
            concept=concept,
            base_content={
                "type": "introduction",
                "explanation": f"Introduction to {concept}",
                "examples": ["Basic example 1", "Basic example 2"],
                "exercises": ["Simple exercise 1", "Simple exercise 2"]
            },
            conditional_content={
                "struggling": {
                    "extra_examples": ["Very simple example"],
                    "hints": ["Think about...", "Remember that..."]
                },
                "advanced": {
                    "challenge": "Try this advanced variation",
                    "connection": f"This relates to other concepts like..."
                }
            },
            success_threshold=0.7,
            next_lessons={
                "success": f"practice_{concept}_{index}",
                "partial": f"review_{concept}_{index}",
                "failure": f"remedial_{concept}_{index}"
            }
        )
        
    def _create_practice_lesson(self, concept: str, profile: LearnerProfile,
                               index: Optional[int] = None) -> ConditionalLesson:
        """Create practice lesson for concept."""
        difficulty = profile.preferred_difficulty
        
        return ConditionalLesson(
            id=f"practice_{concept}_{index or 0}",
            concept=concept,
            base_content={
                "type": "practice",
                "exercises": [
                    {"difficulty": difficulty * 0.8, "type": "basic"},
                    {"difficulty": difficulty, "type": "standard"},
                    {"difficulty": difficulty * 1.2, "type": "challenge"}
                ],
                "hints_available": True
            },
            conditional_content={
                "time_pressure": {
                    "time_limit": 300,  # 5 minutes
                    "bonus_points": True
                },
                "collaborative": {
                    "peer_review": True,
                    "discussion_prompts": ["What approach did you take?"]
                }
            },
            success_threshold=0.75,
            next_lessons={
                "success": f"advanced_{concept}_{index or 0}",
                "partial": f"practice_{concept}_{(index or 0) + 1}",
                "failure": f"review_{concept}_{index or 0}"
            }
        )
        
    def _create_advanced_lesson(self, concept: str, index: int) -> ConditionalLesson:
        """Create advanced lesson for concept."""
        return ConditionalLesson(
            id=f"advanced_{concept}_{index}",
            concept=concept,
            base_content={
                "type": "advanced",
                "synthesis": f"Combine {concept} with other concepts",
                "projects": ["Mini project 1", "Mini project 2"],
                "open_ended": True
            },
            conditional_content={
                "creative": {
                    "design_challenge": f"Design your own {concept} system",
                    "constraints": ["Must be efficient", "Must be elegant"]
                },
                "analytical": {
                    "analysis_task": f"Analyze different {concept} implementations",
                    "comparison": "Compare and contrast approaches"
                }
            },
            success_threshold=0.8,
            next_lessons={
                "success": f"mastery_{concept}_{index}",
                "partial": f"advanced_{concept}_{index + 1}",
                "failure": f"practice_{concept}_{index}"
            }
        )
        
    def _create_remediation_lesson(self, concept: str,
                                 profile: LearnerProfile) -> ConditionalLesson:
        """Create remediation lesson for struggling concept."""
        return ConditionalLesson(
            id=f"remedial_{concept}_{len(self.lesson_graph)}",
            concept=concept,
            base_content={
                "type": "remediation",
                "review": "Let's review the basics",
                "step_by_step": True,
                "scaffolding": "high",
                "multiple_representations": ["visual", "verbal", "symbolic"]
            },
            conditional_content={
                "visual_learner": {
                    "diagrams": True,
                    "animations": True
                },
                "hands_on_learner": {
                    "interactive": True,
                    "manipulatives": True
                }
            },
            success_threshold=0.6,  # Lower threshold
            next_lessons={
                "success": f"practice_{concept}_0",
                "partial": f"remedial_{concept}_{len(self.lesson_graph) + 1}",
                "failure": f"prerequisite_{concept}_0"
            }
        )
        
    def _link_lessons(self, graph: Dict[str, ConditionalLesson],
                     profile: LearnerProfile):
        """Create connections between lessons."""
        lessons = list(graph.values())
        
        for i, lesson in enumerate(lessons[:-1]):
            # Default progression
            if "success" not in lesson.next_lessons:
                lesson.next_lessons["success"] = lessons[i + 1].id
                
            # Add review loops
            if lesson.concept in profile.struggle_areas:
                review_id = f"review_{lesson.concept}_{i}"
                if review_id not in graph:
                    review_lesson = self._create_remediation_lesson(
                        lesson.concept, profile
                    )
                    review_lesson.id = review_id
                    graph[review_id] = review_lesson
                    
    def _generate_initial_path(self, lesson_graph: Dict[str, ConditionalLesson],
                             profile: LearnerProfile) -> List[ConditionalLesson]:
        """Generate initial learning path."""
        # Sort lessons by difficulty and prerequisites
        lessons = list(lesson_graph.values())
        
        # Filter based on current mastery
        relevant_lessons = []
        for lesson in lessons:
            mastery = profile.concept_mastery.get(lesson.concept, ConceptMastery.NONE)
            if mastery.value < ConceptMastery.PROFICIENCY.value:
                relevant_lessons.append(lesson)
                
        return relevant_lessons[:10]  # Initial 10 lessons
        
    def _apply_adaptations(self, lessons: List[ConditionalLesson],
                         profile: LearnerProfile) -> List[ConditionalLesson]:
        """Apply adaptations to lessons based on profile."""
        adapted_lessons = []
        
        for lesson in lessons:
            adapted = self._adapt_lesson(lesson, profile)
            adapted_lessons.append(adapted)
            
        return adapted_lessons
        
    def _adapt_lesson(self, lesson: ConditionalLesson,
                     profile: LearnerProfile) -> ConditionalLesson:
        """Adapt single lesson to learner."""
        # Apply adaptation rules
        adaptations = []
        
        for rule in self.adaptation_rules:
            adaptation = rule(profile, lesson)
            if adaptation:
                adaptations.append(adaptation)
                
        # Create adapted lesson
        import copy
        adapted = copy.deepcopy(lesson)
        adapted.adaptations = adaptations
        
        # Apply adaptations to content
        for adaptation in adaptations:
            if "add_examples" in adaptation and adaptation["add_examples"]:
                adapted.base_content["examples"] = adapted.base_content.get("examples", []) + \
                                                 ["Extra example 1", "Extra example 2"]
                                                 
            if "simplify_language" in adaptation and adaptation["simplify_language"]:
                adapted.base_content["simple_mode"] = True
                
            if "add_challenges" in adaptation and adaptation["add_challenges"]:
                adapted.base_content["bonus_challenges"] = ["Challenge 1", "Challenge 2"]
                
        return adapted
        
    def _identify_knowledge_gaps(self, profile: LearnerProfile,
                               target_concept: str) -> List[str]:
        """Identify knowledge gaps for concept."""
        # Simple implementation - in practice would use prerequisite graph
        gaps = []
        
        # Check mastery of related concepts
        related_concepts = ["basics", "fundamentals", "prerequisites"]
        
        for concept in related_concepts:
            if profile.concept_mastery.get(concept, ConceptMastery.NONE).value < \
               ConceptMastery.COMPETENCE.value:
                gaps.append(concept)
                
        return gaps