"""
Training API - Public facade for training and learning capabilities.

This module provides a clean API for training the system on new concepts
and transformations.
"""

from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime

# Import from new structure
from ..curriculum.factory import CurriculumFactory
from ..curriculum.generators.basic import BasicCurriculumGenerator
from ..curriculum.generators.conditional import ConditionalCurriculumGenerator
from ..curriculum.generators.iterative import IterativeCurriculumGenerator
from ..core.transformation import Transformation
from ..brains.bayesian import BayesianBrain
from ..brains.utility import UtilityBrain

logger = logging.getLogger(__name__)


@dataclass
class TrainingSession:
    """Represents a training session."""
    id: str
    start_time: datetime
    curriculum_type: str
    target_concepts: List[str]
    progress: Dict[str, float] = field(default_factory=dict)
    completed_lessons: List[str] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    active: bool = True
    
    
@dataclass
class TrainingResult:
    """Result from a training operation."""
    success: bool
    session_id: str
    concepts_learned: List[str]
    mastery_levels: Dict[str, float]
    total_time: float
    lessons_completed: int
    average_performance: float
    recommendations: List[str] = field(default_factory=list)


class TrainingAPI:
    """
    Public API for training and learning capabilities.
    
    This class provides methods for training the system on new concepts,
    managing curricula, and tracking learning progress.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Training API.
        
        Args:
            config: Optional configuration
        """
        self.config = config or {}
        self.sessions: Dict[str, TrainingSession] = {}
        self.bayesian_brain = BayesianBrain()
        self.utility_brain = UtilityBrain()
        
        # Initialize curriculum generators
        self.basic_generator = BasicCurriculumGenerator()
        self.conditional_generator = ConditionalCurriculumGenerator()
        self.iterative_generator = IterativeCurriculumGenerator()
        
    def start_training(self, concepts: List[str],
                      curriculum_type: str = "adaptive",
                      options: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new training session.
        
        Args:
            concepts: Concepts to learn
            curriculum_type: Type of curriculum ("basic", "adaptive", "iterative")
            options: Training options
            
        Returns:
            Session ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = TrainingSession(
            id=session_id,
            start_time=datetime.now(),
            curriculum_type=curriculum_type,
            target_concepts=concepts
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Started training session {session_id} for concepts: {concepts}")
        
        return session_id
        
    def train_concept(self, concept: str,
                     examples: List[Dict[str, Any]],
                     validation_set: Optional[List[Dict[str, Any]]] = None) -> TrainingResult:
        """
        Train a specific concept with examples.
        
        Args:
            concept: Concept to train
            examples: Training examples
            validation_set: Optional validation examples
            
        Returns:
            Training result
        """
        session_id = self.start_training([concept], curriculum_type="basic")
        session = self.sessions[session_id]
        
        start_time = datetime.now()
        
        # Process training examples
        correct = 0
        for i, example in enumerate(examples):
            # Train on example
            success = self._process_example(concept, example)
            if success:
                correct += 1
                
            # Update progress
            session.performance_history.append(correct / (i + 1))
            
            # Update Bayesian belief
            self.bayesian_brain.observe(concept, success, credibility=0.9)
            
        # Validate if validation set provided
        mastery = correct / len(examples) if examples else 0.0
        
        if validation_set:
            val_correct = sum(
                1 for ex in validation_set 
                if self._validate_example(concept, ex)
            )
            mastery = val_correct / len(validation_set)
            
        # Finalize session
        session.active = False
        session.progress[concept] = mastery
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        return TrainingResult(
            success=mastery >= 0.7,
            session_id=session_id,
            concepts_learned=[concept] if mastery >= 0.7 else [],
            mastery_levels={concept: mastery},
            total_time=total_time,
            lessons_completed=len(examples),
            average_performance=mastery,
            recommendations=self._generate_recommendations(concept, mastery)
        )
        
    def train_transformation(self, name: str,
                           input_output_pairs: List[Tuple[Any, Any]],
                           description: Optional[str] = None) -> TrainingResult:
        """
        Train a new transformation from examples.
        
        Args:
            name: Name of transformation
            input_output_pairs: Example (input, output) pairs
            description: Optional description
            
        Returns:
            Training result
        """
        session_id = self.start_training([f"transformation_{name}"])
        session = self.sessions[session_id]
        
        start_time = datetime.now()
        
        # Learn transformation pattern
        success_count = 0
        learned_pattern = None
        
        for i, (input_val, output_val) in enumerate(input_output_pairs):
            # Try to learn pattern
            pattern = self._learn_pattern(input_val, output_val, learned_pattern)
            
            if pattern:
                learned_pattern = pattern
                success_count += 1
                
            session.performance_history.append(success_count / (i + 1))
            
        # Create transformation if learned
        mastery = success_count / len(input_output_pairs) if input_output_pairs else 0.0
        
        if mastery >= 0.8 and learned_pattern:
            # Register transformation
            self._register_transformation(name, learned_pattern, description)
            concepts_learned = [f"transformation_{name}"]
        else:
            concepts_learned = []
            
        total_time = (datetime.now() - start_time).total_seconds()
        
        return TrainingResult(
            success=mastery >= 0.8,
            session_id=session_id,
            concepts_learned=concepts_learned,
            mastery_levels={f"transformation_{name}": mastery},
            total_time=total_time,
            lessons_completed=len(input_output_pairs),
            average_performance=mastery,
            recommendations=self._generate_transformation_recommendations(name, mastery)
        )
        
    def continue_training(self, session_id: str,
                        additional_lessons: int = 10) -> TrainingResult:
        """
        Continue an existing training session.
        
        Args:
            session_id: Session to continue
            additional_lessons: Number of lessons to add
            
        Returns:
            Updated training result
        """
        if session_id not in self.sessions:
            raise ValueError(f"Unknown session: {session_id}")
            
        session = self.sessions[session_id]
        if not session.active:
            raise ValueError(f"Session {session_id} is not active")
            
        start_time = datetime.now()
        
        # Generate additional lessons based on progress
        if session.curriculum_type == "adaptive":
            generator = self.conditional_generator
        elif session.curriculum_type == "iterative":
            generator = self.iterative_generator
        else:
            generator = self.basic_generator
            
        # Get current progress
        struggling_concepts = [
            c for c in session.target_concepts 
            if session.progress.get(c, 0) < 0.7
        ]
        
        # Generate remedial lessons
        if struggling_concepts and hasattr(generator, 'generate_remedial_lessons'):
            lessons = generator.generate_remedial_lessons(
                struggling_concepts[0], additional_lessons
            )
        else:
            lessons = generator.generate_practice_set(
                session.target_concepts, additional_lessons
            )
            
        # Process lessons
        performances = []
        for lesson in lessons:
            performance = self._process_lesson(lesson, session)
            performances.append(performance)
            session.performance_history.append(performance)
            
        # Update mastery
        for concept in session.target_concepts:
            current_mastery = session.progress.get(concept, 0.0)
            # Simple update based on recent performance
            recent_avg = sum(performances) / len(performances) if performances else 0
            new_mastery = 0.7 * current_mastery + 0.3 * recent_avg
            session.progress[concept] = new_mastery
            
        total_time = (datetime.now() - start_time).total_seconds()
        
        return TrainingResult(
            success=all(m >= 0.7 for m in session.progress.values()),
            session_id=session_id,
            concepts_learned=[c for c, m in session.progress.items() if m >= 0.7],
            mastery_levels=session.progress.copy(),
            total_time=total_time,
            lessons_completed=len(lessons),
            average_performance=sum(performances) / len(performances) if performances else 0,
            recommendations=self._generate_session_recommendations(session)
        )
        
    def get_progress(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get training progress.
        
        Args:
            session_id: Specific session or None for overall
            
        Returns:
            Progress information
        """
        if session_id:
            if session_id not in self.sessions:
                return {"error": f"Unknown session: {session_id}"}
                
            session = self.sessions[session_id]
            return {
                "session_id": session_id,
                "active": session.active,
                "concepts": session.target_concepts,
                "progress": session.progress,
                "lessons_completed": len(session.completed_lessons),
                "current_performance": session.performance_history[-1] if session.performance_history else 0,
                "performance_trend": self._calculate_trend(session.performance_history)
            }
        else:
            # Overall progress
            all_concepts = set()
            for session in self.sessions.values():
                all_concepts.update(session.target_concepts)
                
            concept_mastery = {}
            for concept in all_concepts:
                masteries = [
                    s.progress.get(concept, 0) 
                    for s in self.sessions.values() 
                    if concept in s.target_concepts
                ]
                if masteries:
                    concept_mastery[concept] = max(masteries)
                    
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": sum(1 for s in self.sessions.values() if s.active),
                "concepts_attempted": len(all_concepts),
                "concepts_mastered": sum(1 for m in concept_mastery.values() if m >= 0.7),
                "overall_mastery": concept_mastery
            }
            
    def recommend_next(self, learner_profile: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Recommend next concepts to learn.
        
        Args:
            learner_profile: Optional learner information
            
        Returns:
            List of recommended concepts
        """
        # Get current knowledge state
        mastered = set()
        attempted = set()
        
        for session in self.sessions.values():
            for concept, mastery in session.progress.items():
                if mastery >= 0.7:
                    mastered.add(concept)
                else:
                    attempted.add(concept)
                    
        # Use utility brain to decide what to learn next
        thinking_result = self.utility_brain.think_about({
            "mastered": list(mastered),
            "attempted": list(attempted),
            "profile": learner_profile
        })
        
        # Extract recommendations
        recommendations = []
        
        # Retry struggling concepts
        struggling = attempted - mastered
        if struggling:
            recommendations.extend(list(struggling)[:2])
            
        # Add new concepts based on prerequisites
        # This is simplified - real system would use concept graph
        if "basic" in mastered and "intermediate" not in mastered:
            recommendations.append("intermediate")
            
        if not recommendations:
            recommendations = ["advanced_concepts", "integration", "synthesis"]
            
        return recommendations[:5]  # Top 5 recommendations
        
    def export_progress(self, session_id: Optional[str] = None,
                       format: str = "json") -> Union[str, Dict[str, Any]]:
        """
        Export training progress.
        
        Args:
            session_id: Specific session or None for all
            format: Export format ("json", "summary")
            
        Returns:
            Exported data
        """
        if session_id:
            sessions_to_export = [self.sessions[session_id]] if session_id in self.sessions else []
        else:
            sessions_to_export = list(self.sessions.values())
            
        if format == "summary":
            summary = []
            for session in sessions_to_export:
                summary.append(
                    f"Session {session.id}: "
                    f"{len(session.completed_lessons)} lessons, "
                    f"mastery: {list(session.progress.values())}"
                )
            return "\n".join(summary)
        else:
            # JSON format
            data = {
                "export_time": datetime.now().isoformat(),
                "sessions": [
                    {
                        "id": s.id,
                        "start_time": s.start_time.isoformat(),
                        "concepts": s.target_concepts,
                        "progress": s.progress,
                        "lessons_completed": len(s.completed_lessons),
                        "active": s.active
                    }
                    for s in sessions_to_export
                ]
            }
            return data
            
    def _process_example(self, concept: str, example: Dict[str, Any]) -> bool:
        """Process a training example."""
        # Simplified processing
        # Real implementation would use the actual learning mechanisms
        
        # Simulate learning with some randomness
        import random
        
        # Base success rate improves with more examples
        base_rate = 0.6
        if hasattr(self, '_example_count'):
            self._example_count += 1
            base_rate = min(0.9, 0.6 + self._example_count * 0.02)
        else:
            self._example_count = 1
            
        return random.random() < base_rate
        
    def _validate_example(self, concept: str, example: Dict[str, Any]) -> bool:
        """Validate an example."""
        # Simplified validation
        return self._process_example(concept, example)
        
    def _learn_pattern(self, input_val: Any, output_val: Any,
                      current_pattern: Optional[Any]) -> Optional[Any]:
        """Learn pattern from input/output pair."""
        # Simplified pattern learning
        # Real implementation would use transformation discovery
        
        # For now, just return a simple pattern representation
        return {
            "type": "mapping",
            "input_type": type(input_val).__name__,
            "output_type": type(output_val).__name__,
            "examples": [(input_val, output_val)]
        }
        
    def _register_transformation(self, name: str, pattern: Any,
                               description: Optional[str]):
        """Register a learned transformation."""
        # In real implementation, would register with transformation system
        logger.info(f"Registered transformation '{name}': {description or 'No description'}")
        
    def _process_lesson(self, lesson: Any, session: TrainingSession) -> float:
        """Process a lesson and return performance."""
        # Simplified lesson processing
        import random
        
        # Performance based on current mastery
        base_performance = 0.5
        for concept in session.target_concepts:
            if concept in session.progress:
                base_performance += session.progress[concept] * 0.1
                
        performance = min(1.0, base_performance + random.uniform(-0.1, 0.2))
        
        # Record lesson completion
        if hasattr(lesson, 'id'):
            session.completed_lessons.append(lesson.id)
            
        return performance
        
    def _generate_recommendations(self, concept: str, mastery: float) -> List[str]:
        """Generate recommendations for concept learning."""
        recommendations = []
        
        if mastery < 0.3:
            recommendations.append(f"Review prerequisites for {concept}")
            recommendations.append("Try simpler examples first")
        elif mastery < 0.7:
            recommendations.append(f"Practice more examples of {concept}")
            recommendations.append("Focus on edge cases")
        else:
            recommendations.append(f"Ready to advance beyond {concept}")
            recommendations.append("Try integrating with other concepts")
            
        return recommendations
        
    def _generate_transformation_recommendations(self, name: str,
                                               mastery: float) -> List[str]:
        """Generate recommendations for transformation learning."""
        if mastery < 0.5:
            return [
                "Provide more diverse examples",
                "Ensure examples cover edge cases",
                "Check for consistency in patterns"
            ]
        elif mastery < 0.8:
            return [
                "Add examples with different input types",
                "Test with boundary conditions"
            ]
        else:
            return [
                f"Transformation '{name}' successfully learned",
                "Consider composing with other transformations"
            ]
            
    def _generate_session_recommendations(self, session: TrainingSession) -> List[str]:
        """Generate recommendations for a session."""
        recommendations = []
        
        # Check struggling concepts
        struggling = [c for c, m in session.progress.items() if m < 0.5]
        if struggling:
            recommendations.append(f"Focus on struggling concepts: {', '.join(struggling)}")
            
        # Check if making progress
        if len(session.performance_history) > 5:
            recent_trend = self._calculate_trend(session.performance_history[-5:])
            if recent_trend < 0:
                recommendations.append("Performance declining - consider a break")
            elif recent_trend > 0.1:
                recommendations.append("Good progress - increase difficulty")
                
        return recommendations
        
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in values."""
        if len(values) < 2:
            return 0.0
            
        # Simple linear trend
        n = len(values)
        if n == 0:
            return 0.0
            
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
            
        return numerator / denominator


# Convenience functions
def train(concept: str, examples: List[Dict[str, Any]], **kwargs) -> TrainingResult:
    """Quick training function."""
    api = TrainingAPI()
    return api.train_concept(concept, examples, **kwargs)


def get_recommendations(**kwargs) -> List[str]:
    """Get learning recommendations."""
    api = TrainingAPI()
    return api.recommend_next(**kwargs)