"""
Unit tests for the SymbolicParser component.

Tests the parsing logic that converts sentences into hierarchical
ParseTree structures using the CandidateGenerator.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock
from tier2.domains.language.symbolic_parser import SymbolicParser
from tier2.domains.language.symbolic import RegionCandidate
from tier2.domains.language.candidate_generator import CandidateGenerator
from tier3.world_contexts.knowledge.graph import Concept


class TestSymbolicParser:
    """Test suite for the SymbolicParser class."""
    
    @pytest.fixture
    def mock_candidate_generator(self):
        """Create a mock CandidateGenerator."""
        generator = Mock(spec=CandidateGenerator)
        
        # Default behavior: return some candidates for any phrase
        def mock_generate(phrase):
            # Create different candidates based on the phrase
            if "cat" in phrase.lower():
                return [
                    RegionCandidate({Concept("Cat")}, 0.9, "exact_match"),
                    RegionCandidate({Concept("Feline")}, 0.7, "synonym")
                ]
            elif "mat" in phrase.lower():
                return [
                    RegionCandidate({Concept("Mat")}, 0.8, "exact_match"),
                    RegionCandidate({Concept("Rug")}, 0.6, "synonym")
                ]
            elif "black" in phrase.lower():
                return [
                    RegionCandidate({Concept("Black_Color")}, 0.9, "exact_match")
                ]
            else:
                # Generic candidates for other phrases
                return [
                    RegionCandidate({Concept("Generic")}, 0.5, "fallback")
                ]
        
        generator.generate_candidates_for_phrase.side_effect = mock_generate
        
        # For context-aware generation, accept both phrase and context
        def mock_generate_with_context(phrase, context=None):
            return mock_generate(phrase)
        
        generator.generate_candidates_with_context.side_effect = mock_generate_with_context
        
        return generator
    
    @pytest.fixture
    def parser(self, mock_candidate_generator):
        """Create a SymbolicParser with mock generator."""
        return SymbolicParser(mock_candidate_generator)
    
    def test_parse_simple_sentence(self, parser):
        """Test parsing a simple sentence with no sub-clauses."""
        sentence = "The cat sat on the mat"
        tree = parser.parse_sentence(sentence)
        
        # Should have a single root constraint
        assert tree.root_constraint.text == sentence
        assert len(tree.children) == 0
        
        # Root should be grounded with candidates
        assert tree.root_constraint.is_grounded
        assert len(tree.root_constraint.possible_regions) > 0
        
        # Check all constraints
        all_constraints = tree.get_all_constraints()
        assert len(all_constraints) == 1
    
    def test_parse_sentence_with_relative_clause(self, parser):
        """Test parsing a sentence with a relative clause."""
        sentence = "The cat, which was black, sat on the mat"
        tree = parser.parse_sentence(sentence)
        
        # Should have root and one child
        assert tree.root_constraint.text == "The cat sat on the mat"
        assert len(tree.children) == 1
        
        # Check the relative clause
        relative_constraints = list(tree.children.keys())
        assert len(relative_constraints) == 1
        relative_constraint = relative_constraints[0]
        assert relative_constraint.text == "which was black"
        assert relative_constraint.memoization_key.startswith("relative_")
        
        # Both should be grounded
        assert tree.root_constraint.is_grounded
        assert relative_constraint.is_grounded
        
        # Check tree structure
        assert tree.get_depth() == 2
        all_constraints = tree.get_all_constraints()
        assert len(all_constraints) == 2
    
    def test_parse_sentence_with_multiple_clauses(self, parser):
        """Test parsing a sentence with multiple sub-clauses."""
        sentence = "The cat, which was black, sat on the mat, that was red"
        tree = parser.parse_sentence(sentence)
        
        # Should have root and two children
        assert tree.root_constraint.text == "The cat sat on the mat"
        assert len(tree.children) == 2
        
        # Check both relative clauses
        child_texts = {c.text for c in tree.children.keys()}
        assert "which was black" in child_texts
        assert "that was red" in child_texts
    
    def test_parse_sentence_with_dependent_clause(self, parser):
        """Test parsing a sentence with semicolon-separated clauses."""
        sentence = "The cat sat on the mat; it was comfortable"
        tree = parser.parse_sentence(sentence)
        
        # Root should be the first part
        assert tree.root_constraint.text == "The cat sat on the mat"
        assert len(tree.children) == 1
        
        # Check dependent clause
        dependent_constraint = list(tree.children.keys())[0]
        assert dependent_constraint.text == "it was comfortable"
        assert dependent_constraint.memoization_key.startswith("dependent_")
    
    def test_parse_empty_sentence(self, parser):
        """Test parsing an empty sentence."""
        tree = parser.parse_sentence("")
        
        assert tree.root_constraint.text == ""
        assert len(tree.children) == 0
        assert not tree.root_constraint.is_grounded
    
    def test_parse_with_colon(self, parser):
        """Test parsing a sentence with colon-separated parts."""
        sentence = "Remember this: the cat is always right"
        tree = parser.parse_sentence(sentence)
        
        assert tree.root_constraint.text == "Remember this"
        assert len(tree.children) == 1
        
        dependent = list(tree.children.keys())[0]
        assert dependent.text == "the cat is always right"
    
    def test_beam_width_limiting(self, parser, mock_candidate_generator):
        """Test that beam width limits candidates."""
        # Override the side_effect to return many candidates
        def many_candidates(phrase):
            return [
                RegionCandidate({Concept(f"Concept_{i}")}, 0.9 - i*0.1, "test")
                for i in range(10)
            ]
        
        mock_candidate_generator.generate_candidates_for_phrase.side_effect = many_candidates
        
        sentence = "Test sentence"
        tree = parser.parse_sentence(sentence)
        
        # Should only keep top 5 (default beam width)
        assert len(tree.root_constraint.possible_regions) == 5
        
        # Should be sorted by probability
        probs = [c.probability for c in tree.root_constraint.possible_regions]
        assert probs == sorted(probs, reverse=True)
    
    def test_chunking_edge_cases(self, parser):
        """Test various edge cases in sentence chunking."""
        # Multiple commas
        sentence = "The cat, tired and hungry, which had been outside, came home"
        tree = parser.parse_sentence(sentence)
        # Should identify "which had been outside" as relative clause
        child_texts = {c.text for c in tree.children.keys()}
        assert "which had been outside" in child_texts
        
        # Nested structure (not fully supported in V1 but shouldn't crash)
        sentence = "The cat said: the dog, who was brave, saved the day"
        tree = parser.parse_sentence(sentence)
        assert tree is not None
        assert tree.root_constraint is not None
    
    def test_parse_with_context(self, parser, mock_candidate_generator):
        """Test context-aware parsing."""
        sentence = "The cat sat on it"
        context = "There was a comfortable mat in the room"
        
        # Parse with context
        tree = parser.parse_with_context(sentence, context)
        
        # Should have called generate_candidates_with_context
        assert mock_candidate_generator.generate_candidates_with_context.called
        
        # Tree structure should be the same
        assert tree.root_constraint.text == sentence
        assert tree.root_constraint.is_grounded
    
    def test_memoization_keys(self, parser):
        """Test that memoization keys are properly generated."""
        sentence = "The cat, which was black, sat on the mat; it purred"
        tree = parser.parse_sentence(sentence)
        
        # Check main clause key
        assert tree.root_constraint.memoization_key == "main_the_cat_sat_on_the_mat"
        
        # Check child keys
        for constraint in tree.children.keys():
            if "which was black" in constraint.text:
                assert constraint.memoization_key == "relative_which_was_black"
            elif "it purred" in constraint.text:
                assert constraint.memoization_key == "dependent_it_purred"
    
    def test_tree_traversal_methods(self, parser):
        """Test ParseTree utility methods."""
        sentence = "The cat, which was black, sat on the mat, that was red"
        tree = parser.parse_sentence(sentence)
        
        # Test get_all_constraints
        all_constraints = tree.get_all_constraints()
        assert len(all_constraints) == 3
        texts = {c.text for c in all_constraints}
        assert "The cat sat on the mat" in texts
        assert "which was black" in texts
        assert "that was red" in texts
        
        # Test get_depth
        assert tree.get_depth() == 2
        
        # Test repr
        repr_str = repr(tree)
        assert "root='The cat sat on the mat'" in repr_str
        assert "children=2" in repr_str
        assert "depth=2" in repr_str


    def test_parse_sequence_with_pronouns(self, parser, mock_candidate_generator):
        """Test parsing a sequence with pronoun resolution."""
        # Set up mock to track calls
        call_history = []
        
        def track_calls(phrase):
            call_history.append(phrase)
            # Return different candidates based on phrase
            if "cat" in phrase.lower():
                return [
                    RegionCandidate({Concept("Cat")}, 0.9, "exact_match"),
                    RegionCandidate({Concept("Feline")}, 0.7, "synonym")
                ]
            elif "mat" in phrase.lower():
                return [
                    RegionCandidate({Concept("Mat")}, 0.8, "exact_match")
                ]
            elif "it" in phrase.lower():
                # This shouldn't be called if pronoun resolution works
                return [
                    RegionCandidate({Concept("Generic_It")}, 0.3, "fallback")
                ]
            else:
                return [
                    RegionCandidate({Concept("Generic")}, 0.5, "fallback")
                ]
        
        mock_candidate_generator.generate_candidates_for_phrase.side_effect = track_calls
        mock_candidate_generator.generate_candidates_with_context.side_effect = track_calls
        
        # Parse sequence
        sentences = [
            "The cat sat on the mat",
            "It was comfortable"
        ]
        
        trees = parser.parse_sequence(sentences)
        
        # Should have two trees
        assert len(trees) == 2
        
        # First tree should be normal
        assert trees[0].root_constraint.text == "The cat sat on the mat"
        
        # Second tree should have the pronoun sentence
        assert trees[1].root_constraint.text == "It was comfortable"
        
        # Parser should have built up context from first sentence
        assert len(parser.parsing_context) > 0
        
        # Context should include cat and mat concepts
        context_names = [c for c in parser.parsing_context]
        assert any("cat" in str(c).lower() for c in context_names)
    
    def test_clear_context(self, parser):
        """Test clearing the parsing context."""
        # Add some context
        parser.parsing_context = [Concept("cat"), Concept("dog")]
        
        # Clear it
        parser.clear_context()
        
        # Should be empty
        assert parser.parsing_context == []
    
    def test_context_window_limit(self, parser, mock_candidate_generator):
        """Test that context window size is maintained."""
        # Set small window for testing
        parser.context_window_size = 3
        
        # Parse multiple sentences to build up context
        sentences = [
            "The cat sat",
            "The dog ran",
            "The bird flew",
            "The fish swam"
        ]
        
        for sentence in sentences:
            parser.parse_sentence(sentence)
        
        # Context should not exceed window size
        assert len(parser.parsing_context) <= parser.context_window_size * 3  # 3 concepts per sentence max


class TestSymbolicParserIntegration:
    """Integration tests with real CandidateGenerator."""
    
    def test_with_real_candidate_generator(self):
        """Test parser with a real CandidateGenerator (simplified)."""
        from tier3.world_contexts.knowledge.graph import WorldKnowledgeGraph
        from tier3.world_contexts.knowledge.hub import KnowledgeHub
        
        # Create minimal knowledge graph
        graph = WorldKnowledgeGraph()
        graph.add_concept(Concept("Cat"))
        graph.add_concept(Concept("Mat"))
        
        hub = KnowledgeHub()
        hub.wkg = graph
        
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Parse a simple sentence
        sentence = "cat mat"
        tree = parser.parse_sentence(sentence)
        
        assert tree.root_constraint.text == sentence
        assert tree.root_constraint.is_grounded
        assert len(tree.root_constraint.possible_regions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])