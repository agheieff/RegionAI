"""
Tests for the mathematical curriculum manager.
"""

import tempfile
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pathlib import Path
from unittest.mock import patch

from regionai.world_contexts.math_curriculum import MathCurriculum, MathProblem
from regionai.linguistics.lean_ast import Theorem, Hypothesis


class TestMathProblem:
    """Test the MathProblem class."""
    
    def test_math_problem_creation(self):
        """Test creating a MathProblem."""
        theorem = Theorem(
            name="test_theorem",
            statement="p → p",
            hypotheses=[Hypothesis("p", "Prop")]
        )
        
        problem = MathProblem(
            theorem=theorem,
            difficulty=0.5,
            topics=["logic", "implication"]
        )
        
        assert problem.theorem == theorem
        assert problem.difficulty == 0.5
        assert problem.topics == ["logic", "implication"]
        assert problem.input_data == "Prove: test_theorem"
        assert problem.output_data == "p → p"
    
    def test_math_problem_metadata(self):
        """Test MathProblem metadata generation."""
        theorem = Theorem(
            name="modus_ponens",
            statement="p → (p → q) → q",
            hypotheses=[
                Hypothesis("p", "Prop"),
                Hypothesis("q", "Prop")
            ],
            metadata={'source_file': 'test.lean'}
        )
        
        problem = MathProblem(
            theorem=theorem,
            difficulty=0.3,
            topics=["logic"],
            prerequisites=["self_implication"]
        )
        
        assert problem.metadata['theorem_name'] == "modus_ponens"
        assert problem.metadata['hypotheses_count'] == 2
        assert problem.metadata['source_file'] == 'test.lean'
        assert problem.metadata['difficulty'] == 0.3
        assert problem.metadata['topics'] == ["logic"]


class TestMathCurriculum:
    """Test the MathCurriculum class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.curriculum = MathCurriculum(curriculum_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test MathCurriculum initialization."""
        assert self.curriculum.curriculum_dir == Path(self.temp_dir)
        assert self.curriculum.problems == []
        assert self.curriculum.problems_by_topic == {}
        assert self.curriculum.problems_by_name == {}
    
    def test_load_empty_directory(self):
        """Test loading from empty directory."""
        self.curriculum.load_curriculum()
        assert len(self.curriculum.problems) == 0
    
    def test_load_single_file(self):
        """Test loading a single .lean file."""
        # Create a test file
        lean_file = Path(self.temp_dir) / "test.lean"
        lean_file.write_text("""
        theorem simple : p → p
        theorem modus_ponens (p q : Prop) : p → (p → q) → q
        """)
        
        self.curriculum.load_curriculum()
        
        assert len(self.curriculum.problems) == 2
        assert "simple" in self.curriculum.problems_by_name
        assert "modus_ponens" in self.curriculum.problems_by_name
    
    def test_load_nested_files(self):
        """Test loading from nested directory structure."""
        # Create nested structure
        logic_dir = Path(self.temp_dir) / "logic"
        logic_dir.mkdir()
        
        (logic_dir / "basic.lean").write_text("theorem identity : p → p")
        (logic_dir / "advanced.lean").write_text("theorem complex : ∀x, P(x) → Q(x)")
        
        self.curriculum.load_curriculum()
        
        assert len(self.curriculum.problems) == 2
        # Check that logic topic was extracted from directory
        assert "logic" in self.curriculum.problems_by_topic
    
    def test_load_with_parse_error(self):
        """Test handling parse errors gracefully."""
        # Create a file with invalid syntax
        bad_file = Path(self.temp_dir) / "bad.lean"
        bad_file.write_text("theorem incomplete")
        
        # Should not raise exception
        self.curriculum.load_curriculum()
        # Bad file should be skipped
        assert len(self.curriculum.problems) == 0
    
    def test_estimate_difficulty(self):
        """Test difficulty estimation."""
        # Test simple theorem
        simple = Theorem("self", "p → p")
        assert self.curriculum._estimate_difficulty(simple) < 0.2
        
        # Test with quantifiers
        forall_theorem = Theorem("universal", "∀x, P(x)")
        assert self.curriculum._estimate_difficulty(forall_theorem) > 0.6
        
        # Test with multiple operators
        complex_theorem = Theorem("complex", "p ∧ q → r ∨ s")
        difficulty = self.curriculum._estimate_difficulty(complex_theorem)
        assert 0.4 < difficulty < 0.8
    
    def test_extract_topics(self):
        """Test topic extraction."""
        # Implication
        impl_theorem = Theorem("impl", "p → q")
        topics = self.curriculum._extract_topics(impl_theorem, "default")
        assert "implication" in topics
        assert "default" in topics
        
        # Conjunction and disjunction
        and_or_theorem = Theorem("and_or", "p ∧ q ∨ r")
        topics = self.curriculum._extract_topics(and_or_theorem, "logic")
        assert "conjunction" in topics
        assert "disjunction" in topics
        
        # Commutativity
        comm_theorem = Theorem("and_comm", "p ∧ q → q ∧ p")
        topics = self.curriculum._extract_topics(comm_theorem, "algebra")
        assert "commutativity" in topics
    
    def test_get_problems_by_difficulty(self):
        """Test filtering problems by difficulty."""
        # Create problems with different difficulties
        easy = MathProblem(
            theorem=Theorem("easy", "p → p"),
            difficulty=0.1
        )
        medium = MathProblem(
            theorem=Theorem("medium", "p → q → p"),
            difficulty=0.5
        )
        hard = MathProblem(
            theorem=Theorem("hard", "∀x, ∃y, P(x,y)"),
            difficulty=0.9
        )
        
        self.curriculum.problems = [easy, medium, hard]
        
        # Test difficulty ranges
        basic = self.curriculum.get_problems(difficulty_range=(0.0, 0.3))
        assert len(basic) == 1
        assert basic[0].theorem.name == "easy"
        
        intermediate = self.curriculum.get_problems(difficulty_range=(0.3, 0.7))
        assert len(intermediate) == 1
        assert intermediate[0].theorem.name == "medium"
    
    def test_get_problems_by_topic(self):
        """Test filtering problems by topic."""
        p1 = MathProblem(
            theorem=Theorem("t1", "p → q"),
            topics=["logic", "implication"]
        )
        p2 = MathProblem(
            theorem=Theorem("t2", "p ∧ q"),
            topics=["logic", "conjunction"]
        )
        p3 = MathProblem(
            theorem=Theorem("t3", "∀x, P(x)"),
            topics=["quantification"]
        )
        
        self.curriculum.problems = [p1, p2, p3]
        
        logic_problems = self.curriculum.get_problems(topics=["logic"])
        assert len(logic_problems) == 2
        
        impl_problems = self.curriculum.get_problems(topics=["implication"])
        assert len(impl_problems) == 1
        assert impl_problems[0].theorem.name == "t1"
    
    def test_get_problems_with_limit(self):
        """Test limiting number of returned problems."""
        # Create 10 problems
        for i in range(10):
            self.curriculum.problems.append(
                MathProblem(
                    theorem=Theorem(f"t{i}", "p → p"),
                    difficulty=i / 10.0
                )
            )
        
        limited = self.curriculum.get_problems(limit=5)
        assert len(limited) == 5
        # Should be sorted by difficulty
        assert all(limited[i].difficulty <= limited[i+1].difficulty 
                  for i in range(4))
    
    def test_get_problem_by_name(self):
        """Test retrieving specific problem by name."""
        theorem = Theorem("specific", "p → p")
        problem = MathProblem(theorem=theorem)
        self.curriculum.problems_by_name["specific"] = problem
        
        retrieved = self.curriculum.get_problem_by_name("specific")
        assert retrieved == problem
        
        assert self.curriculum.get_problem_by_name("nonexistent") is None
    
    def test_get_curriculum_stats(self):
        """Test getting curriculum statistics."""
        # Empty curriculum
        stats = self.curriculum.get_curriculum_stats()
        assert stats['total_problems'] == 0
        
        # Add some problems
        self.curriculum.problems = [
            MathProblem(
                theorem=Theorem("easy1", "p"),
                difficulty=0.1,
                topics=["logic"]
            ),
            MathProblem(
                theorem=Theorem("easy2", "q"),
                difficulty=0.15,
                topics=["logic", "basic"]
            ),
            MathProblem(
                theorem=Theorem("hard", "∀x, P(x)"),
                difficulty=0.8,
                topics=["quantification"]
            )
        ]
        
        # Update topic index
        for p in self.curriculum.problems:
            for topic in p.topics:
                if topic not in self.curriculum.problems_by_topic:
                    self.curriculum.problems_by_topic[topic] = []
                self.curriculum.problems_by_topic[topic].append(p)
        
        stats = self.curriculum.get_curriculum_stats()
        assert stats['total_problems'] == 3
        assert stats['topics']['logic'] == 2
        assert stats['topics']['quantification'] == 1
        assert stats['difficulty_distribution']['trivial'] == 2
        assert stats['difficulty_distribution']['hard'] == 1
        assert 0.3 < stats['average_difficulty'] < 0.4


class TestMathCurriculumIntegration:
    """Test integration with the curriculum factory."""
    
    @patch('regionai.data.math_curriculum.MathCurriculum.load_curriculum')
    @patch('regionai.data.math_curriculum.MathCurriculum.get_problems')
    def test_factory_integration(self, mock_get_problems, mock_load):
        """Test that MathCurriculum integrates with factory."""
        from regionai.data.curriculum_factory import create_curriculum
        
        # Mock the get_problems to return test data
        mock_problems = [
            MathProblem(theorem=Theorem("t1", "p → p"), difficulty=0.1),
            MathProblem(theorem=Theorem("t2", "q → q"), difficulty=0.2),
        ]
        mock_get_problems.return_value = mock_problems
        
        # Create curriculum through factory
        problems = create_curriculum(
            "math_foundations",
            difficulty="basic",
            num_problems=2
        )
        
        # Verify load was called
        mock_load.assert_called_once()
        
        # Verify get_problems was called with correct params
        mock_get_problems.assert_called_once()
        call_args = mock_get_problems.call_args
        assert call_args[1]['difficulty_range'] == (0.0, 0.3)
        assert call_args[1]['limit'] == 2
        
        # Verify returned problems
        assert len(problems) == 2
        assert all(isinstance(p, MathProblem) for p in problems)