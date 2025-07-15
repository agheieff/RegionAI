"""
Vignette Curriculum - Learning commonsense through everyday scenarios.

This module provides a curriculum of vignettes (short scenarios) that
teach commonsense reasoning through everyday situations.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import random


class VignetteDifficulty(Enum):
    """Difficulty levels for vignettes."""
    BASIC = "basic"          # Single concept, clear outcome
    INTERMEDIATE = "intermediate"  # Multiple concepts, some inference
    ADVANCED = "advanced"    # Complex interactions, ambiguity
    EXPERT = "expert"        # Subtle reasoning, cultural context


@dataclass
class VignetteQuestion:
    """A question about a vignette."""
    question: str
    answer: str
    reasoning_type: str  # causal, temporal, spatial, social, etc.
    difficulty: float


@dataclass
class Vignette:
    """A commonsense learning vignette."""
    id: str
    title: str
    scenario: str
    difficulty: VignetteDifficulty
    concepts: List[str]  # Commonsense concepts involved
    questions: List[VignetteQuestion]
    teaching_points: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class VignetteCurriculum:
    """
    Curriculum of vignettes for teaching commonsense reasoning.
    
    Vignettes progress from simple scenarios with single concepts
    to complex situations requiring integration of multiple concepts.
    """
    
    def __init__(self):
        self.vignettes: Dict[str, Vignette] = {}
        self.by_difficulty: Dict[VignetteDifficulty, List[str]] = {
            level: [] for level in VignetteDifficulty
        }
        self.by_concept: Dict[str, List[str]] = {}
        self._initialize_curriculum()
        
    def _initialize_curriculum(self):
        """Initialize the vignette curriculum."""
        
        # Basic vignettes
        self.add_vignette(
            "spilled_milk",
            "The Spilled Milk",
            "Sarah accidentally knocked over her glass of milk at breakfast. The milk spread across the table and started dripping onto the floor.",
            VignetteDifficulty.BASIC,
            concepts=["gravity", "liquids", "containers", "accidents"],
            questions=[
                VignetteQuestion(
                    "What direction did the milk flow?",
                    "Downward/toward the floor",
                    "physical",
                    0.2
                ),
                VignetteQuestion(
                    "What should Sarah do first?",
                    "Stop the milk from dripping/clean it up",
                    "practical",
                    0.3
                ),
                VignetteQuestion(
                    "Could the milk flow upward?",
                    "No, because of gravity",
                    "physical",
                    0.2
                )
            ],
            teaching_points=[
                "Gravity causes liquids to flow downward",
                "Spilled liquids spread and need immediate attention",
                "Accidents require practical responses"
            ]
        )
        
        self.add_vignette(
            "locked_out",
            "Locked Outside",
            "Tom came home from work and reached for his keys. He realized he had left them inside the house. The door was locked.",
            VignetteDifficulty.BASIC,
            concepts=["keys", "locks", "access", "problem_solving"],
            questions=[
                VignetteQuestion(
                    "Why can't Tom enter his house?",
                    "The door is locked and he doesn't have his keys",
                    "causal",
                    0.2
                ),
                VignetteQuestion(
                    "What is the purpose of keys?",
                    "To unlock/open locked doors",
                    "functional",
                    0.1
                ),
                VignetteQuestion(
                    "What are Tom's options?",
                    "Find another way in, call someone with keys, call a locksmith",
                    "problem_solving",
                    0.4
                )
            ],
            teaching_points=[
                "Keys are required to open locked doors",
                "Being locked out requires alternative solutions",
                "Planning ahead prevents such situations"
            ]
        )
        
        # Intermediate vignettes
        self.add_vignette(
            "birthday_surprise",
            "Birthday Surprise",
            "Emma wanted to surprise her roommate Jake for his birthday. She bought a cake and hid it in the refrigerator. She also invited several friends to come over at 7 PM. At 6:30, Jake said he was going out to meet someone for dinner.",
            VignetteDifficulty.INTERMEDIATE,
            concepts=["surprises", "planning", "timing", "social_coordination"],
            questions=[
                VignetteQuestion(
                    "Why is Jake leaving a problem for Emma?",
                    "The surprise party guests will arrive while he's gone",
                    "temporal",
                    0.5
                ),
                VignetteQuestion(
                    "Why did Emma hide the cake?",
                    "To keep the surprise secret",
                    "social",
                    0.3
                ),
                VignetteQuestion(
                    "What should Emma do?",
                    "Try to delay Jake or reveal the surprise",
                    "problem_solving",
                    0.6
                )
            ],
            teaching_points=[
                "Surprises require secrecy and timing",
                "Plans can be disrupted by unexpected events",
                "Social coordination requires communication"
            ]
        )
        
        self.add_vignette(
            "plant_care",
            "The Wilting Plant",
            "Maria noticed her office plant's leaves were turning brown and drooping. She had been watering it every day. The plant sits on her desk near the window, which gets direct afternoon sunlight. The office heating system runs constantly.",
            VignetteDifficulty.INTERMEDIATE,
            concepts=["plants", "water", "sunlight", "problem_diagnosis"],
            questions=[
                VignetteQuestion(
                    "What might be wrong with the plant?",
                    "Overwatering, too much direct sunlight, or dry air",
                    "causal",
                    0.6
                ),
                VignetteQuestion(
                    "Is daily watering always good for plants?",
                    "No, it can cause overwatering",
                    "biological",
                    0.5
                ),
                VignetteQuestion(
                    "How do heating systems affect plants?",
                    "They dry the air, which can stress plants",
                    "environmental",
                    0.5
                )
            ],
            teaching_points=[
                "Too much water can harm plants",
                "Plants have specific environmental needs",
                "Multiple factors affect plant health"
            ]
        )
        
        # Advanced vignettes
        self.add_vignette(
            "restaurant_dilemma",
            "The Restaurant Bill",
            "Eight friends went out for dinner to celebrate. When the bill came, it was $240. Two friends said they only had cash and put in $25 each. One friend realized she forgot her wallet. Another said he could only contribute $20 because he just had an appetizer. The others looked at each other uncertainly.",
            VignetteDifficulty.ADVANCED,
            concepts=["social_obligations", "fairness", "money", "group_dynamics"],
            questions=[
                VignetteQuestion(
                    "What is the social tension here?",
                    "Unequal contributions vs. equal splitting expectations",
                    "social",
                    0.7
                ),
                VignetteQuestion(
                    "How much do the others need to pay?",
                    "$170 split among 4 people = $42.50 each",
                    "mathematical",
                    0.6
                ),
                VignetteQuestion(
                    "What's the fairest solution?",
                    "Split by what each person ordered, or agree on proportional contributions",
                    "ethical",
                    0.8
                )
            ],
            teaching_points=[
                "Group dining creates complex social obligations",
                "Fairness can be interpreted differently",
                "Communication prevents awkward situations"
            ]
        )
        
        self.add_vignette(
            "neighbor_noise",
            "The New Neighbor",
            "Alex lives in an apartment and works from home. A new neighbor moved in upstairs last week. Every afternoon around 2 PM, Alex hears loud music and footsteps, making it hard to concentrate on video calls. The neighbor seems friendly when they meet in the hallway.",
            VignetteDifficulty.ADVANCED,
            concepts=["neighbors", "noise", "conflict_resolution", "social_norms"],
            questions=[
                VignetteQuestion(
                    "What's the neighbor probably doing at 2 PM?",
                    "Exercising, cleaning, or enjoying music during their free time",
                    "inference",
                    0.6
                ),
                VignetteQuestion(
                    "Why hasn't Alex complained yet?",
                    "Wants to maintain friendly relationship, avoiding conflict",
                    "social",
                    0.7
                ),
                VignetteQuestion(
                    "What's the best approach?",
                    "Politely discuss the issue and find a compromise",
                    "social",
                    0.7
                )
            ],
            teaching_points=[
                "Apartment living requires compromise",
                "People may not realize they're causing problems",
                "Direct but polite communication solves most issues"
            ]
        )
        
        # Expert vignettes
        self.add_vignette(
            "gift_rejection",
            "The Refused Gift",
            "At a family gathering, Chen's aunt offered him an envelope, likely containing money as a graduation gift. Following his parents' earlier instructions to be polite but not take money from relatives, Chen refused twice. His aunt insisted a third time, looking slightly offended. Other relatives were watching.",
            VignetteDifficulty.EXPERT,
            concepts=["cultural_norms", "gift_giving", "family_dynamics", "face_saving"],
            questions=[
                VignetteQuestion(
                    "Why did the aunt insist three times?",
                    "Cultural norm of offering multiple times to show sincerity",
                    "cultural",
                    0.8
                ),
                VignetteQuestion(
                    "What should Chen do?",
                    "Accept on the third offer to respect the aunt and cultural norms",
                    "cultural",
                    0.9
                ),
                VignetteQuestion(
                    "Why are others watching?",
                    "Public gift exchange affects family reputation and relationships",
                    "social",
                    0.8
                )
            ],
            teaching_points=[
                "Cultural norms override literal instructions",
                "Gift refusal/acceptance has complex rules",
                "Public actions affect family dynamics"
            ]
        )
        
    def add_vignette(self, id: str, title: str, scenario: str,
                    difficulty: VignetteDifficulty, concepts: List[str],
                    questions: List[VignetteQuestion], teaching_points: List[str]):
        """Add a vignette to the curriculum."""
        vignette = Vignette(
            id=id,
            title=title,
            scenario=scenario,
            difficulty=difficulty,
            concepts=concepts,
            questions=questions,
            teaching_points=teaching_points
        )
        
        self.vignettes[id] = vignette
        self.by_difficulty[difficulty].append(id)
        
        for concept in concepts:
            if concept not in self.by_concept:
                self.by_concept[concept] = []
            self.by_concept[concept].append(id)
            
    def get_vignette(self, id: str) -> Optional[Vignette]:
        """Get a specific vignette."""
        return self.vignettes.get(id)
        
    def get_by_difficulty(self, difficulty: VignetteDifficulty,
                         limit: Optional[int] = None) -> List[Vignette]:
        """Get vignettes of a specific difficulty."""
        vignette_ids = self.by_difficulty.get(difficulty, [])
        vignettes = [self.vignettes[vid] for vid in vignette_ids]
        
        if limit:
            return vignettes[:limit]
        return vignettes
        
    def get_by_concept(self, concept: str) -> List[Vignette]:
        """Get vignettes involving a specific concept."""
        vignette_ids = self.by_concept.get(concept, [])
        return [self.vignettes[vid] for vid in vignette_ids]
        
    def get_learning_sequence(self, concepts: List[str],
                            max_vignettes: int = 10) -> List[Vignette]:
        """
        Get a sequence of vignettes for learning specific concepts.
        
        Args:
            concepts: Concepts to learn
            max_vignettes: Maximum number of vignettes
            
        Returns:
            Ordered list of vignettes
        """
        selected = []
        selected_ids = set()
        
        # Start with basic vignettes containing these concepts
        for difficulty in [VignetteDifficulty.BASIC, VignetteDifficulty.INTERMEDIATE,
                          VignetteDifficulty.ADVANCED, VignetteDifficulty.EXPERT]:
            for concept in concepts:
                for vid in self.by_concept.get(concept, []):
                    if vid not in selected_ids and self.vignettes[vid].difficulty == difficulty:
                        selected.append(self.vignettes[vid])
                        selected_ids.add(vid)
                        
                        if len(selected) >= max_vignettes:
                            return selected
                            
        return selected
        
    def evaluate_understanding(self, vignette_id: str,
                             answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Evaluate understanding of a vignette based on answers.
        
        Args:
            vignette_id: Vignette to evaluate
            answers: Dict mapping question to given answer
            
        Returns:
            Evaluation results
        """
        vignette = self.get_vignette(vignette_id)
        if not vignette:
            return {"error": "Vignette not found"}
            
        results = {
            "vignette": vignette.title,
            "total_questions": len(vignette.questions),
            "answered": len(answers),
            "correct": 0,
            "by_reasoning_type": {},
            "feedback": []
        }
        
        for i, question in enumerate(vignette.questions):
            q_text = question.question
            if q_text in answers:
                # Simple evaluation - check key concepts
                given = answers[q_text].lower()
                expected = question.answer.lower()
                
                # Check if key words from expected answer are in given answer
                key_words = [w for w in expected.split() 
                           if len(w) > 3 and w not in ['the', 'and', 'or']]
                
                matches = sum(1 for word in key_words if word in given)
                is_correct = matches >= len(key_words) * 0.5
                
                if is_correct:
                    results["correct"] += 1
                    
                # Track by reasoning type
                r_type = question.reasoning_type
                if r_type not in results["by_reasoning_type"]:
                    results["by_reasoning_type"][r_type] = {"total": 0, "correct": 0}
                    
                results["by_reasoning_type"][r_type]["total"] += 1
                if is_correct:
                    results["by_reasoning_type"][r_type]["correct"] += 1
                    
                # Provide feedback
                if not is_correct:
                    results["feedback"].append({
                        "question": q_text,
                        "expected": question.answer,
                        "reasoning": f"This requires {question.reasoning_type} reasoning"
                    })
                    
        results["score"] = results["correct"] / results["total_questions"]
        return results
        
    def generate_practice_session(self, focus_concepts: Optional[List[str]] = None,
                                difficulty: Optional[VignetteDifficulty] = None,
                                num_vignettes: int = 5) -> List[Vignette]:
        """
        Generate a practice session with random vignettes.
        
        Args:
            focus_concepts: Optional concepts to focus on
            difficulty: Optional difficulty level
            num_vignettes: Number of vignettes
            
        Returns:
            List of vignettes for practice
        """
        candidates = list(self.vignettes.values())
        
        # Filter by difficulty
        if difficulty:
            candidates = [v for v in candidates if v.difficulty == difficulty]
            
        # Filter by concepts
        if focus_concepts:
            candidates = [v for v in candidates 
                         if any(c in v.concepts for c in focus_concepts)]
                         
        # Random selection
        if len(candidates) > num_vignettes:
            return random.sample(candidates, num_vignettes)
        return candidates