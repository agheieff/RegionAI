"""
Mathematical curriculum manager for RegionAI.

This module manages loading and providing mathematical problems from
Lean files, creating a structured curriculum for the reasoning engine.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

try:
    from tier2.linguistics.lean_parser import LeanParser, LeanParseError
    from tier2.linguistics.lean_ast import Theorem
    from .problem import Problem
except ImportError:
    # Allow direct module execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    sys.path.append(str(Path(__file__).parent))
    from lean_parser import LeanParser, LeanParseError
    from lean_ast import Theorem
    from problem import Problem


logger = logging.getLogger(__name__)


@dataclass
class MathProblem(Problem):
    """
    A mathematical problem derived from a Lean theorem.
    
    This extends the base Problem class to include theorem-specific
    information needed for mathematical reasoning.
    """
    theorem: Theorem
    difficulty: float = 1.0
    topics: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    
    def __init__(self, theorem: Theorem, difficulty: float = 1.0,
                 topics: List[str] = None, prerequisites: List[str] = None):
        """Initialize MathProblem with proper base class fields."""
        # Initialize base Problem fields
        super().__init__(
            name=theorem.name,
            problem_type="theorem_proving",
            input_data=f"Prove: {theorem.name}",
            output_data=theorem.statement,
            description=f"Prove the theorem: {theorem.statement}"
        )
        
        # Store additional fields
        self.theorem = theorem
        self.difficulty = difficulty
        self.topics = topics or []
        self.prerequisites = prerequisites or []
        
        # Add metadata
        self.metadata = {
            'theorem_name': self.theorem.name,
            'hypotheses_count': len(self.theorem.hypotheses),
            'source_file': self.theorem.metadata.get('source_file', 'unknown'),
            'difficulty': self.difficulty,
            'topics': self.topics
        }


class MathCurriculum:
    """
    Manages mathematical curriculum for RegionAI.
    
    This class loads theorem definitions from Lean files and provides
    them as problems for the reasoning engine to solve. It supports
    organizing problems by difficulty and topic.
    """
    
    def __init__(self, curriculum_dir: Optional[Path] = None, 
                 curriculum_file: Optional[str] = None):
        """
        Initialize the math curriculum.
        
        Args:
            curriculum_dir: Directory containing .lean files.
            curriculum_file: Optional specific file to load (e.g., "test_self_improve.lean")
                          Defaults to curricula/math/ relative to project root.
        """
        if curriculum_dir is None:
            # Default to curricula/math/ relative to this file
            module_dir = Path(__file__).parent.parent.parent.parent
            curriculum_dir = module_dir / "curricula" / "math"
            
        self.curriculum_dir = Path(curriculum_dir)
        self.curriculum_file = curriculum_file  # Store specific file if provided
        self.parser = LeanParser()
        self.problems: List[MathProblem] = []
        self.problems_by_topic: Dict[str, List[MathProblem]] = {}
        self.problems_by_name: Dict[str, MathProblem] = {}
        
        # Difficulty estimation rules
        self.difficulty_rules = {
            'self': 0.1,  # Self-implication is trivial
            'modus_ponens': 0.3,
            'and': 0.2,  # Conjunction operations are simple
            'or': 0.3,   # Disjunction slightly harder
            'not': 0.4,  # Negation requires more thought
            'iff': 0.5,  # Biconditionals are moderate
            'forall': 0.7,  # Universal quantification is harder
            'exists': 0.8,  # Existential quantification is challenging
        }
        
    def load_curriculum(self) -> None:
        """
        Load all .lean files from the curriculum directory.
        
        This method recursively finds all .lean files and parses them
        into mathematical problems.
        """
        if not self.curriculum_dir.exists():
            logger.warning(f"Curriculum directory does not exist: {self.curriculum_dir}")
            return
            
        logger.info(f"Loading mathematical curriculum from: {self.curriculum_dir}")
        
        # If specific file is requested, load only that file
        if self.curriculum_file:
            specific_file = self.curriculum_dir / self.curriculum_file
            if specific_file.exists():
                logger.info(f"Loading specific curriculum file: {specific_file}")
                try:
                    self._load_file(specific_file)
                except Exception as e:
                    logger.error(f"Failed to load {specific_file}: {e}")
            else:
                logger.error(f"Specific curriculum file not found: {specific_file}")
                return
        else:
            # Find all .lean files
            lean_files = list(self.curriculum_dir.rglob("*.lean"))
            
            if not lean_files:
                logger.warning(f"No .lean files found in {self.curriculum_dir}")
                return
                
            # Parse each file
            for lean_file in sorted(lean_files):
                try:
                    self._load_file(lean_file)
                except Exception as e:
                    logger.error(f"Failed to load {lean_file}: {e}")
                
        logger.info(f"Loaded {len(self.problems)} mathematical problems")
        
    def _load_file(self, file_path: Path) -> None:
        """
        Load theorems from a single .lean file.
        
        Args:
            file_path: Path to the .lean file
        """
        logger.debug(f"Loading file: {file_path}")
        
        try:
            theorems = self.parser.parse_file(file_path)
        except LeanParseError as e:
            logger.error(f"Parse error in {file_path}: {e}")
            return
            
        # Extract topic from file path
        relative_path = file_path.relative_to(self.curriculum_dir)
        topic = relative_path.parent.name if relative_path.parent.name else "general"
        
        # Convert theorems to problems
        for theorem in theorems:
            problem = self._create_problem(theorem, topic)
            self.problems.append(problem)
            
            # Index by name
            self.problems_by_name[theorem.name] = problem
            
            # Index by topic
            for problem_topic in problem.topics:
                if problem_topic not in self.problems_by_topic:
                    self.problems_by_topic[problem_topic] = []
                self.problems_by_topic[problem_topic].append(problem)
                
    def _create_problem(self, theorem: Theorem, default_topic: str) -> MathProblem:
        """
        Create a MathProblem from a Theorem.
        
        Args:
            theorem: The theorem to convert
            default_topic: Default topic if none can be inferred
            
        Returns:
            MathProblem instance
        """
        # Estimate difficulty based on theorem characteristics
        difficulty = self._estimate_difficulty(theorem)
        
        # Extract topics from theorem name and statement
        topics = self._extract_topics(theorem, default_topic)
        
        # Identify prerequisites (simplified for now)
        prerequisites = self._identify_prerequisites(theorem)
        
        return MathProblem(
            theorem=theorem,
            difficulty=difficulty,
            topics=topics,
            prerequisites=prerequisites
        )
        
    def _estimate_difficulty(self, theorem: Theorem) -> float:
        """
        Estimate the difficulty of a theorem.
        
        Args:
            theorem: The theorem to analyze
            
        Returns:
            Difficulty score between 0 and 1
        """
        difficulty = 0.5  # Base difficulty
        
        # Check theorem name for keywords
        name_lower = theorem.name.lower()
        for keyword, score in self.difficulty_rules.items():
            if keyword in name_lower:
                difficulty = score
                break
                
        # Adjust based on statement complexity
        theorem.statement.lower()
        
        # Count logical operators
        operators = ['→', '->', '∧', '/\\', '∨', '\\/', '¬', '~', '↔', '<->', '∀', '∃']
        operator_count = sum(1 for op in operators if op in theorem.statement)
        difficulty += operator_count * 0.05
        
        # Adjust based on hypothesis count
        difficulty += len(theorem.hypotheses) * 0.02
        
        # Clamp to [0, 1]
        return min(1.0, max(0.0, difficulty))
        
    def _extract_topics(self, theorem: Theorem, default_topic: str) -> List[str]:
        """
        Extract topics from theorem name and statement.
        
        Args:
            theorem: The theorem to analyze
            default_topic: Default topic to include
            
        Returns:
            List of topic strings
        """
        topics = [default_topic]
        
        # Add topics based on logical operators used
        if '→' in theorem.statement or '->' in theorem.statement:
            topics.append("implication")
        if '∧' in theorem.statement or '/\\' in theorem.statement:
            topics.append("conjunction")
        if '∨' in theorem.statement or '\\/' in theorem.statement:
            topics.append("disjunction")
        if '¬' in theorem.statement or '~' in theorem.statement:
            topics.append("negation")
        if '↔' in theorem.statement or '<->' in theorem.statement:
            topics.append("biconditional")
        if '∀' in theorem.statement:
            topics.append("universal_quantification")
        if '∃' in theorem.statement:
            topics.append("existential_quantification")
            
        # Check for specific theorem types
        name_lower = theorem.name.lower()
        if 'comm' in name_lower:
            topics.append("commutativity")
        if 'assoc' in name_lower:
            topics.append("associativity")
        if 'distrib' in name_lower:
            topics.append("distributivity")
        if 'identity' in name_lower or 'ident' in name_lower:
            topics.append("identity")
        if 'elim' in name_lower:
            topics.append("elimination")
        if 'intro' in name_lower:
            topics.append("introduction")
            
        return list(set(topics))  # Remove duplicates
        
    def _identify_prerequisites(self, theorem: Theorem) -> List[str]:
        """
        Identify prerequisite theorems.
        
        This is a simplified version that looks for theorem names
        mentioned in the statement. A full implementation would
        analyze the proof structure.
        
        Args:
            theorem: The theorem to analyze
            
        Returns:
            List of prerequisite theorem names
        """
        prerequisites = []
        
        # For now, we'll use a simple heuristic
        # In practice, this would analyze the proof to find dependencies
        if 'modus_ponens' in theorem.statement:
            prerequisites.append('modus_ponens')
            
        return prerequisites
        
    def get_problems(self, 
                    difficulty_range: Optional[tuple[float, float]] = None,
                    topics: Optional[List[str]] = None,
                    limit: Optional[int] = None) -> List[MathProblem]:
        """
        Get problems matching specified criteria.
        
        Args:
            difficulty_range: Optional (min, max) difficulty range
            topics: Optional list of topics to filter by
            limit: Optional maximum number of problems to return
            
        Returns:
            List of matching MathProblem instances
        """
        problems = self.problems
        
        # Filter by difficulty
        if difficulty_range:
            min_diff, max_diff = difficulty_range
            problems = [p for p in problems 
                       if min_diff <= p.difficulty <= max_diff]
                       
        # Filter by topics
        if topics:
            problems = [p for p in problems 
                       if any(t in p.topics for t in topics)]
                       
        # Sort by difficulty
        problems.sort(key=lambda p: p.difficulty)
        
        # Apply limit
        if limit:
            problems = problems[:limit]
            
        return problems
        
    def get_problem_by_name(self, name: str) -> Optional[MathProblem]:
        """
        Get a specific problem by theorem name.
        
        Args:
            name: The theorem name
            
        Returns:
            MathProblem instance or None if not found
        """
        return self.problems_by_name.get(name)
        
    def get_curriculum_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded curriculum.
        
        Returns:
            Dictionary with curriculum statistics
        """
        if not self.problems:
            return {
                'total_problems': 0,
                'topics': {},
                'difficulty_distribution': {},
                'average_difficulty': 0.0
            }
            
        # Topic distribution
        topic_counts = {}
        for topic, probs in self.problems_by_topic.items():
            topic_counts[topic] = len(probs)
            
        # Difficulty distribution
        difficulty_buckets = {
            'trivial': 0,      # 0.0 - 0.2
            'easy': 0,         # 0.2 - 0.4
            'moderate': 0,     # 0.4 - 0.6
            'hard': 0,         # 0.6 - 0.8
            'very_hard': 0     # 0.8 - 1.0
        }
        
        for problem in self.problems:
            if problem.difficulty <= 0.2:
                difficulty_buckets['trivial'] += 1
            elif problem.difficulty <= 0.4:
                difficulty_buckets['easy'] += 1
            elif problem.difficulty <= 0.6:
                difficulty_buckets['moderate'] += 1
            elif problem.difficulty <= 0.8:
                difficulty_buckets['hard'] += 1
            else:
                difficulty_buckets['very_hard'] += 1
                
        # Average difficulty
        avg_difficulty = sum(p.difficulty for p in self.problems) / len(self.problems)
        
        return {
            'total_problems': len(self.problems),
            'topics': topic_counts,
            'difficulty_distribution': difficulty_buckets,
            'average_difficulty': avg_difficulty,
            'files_loaded': len(set(p.theorem.metadata.get('source_file', '') 
                                  for p in self.problems))
        }