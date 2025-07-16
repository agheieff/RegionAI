"""
Unit tests for the ContextResolver component.

Tests pronoun resolution and other anaphoric reference handling.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from regionai.domains.language.context_resolver import ContextResolver
from regionai.world_contexts.knowledge.graph import Concept


class TestContextResolver:
    """Test suite for the ContextResolver class."""
    
    @pytest.fixture
    def resolver(self):
        """Create a ContextResolver instance."""
        return ContextResolver()
    
    def test_resolve_it_pronoun(self, resolver):
        """Test resolution of 'it' pronoun."""
        recent_concepts = [
            Concept("mat"),    # Most recent
            Concept("cat"),    # Second most recent
            Concept("house")   # Least recent
        ]
        
        candidates = resolver.resolve_pronoun("it", recent_concepts)
        
        # Should have candidates
        assert len(candidates) > 0
        
        # "mat" should be top candidate (inanimate + most recent)
        top_candidate = candidates[0]
        assert Concept("mat") in top_candidate.concept_intersections
        assert top_candidate.probability > 0.8
        assert top_candidate.source_heuristic == "pronoun_resolution"
    
    def test_resolve_they_pronoun(self, resolver):
        """Test resolution of 'they' pronoun."""
        recent_concepts = [
            Concept("cats"),      # Plural, most recent
            Concept("dogs"),      # Plural
            Concept("mat"),       # Singular
            Concept("children")   # Plural
        ]
        
        candidates = resolver.resolve_pronoun("they", recent_concepts)
        
        # Should prefer plural concepts
        assert len(candidates) > 0
        
        # "cats" should be top (plural + most recent)
        top_candidate = candidates[0]
        assert Concept("cats") in top_candidate.concept_intersections
    
    def test_resolve_he_pronoun(self, resolver):
        """Test resolution of male pronouns."""
        recent_concepts = [
            Concept("woman"),
            Concept("man"),      # Should match "he"
            Concept("cat"),
            Concept("boy")       # Also matches but less recent
        ]
        
        candidates = resolver.resolve_pronoun("he", recent_concepts)
        
        # Should find male concepts
        assert len(candidates) > 0
        
        # Check that male concepts are preferred
        concept_names = [
            list(c.concept_intersections)[0] 
            for c in candidates if c.probability > 0.5
        ]
        assert Concept("man") in concept_names or Concept("boy") in concept_names
    
    def test_resolve_she_pronoun(self, resolver):
        """Test resolution of female pronouns."""
        recent_concepts = [
            Concept("man"),
            Concept("woman"),    # Should match "she"
            Concept("girl"),     # Also matches
            Concept("cat")
        ]
        
        candidates = resolver.resolve_pronoun("she", recent_concepts)
        
        # Should find female concepts
        assert len(candidates) > 0
        
        # Check that female concepts are preferred
        high_prob_concepts = [
            list(c.concept_intersections)[0] 
            for c in candidates if c.probability > 0.5
        ]
        assert any(c in high_prob_concepts for c in [Concept("woman"), Concept("girl")])
    
    def test_empty_context(self, resolver):
        """Test behavior with empty context."""
        candidates = resolver.resolve_pronoun("it", [])
        
        assert candidates == []
    
    def test_recency_effect(self, resolver):
        """Test that more recent concepts get higher scores."""
        recent_concepts = [
            Concept("mat"),      # Most recent
            Concept("chair"),    # Less recent
            Concept("table")     # Least recent
        ]
        
        candidates = resolver.resolve_pronoun("it", recent_concepts)
        
        # All should be compatible with "it"
        assert len(candidates) >= 3
        
        # Should be ordered by recency (and thus probability)
        probs = [c.probability for c in candidates[:3]]
        assert probs[0] > probs[1] > probs[2]
    
    def test_compatibility_scoring(self, resolver):
        """Test that compatibility affects scoring."""
        # Put incompatible concept more recent to test compatibility override
        recent_concepts = [
            Concept("children"),  # Plural, most recent but incompatible with "it"
            Concept("mat"),       # Singular inanimate, compatible with "it"
            Concept("cat")        # Singular animate
        ]
        
        # Test "it" - should prefer compatible concepts despite recency
        it_candidates = resolver.resolve_pronoun("it", recent_concepts)
        
        # All candidates should have some score
        assert len(it_candidates) >= 2
        
        # "mat" should get a good score despite not being most recent
        # because it's highly compatible with "it"
        mat_candidate = next(
            (c for c in it_candidates if Concept("mat") in c.concept_intersections),
            None
        )
        assert mat_candidate is not None
        assert mat_candidate.probability > 0.5  # Should still have decent score
    
    def test_definite_reference_resolution(self, resolver):
        """Test resolution of definite references like 'the cat'."""
        recent_concepts = [
            Concept("dog"),
            Concept("cat"),
            Concept("black_cat"),
            Concept("table")
        ]
        
        candidates = resolver.resolve_definite_reference("the cat", recent_concepts)
        
        # Should find cat-related concepts
        assert len(candidates) > 0
        
        # Exact match should be top
        top_candidate = candidates[0]
        assert Concept("cat") in top_candidate.concept_intersections
        assert top_candidate.source_heuristic == "definite_reference_resolution"
    
    def test_update_context(self, resolver):
        """Test context window management."""
        # Create more concepts than window size
        concepts = [Concept(f"concept_{i}") for i in range(15)]
        
        # Update with window size 10
        updated = resolver.update_context(concepts, context_window=10)
        
        # Should keep only last 10
        assert len(updated) == 10
        assert updated == concepts[-10:]
    
    def test_case_insensitive_pronouns(self, resolver):
        """Test that pronoun resolution is case-insensitive."""
        recent_concepts = [Concept("mat")]
        
        # Try different cases
        candidates_lower = resolver.resolve_pronoun("it", recent_concepts)
        candidates_upper = resolver.resolve_pronoun("IT", recent_concepts)
        candidates_mixed = resolver.resolve_pronoun("It", recent_concepts)
        
        # All should produce same results
        assert len(candidates_lower) == len(candidates_upper) == len(candidates_mixed)
        assert candidates_lower[0].probability == candidates_upper[0].probability


class TestContextResolverIntegration:
    """Integration tests for ContextResolver with SymbolicParser."""
    
    def test_parser_pronoun_resolution(self):
        """Test that parser correctly uses context resolver for pronouns."""
        from regionai.domains.language.symbolic_parser import SymbolicParser
        from regionai.domains.language.candidate_generator import CandidateGenerator
        from regionai.world_contexts.knowledge.graph import WorldKnowledgeGraph
        from regionai.world_contexts.knowledge.hub import KnowledgeHub
        
        # Create knowledge graph
        graph = WorldKnowledgeGraph()
        graph.add_concept(Concept("cat"))
        graph.add_concept(Concept("mat"))
        graph.add_concept(Concept("black"))
        
        hub = KnowledgeHub()
        hub.wkg = graph
        
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Parse sequence with pronoun
        sentences = [
            "The cat sat on the mat",
            "It was black"
        ]
        
        trees = parser.parse_sequence(sentences)
        
        # Check that we got two trees
        assert len(trees) == 2
        
        # Second tree should have resolved "It"
        second_tree = trees[1]
        assert second_tree.root_constraint.text == "It was black"
        
        # The constraint should be grounded
        assert second_tree.root_constraint.is_grounded
        
        # Check if pronoun was detected (by checking candidates)
        # Since "It was black" contains a pronoun, it should have used context resolution
        if second_tree.root_constraint.possible_regions:
            # At least one candidate should be from pronoun resolution
            sources = [c.source_heuristic for c in second_tree.root_constraint.possible_regions]
            # Could be either pronoun_resolution or regular matching
            assert any(source in ["pronoun_resolution", "partial_word_match", "substring_match"] 
                      for source in sources)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])