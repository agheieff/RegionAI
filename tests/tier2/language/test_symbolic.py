"""
Unit tests for the symbolic language engine data models.

Tests the RegionCandidate and SymbolicConstraint dataclasses to ensure
they correctly implement the design specified in DESIGN-XV.md.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tier2.domains.language.symbolic import RegionCandidate, SymbolicConstraint
from tier3.world_contexts.knowledge.graph import Concept


class TestRegionCandidate:
    """Test suite for RegionCandidate dataclass."""
    
    def test_basic_instantiation(self):
        """Test creating a RegionCandidate with valid values."""
        concepts = {Concept("Cat"), Concept("Animal")}
        candidate = RegionCandidate(
            concept_intersections=concepts,
            probability=0.85,
            source_heuristic="noun_phrase_analyzer"
        )
        
        assert candidate.concept_intersections == concepts
        assert candidate.probability == 0.85
        assert candidate.source_heuristic == "noun_phrase_analyzer"
    
    def test_probability_validation(self):
        """Test that probability must be between 0.0 and 1.0."""
        concepts = {Concept("Dog")}
        
        # Valid probabilities
        RegionCandidate(concepts, 0.0, "test")
        RegionCandidate(concepts, 1.0, "test")
        RegionCandidate(concepts, 0.5, "test")
        
        # Invalid probabilities
        with pytest.raises(ValueError, match="Probability must be between"):
            RegionCandidate(concepts, -0.1, "test")
        
        with pytest.raises(ValueError, match="Probability must be between"):
            RegionCandidate(concepts, 1.1, "test")
    
    def test_equality(self):
        """Test equality comparison between RegionCandidates."""
        cat_concept = Concept("Cat")
        animal_concept = Concept("Animal")
        
        candidate1 = RegionCandidate(
            {cat_concept, animal_concept},
            0.8,
            "analyzer_1"
        )
        
        candidate2 = RegionCandidate(
            {cat_concept, animal_concept},
            0.8,
            "analyzer_1"
        )
        
        candidate3 = RegionCandidate(
            {cat_concept, animal_concept},
            0.7,  # Different probability
            "analyzer_1"
        )
        
        candidate4 = RegionCandidate(
            {cat_concept},  # Different concepts
            0.8,
            "analyzer_1"
        )
        
        candidate5 = RegionCandidate(
            {cat_concept, animal_concept},
            0.8,
            "analyzer_2"  # Different source
        )
        
        # Same concepts and source = equal
        assert candidate1 == candidate2
        
        # Different probability but same concepts/source = equal
        assert candidate1 == candidate3
        
        # Different concepts = not equal
        assert candidate1 != candidate4
        
        # Different source = not equal
        assert candidate1 != candidate5
    
    def test_hashability(self):
        """Test that RegionCandidates can be used in sets and dicts."""
        cat = Concept("Cat")
        dog = Concept("Dog")
        
        candidate1 = RegionCandidate({cat}, 0.9, "test")
        candidate2 = RegionCandidate({cat}, 0.8, "test")  # Same as 1, different prob
        candidate3 = RegionCandidate({dog}, 0.9, "test")  # Different concept
        
        # Can create a set
        candidate_set = {candidate1, candidate2, candidate3}
        
        # candidate1 and candidate2 are considered the same (same hash)
        assert len(candidate_set) == 2
        
        # Can use as dict keys
        candidate_dict = {
            candidate1: "cat_candidate",
            candidate3: "dog_candidate"
        }
        assert len(candidate_dict) == 2


class TestSymbolicConstraint:
    """Test suite for SymbolicConstraint dataclass."""
    
    def test_basic_instantiation(self):
        """Test creating a SymbolicConstraint with default values."""
        constraint = SymbolicConstraint(text="the red car")
        
        assert constraint.text == "the red car"
        assert constraint.possible_regions == []
        assert constraint.is_grounded is False
        assert constraint.memoization_key == "constraint_the_red_car"
    
    def test_custom_memoization_key(self):
        """Test providing a custom memoization key."""
        constraint = SymbolicConstraint(
            text="the cat",
            memoization_key="NP_the_cat_subj"
        )
        
        assert constraint.memoization_key == "NP_the_cat_subj"
    
    def test_add_candidate_simple(self):
        """Test adding candidates to possible_regions."""
        constraint = SymbolicConstraint(text="cat")
        
        cat_concept = Concept("Cat")
        feline_concept = Concept("Feline")
        
        candidate1 = RegionCandidate({cat_concept}, 0.9, "noun_analyzer")
        candidate2 = RegionCandidate({feline_concept}, 0.7, "taxonomy_analyzer")
        
        constraint.add_candidate(candidate1)
        constraint.add_candidate(candidate2)
        
        assert len(constraint.possible_regions) == 2
        assert candidate1 in constraint.possible_regions
        assert candidate2 in constraint.possible_regions
    
    def test_add_candidate_with_beam_width(self):
        """Test that beam width limits the number of candidates."""
        constraint = SymbolicConstraint(text="bank")
        
        # Create candidates with different probabilities
        candidates = [
            RegionCandidate({Concept("Financial_Bank")}, 0.8, "context"),
            RegionCandidate({Concept("River_Bank")}, 0.6, "context"),
            RegionCandidate({Concept("Blood_Bank")}, 0.3, "medical"),
            RegionCandidate({Concept("Memory_Bank")}, 0.2, "tech"),
        ]
        
        # Add all candidates with beam_width=2
        for candidate in candidates:
            constraint.add_candidate(candidate, beam_width=2)
        
        # Should only keep top 2
        assert len(constraint.possible_regions) == 2
        assert constraint.possible_regions[0].probability == 0.8
        assert constraint.possible_regions[1].probability == 0.6
    
    def test_ground_constraint(self):
        """Test grounding a constraint with candidates."""
        constraint = SymbolicConstraint(text="the dog")
        
        assert constraint.is_grounded is False
        
        candidates = [
            RegionCandidate({Concept("Dog")}, 0.95, "noun_phrase"),
            RegionCandidate({Concept("Canine")}, 0.85, "taxonomy")
        ]
        
        constraint.ground(candidates)
        
        assert constraint.is_grounded is True
        assert constraint.possible_regions == candidates
    
    def test_get_top_candidate(self):
        """Test retrieving the most probable candidate."""
        constraint = SymbolicConstraint(text="apple")
        
        # No candidates initially
        assert constraint.get_top_candidate() is None
        
        # Add candidates
        fruit_candidate = RegionCandidate({Concept("Fruit")}, 0.7, "food")
        tech_candidate = RegionCandidate({Concept("Apple_Inc")}, 0.9, "company")
        
        constraint.add_candidate(fruit_candidate)
        constraint.add_candidate(tech_candidate)
        
        # Should return highest probability
        top = constraint.get_top_candidate()
        assert top == tech_candidate
        assert top.probability == 0.9
    
    def test_repr(self):
        """Test string representation of SymbolicConstraint."""
        constraint = SymbolicConstraint(text="test phrase")
        
        # Ungrounded, no candidates
        assert "test phrase" in repr(constraint)
        assert "ungrounded" in repr(constraint)
        assert "0 candidates" in repr(constraint)
        
        # Add some candidates and ground it
        constraint.ground([
            RegionCandidate({Concept("A")}, 0.5, "test"),
            RegionCandidate({Concept("B")}, 0.6, "test")
        ])
        
        assert "grounded" in repr(constraint)
        assert "2 candidates" in repr(constraint)


class TestIntegration:
    """Test interactions between RegionCandidate and SymbolicConstraint."""
    
    def test_complete_workflow(self):
        """Test a complete workflow from constraint creation to grounding."""
        # Create an ungrounded constraint
        constraint = SymbolicConstraint(text="the quick brown fox")
        
        # Verify initial state
        assert not constraint.is_grounded
        assert len(constraint.possible_regions) == 0
        
        # Simulate candidate generation (would normally come from analyzers)
        fox_animal = RegionCandidate(
            concept_intersections={Concept("Fox"), Concept("Animal")},
            probability=0.85,
            source_heuristic="noun_phrase_analyzer"
        )
        
        fox_cunning = RegionCandidate(
            concept_intersections={Concept("Fox"), Concept("Cunning")},
            probability=0.65,
            source_heuristic="metaphor_analyzer"
        )
        
        # Add candidates with beam width
        constraint.add_candidate(fox_animal, beam_width=5)
        constraint.add_candidate(fox_cunning, beam_width=5)
        
        # Verify candidates were added
        assert len(constraint.possible_regions) == 2
        
        # Get top candidate
        top = constraint.get_top_candidate()
        assert top.probability == 0.85
        assert Concept("Animal") in top.concept_intersections
        
        # Ground the constraint (simulate lazy evaluation triggered)
        constraint.is_grounded = True
        
        # Verify final state
        assert constraint.is_grounded
        assert len(constraint.possible_regions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])