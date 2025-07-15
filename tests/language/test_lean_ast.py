"""
Tests for Lean AST data structures.
"""

from tier2.linguistics.lean_ast import (
    Hypothesis, Tactic, TacticType, Theorem, ProofState,
    ProofStep, TheoremDatabase
)


class TestHypothesis:
    """Test the Hypothesis dataclass."""
    
    def test_hypothesis_creation(self):
        """Test creating a hypothesis."""
        hyp = Hypothesis(name="h1", type_expr="n > 0")
        assert hyp.name == "h1"
        assert hyp.type_expr == "n > 0"
        assert hyp.value is None
        assert hyp.metadata == {}
    
    def test_hypothesis_with_value(self):
        """Test hypothesis with a value."""
        hyp = Hypothesis(name="x", type_expr="Nat", value="5")
        assert hyp.value == "5"
        assert str(hyp) == "x : Nat := 5"
    
    def test_hypothesis_to_lean(self):
        """Test converting hypothesis to Lean syntax."""
        hyp = Hypothesis(name="h", type_expr="P ∧ Q")
        assert hyp.to_lean() == "h : P ∧ Q"


class TestTactic:
    """Test the Tactic dataclass."""
    
    def test_tactic_creation(self):
        """Test creating a tactic."""
        tactic = Tactic(TacticType.INTRO)
        assert tactic.tactic_type == TacticType.INTRO
        assert tactic.arguments == []
        assert tactic.target is None
    
    def test_tactic_with_arguments(self):
        """Test tactic with arguments."""
        tactic = Tactic(TacticType.APPLY, arguments=["lemma1", "h"])
        assert tactic.arguments == ["lemma1", "h"]
        assert str(tactic) == "apply lemma1 h"
    
    def test_tactic_with_target(self):
        """Test tactic with target."""
        tactic = Tactic(TacticType.REWRITE, target="h1", arguments=["at", "h2"])
        assert tactic.target == "h1"
        assert str(tactic) == "rewrite h1 at h2"
    
    def test_is_closing_tactic(self):
        """Test identifying closing tactics."""
        assert Tactic(TacticType.EXACT).is_closing_tactic()
        assert Tactic(TacticType.ASSUMPTION).is_closing_tactic()
        assert Tactic(TacticType.RING).is_closing_tactic()
        assert not Tactic(TacticType.INTRO).is_closing_tactic()
        assert not Tactic(TacticType.APPLY).is_closing_tactic()


class TestProofState:
    """Test the ProofState dataclass."""
    
    def test_empty_proof_state(self):
        """Test creating an empty proof state."""
        state = ProofState()
        assert state.goals == []
        assert state.hypotheses == []
        assert not state.completed
    
    def test_proof_state_with_goals(self):
        """Test proof state with goals."""
        state = ProofState(goals=["P → Q", "Q → R"])
        assert len(state.goals) == 2
        assert "P → Q" in state.goals
    
    def test_completed_proof_state(self):
        """Test completed proof state."""
        state = ProofState(completed=True)
        assert state.completed
        assert str(state) == "Proof complete!"
    
    def test_proof_state_string_representation(self):
        """Test string representation of proof state."""
        hyp = Hypothesis("h", "P")
        state = ProofState(
            goals=["P → Q"],
            hypotheses=[hyp]
        )
        output = str(state)
        assert "Hypotheses:" in output
        assert "h : P" in output
        assert "Goals:" in output
        assert "1. P → Q" in output


class TestTheorem:
    """Test the Theorem dataclass."""
    
    def test_theorem_creation(self):
        """Test creating a theorem."""
        theorem = Theorem(name="simple", statement="P → P")
        assert theorem.name == "simple"
        assert theorem.statement == "P → P"
        assert theorem.proof_tactics == []
    
    def test_theorem_with_proof(self):
        """Test theorem with proof tactics."""
        theorem = Theorem(name="impl_self", statement="P → P")
        theorem.add_tactic(Tactic(TacticType.INTRO, arguments=["h"]))
        theorem.add_tactic(Tactic(TacticType.EXACT, arguments=["h"]))
        
        assert theorem.get_proof_length() == 2
        assert theorem.uses_tactic(TacticType.INTRO)
        assert theorem.uses_tactic(TacticType.EXACT)
        assert not theorem.uses_tactic(TacticType.RING)
    
    def test_theorem_to_lean(self):
        """Test converting theorem to Lean syntax."""
        theorem = Theorem(name="test", statement="A ∧ B → B ∧ A")
        theorem.add_tactic(Tactic(TacticType.INTRO, arguments=["h"]))
        theorem.add_tactic(Tactic(TacticType.CONSTRUCTOR))
        
        lean_code = theorem.to_lean()
        assert "theorem test : A ∧ B → B ∧ A := by" in lean_code
        assert "  intro h" in lean_code
        assert "  constructor" in lean_code
    
    def test_tactic_distribution(self):
        """Test getting tactic distribution."""
        theorem = Theorem(name="test", statement="P")
        theorem.add_tactic(Tactic(TacticType.INTRO))
        theorem.add_tactic(Tactic(TacticType.INTRO))
        theorem.add_tactic(Tactic(TacticType.APPLY))
        
        dist = theorem.get_tactic_distribution()
        assert dist[TacticType.INTRO] == 2
        assert dist[TacticType.APPLY] == 1
        assert TacticType.EXACT not in dist


class TestProofStep:
    """Test the ProofStep dataclass."""
    
    def test_proof_step_creation(self):
        """Test creating a proof step."""
        tactic = Tactic(TacticType.INTRO)
        before = ProofState(goals=["P → Q"])
        after = ProofState(goals=["Q"], hypotheses=[Hypothesis("h", "P")])
        
        step = ProofStep(
            step_number=1,
            tactic=tactic,
            before_state=before,
            after_state=after,
            success=True,
            time_ms=10.5
        )
        
        assert step.step_number == 1
        assert step.success
        assert step.time_ms == 10.5
    
    def test_proof_step_to_dict(self):
        """Test converting proof step to dictionary."""
        tactic = Tactic(TacticType.APPLY, arguments=["lemma"])
        before = ProofState(goals=["Goal1", "Goal2"])
        after = ProofState(goals=["Goal2"])
        
        step = ProofStep(
            step_number=5,
            tactic=tactic,
            before_state=before,
            after_state=after,
            success=True,
            time_ms=25.0
        )
        
        data = step.to_dict()
        assert data['step_number'] == 5
        assert data['tactic'] == "apply lemma"
        assert data['tactic_type'] == "apply"
        assert data['before_goals'] == ["Goal1", "Goal2"]
        assert data['after_goals'] == ["Goal2"]
        assert data['success'] is True
        assert data['time_ms'] == 25.0


class TestTheoremDatabase:
    """Test the TheoremDatabase class."""
    
    def test_database_creation(self):
        """Test creating a theorem database."""
        db = TheoremDatabase()
        assert db.theorems == {}
        assert db.by_tactic == {}
    
    def test_add_and_get_theorem(self):
        """Test adding and retrieving theorems."""
        db = TheoremDatabase()
        theorem = Theorem(name="test", statement="P")
        theorem.add_tactic(Tactic(TacticType.SIMP))
        
        db.add_theorem(theorem)
        
        retrieved = db.get_theorem("test")
        assert retrieved is not None
        assert retrieved.name == "test"
        
        assert db.get_theorem("nonexistent") is None
    
    def test_find_theorems_by_tactic(self):
        """Test finding theorems that use specific tactics."""
        db = TheoremDatabase()
        
        # Add theorems with different tactics
        t1 = Theorem(name="t1", statement="P1")
        t1.add_tactic(Tactic(TacticType.SIMP))
        
        t2 = Theorem(name="t2", statement="P2")
        t2.add_tactic(Tactic(TacticType.SIMP))
        t2.add_tactic(Tactic(TacticType.RING))
        
        t3 = Theorem(name="t3", statement="P3")
        t3.add_tactic(Tactic(TacticType.RING))
        
        db.add_theorem(t1)
        db.add_theorem(t2)
        db.add_theorem(t3)
        
        simp_theorems = db.find_theorems_using_tactic(TacticType.SIMP)
        assert len(simp_theorems) == 2
        assert any(t.name == "t1" for t in simp_theorems)
        assert any(t.name == "t2" for t in simp_theorems)
        
        ring_theorems = db.find_theorems_using_tactic(TacticType.RING)
        assert len(ring_theorems) == 2
        assert any(t.name == "t2" for t in ring_theorems)
        assert any(t.name == "t3" for t in ring_theorems)
    
    def test_database_statistics(self):
        """Test getting database statistics."""
        db = TheoremDatabase()
        
        t1 = Theorem(name="t1", statement="P1")
        t1.add_tactic(Tactic(TacticType.INTRO))
        t1.add_tactic(Tactic(TacticType.EXACT))
        
        t2 = Theorem(name="t2", statement="P2")
        t2.add_tactic(Tactic(TacticType.SIMP))
        
        db.add_theorem(t1)
        db.add_theorem(t2)
        
        stats = db.get_statistics()
        assert stats['total_theorems'] == 2
        assert stats['total_tactics'] == 3
        assert stats['average_proof_length'] == 1.5
        assert stats['tactic_usage']['intro'] == 1
        assert stats['tactic_usage']['exact'] == 1
        assert stats['tactic_usage']['simp'] == 1