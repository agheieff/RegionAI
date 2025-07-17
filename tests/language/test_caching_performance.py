"""
Unit tests for caching functionality in the SymbolicParser.

Tests the LRU cache implementation and its impact on performance.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock
from regionai.domains.language.symbolic_parser import SymbolicParser
from regionai.domains.language.candidate_generator import CandidateGenerator
from regionai.domains.language.symbolic import RegionCandidate
from regionai.knowledge.graph import Concept


class TestSymbolicParserCaching:
    """Test suite for caching functionality."""
    
    @pytest.fixture
    def mock_generator(self):
        """Create a mock candidate generator."""
        generator = Mock(spec=CandidateGenerator)
        
        # Track call count
        call_count = {"count": 0}
        
        def mock_generate(phrase):
            call_count["count"] += 1
            return [RegionCandidate({Concept("Test")}, 0.9, "test")]
        
        def mock_generate_context(phrase, context):
            call_count["count"] += 1
            return [RegionCandidate({Concept("Test")}, 0.9, "test")]
        
        generator.generate_candidates_for_phrase.side_effect = mock_generate
        generator.generate_candidates_with_context.side_effect = mock_generate_context
        generator.call_count = call_count
        
        # Add mock knowledge_graph attribute
        mock_knowledge_graph = Mock()
        mock_knowledge_graph.learn_mapping = Mock()
        generator.knowledge_graph = mock_knowledge_graph
        
        return generator
    
    @pytest.fixture
    def parser(self, mock_generator):
        """Create a parser with mock generator."""
        return SymbolicParser(mock_generator)
    
    def test_cache_hit_on_repeated_sentence(self, parser, mock_generator):
        """Test that parsing the same sentence twice works correctly."""
        sentence = "The cat sat on the mat"
        
        # Clear cache, context, and call count
        parser.clear_cache()
        parser.clear_context()
        mock_generator.call_count["count"] = 0
        
        # Parse once
        tree1 = parser.parse_sentence(sentence)
        initial_calls = mock_generator.call_count["count"]
        
        # Clear context again to reset to same state
        parser.clear_context()
        
        # Parse again - should use cache due to same context
        tree2 = parser.parse_sentence(sentence)
        second_calls = mock_generator.call_count["count"]
        
        # Check cache info
        cache_info = parser.get_cache_info()
        
        # Should have cache hit if context is same
        assert cache_info.hits >= 1 or second_calls == initial_calls
        
        # Trees should be identical
        assert tree1.root_constraint.text == tree2.root_constraint.text
        
        # Check cache stats
        info = parser.get_cache_info()
        assert info.hits == 1
        assert info.misses == 1
    
    def test_cache_miss_on_different_sentence(self, parser):
        """Test that different sentences cause cache misses."""
        parser.clear_cache()
        
        # Parse different sentences
        parser.parse_sentence("The cat sat")
        parser.parse_sentence("The dog ran")
        
        info = parser.get_cache_info()
        assert info.hits == 0
        assert info.misses == 2
    
    def test_context_affects_cache_key(self, parser):
        """Test that context changes affect cache lookup."""
        sentence = "It was comfortable"
        parser.clear_cache()
        
        # Parse with empty context
        parser.parsing_context = set()
        parser.parse_sentence(sentence)
        
        # Parse with different context
        parser.parsing_context = {Concept("Cat")}
        parser.parse_sentence(sentence)
        
        # Should be two misses (different context)
        info = parser.get_cache_info()
        assert info.hits == 0
        assert info.misses == 2
    
    def test_context_fingerprint_stability(self, parser):
        """Test that context fingerprint is order-independent."""
        sentence = "Test sentence"
        parser.clear_cache()
        
        # Set context with specific order
        parser.parsing_context = {Concept("Cat"), Concept("Dog"), Concept("Mat")}
        parser.parse_sentence(sentence)
        
        # Rearrange context (same concepts, different order)
        parser.parsing_context = {Concept("Dog"), Concept("Mat"), Concept("Cat")}
        parser.parse_sentence(sentence)
        
        # Should get cache hit (fingerprint should be stable)
        info = parser.get_cache_info()
        assert info.hits == 1
        assert info.misses == 1
    
    def test_clear_cache(self, parser):
        """Test cache clearing functionality."""
        # Parse some sentences
        parser.parse_sentence("Test 1")
        parser.parse_sentence("Test 2")
        parser.parse_sentence("Test 1")  # Should hit
        
        info_before = parser.get_cache_info()
        assert info_before.currsize > 0
        
        # Clear cache
        parser.clear_cache()
        
        info_after = parser.get_cache_info()
        assert info_after.currsize == 0
        assert info_after.hits == 0
        assert info_after.misses == 0
    
    def test_disable_caching(self, parser, mock_generator):
        """Test that disabling cache works correctly."""
        sentence = "The cat sat"
        
        # Disable caching
        parser.disable_caching()
        parser.clear_context()
        mock_generator.call_count["count"] = 0
        
        # Parse twice
        parser.parse_sentence(sentence)
        first_calls = mock_generator.call_count["count"]
        
        parser.parse_sentence(sentence)
        second_calls = mock_generator.call_count["count"]
        
        # Should make calls both times (no caching)
        assert second_calls == first_calls * 2
        
        # Cache info should show no activity
        info = parser.get_cache_info()
        assert info.hits == 0
        assert info.misses == 0
    
    def test_enable_caching_custom_size(self, parser):
        """Test enabling cache with custom size."""
        # Enable with small cache
        parser.enable_caching(maxsize=2)
        parser.clear_cache()
        
        # Parse 3 different sentences
        parser.parse_sentence("One")
        parser.parse_sentence("Two")
        parser.parse_sentence("Three")
        
        # Cache should be at max size
        info = parser.get_cache_info()
        assert info.currsize == 2
        assert info.maxsize == 2
    
    def test_cache_with_parse_sequence(self, parser):
        """Test that parse_sequence benefits from caching."""
        sentences = [
            "The cat sat",
            "The dog ran",
            "The cat sat",  # Repeat
            "The dog ran"   # Repeat
        ]
        
        parser.clear_cache()
        parser.clear_context()
        parser.parse_sequence(sentences)
        
        # Should have some hits (context evolution means not all repeats will hit)
        info = parser.get_cache_info()
        assert info.hits >= 1  # At least some caching should occur
        assert info.misses >= 2  # At least some misses due to context changes
    
    def test_performance_improvement(self, parser):
        """Test that caching provides measurable performance improvement."""
        import time
        
        # Create a corpus with repetition
        corpus = ["Sentence A", "Sentence B", "Sentence C"] * 20
        
        # Time with caching
        parser.clear_cache()
        parser.enable_caching()
        
        start = time.time()
        for sentence in corpus:
            parser.parse_sentence(sentence)
        time_cached = time.time() - start
        
        cache_info = parser.get_cache_info()
        hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses)
        
        # Time without caching
        parser.disable_caching()
        parser.clear_context()
        
        start = time.time()
        for sentence in corpus:
            parser.parse_sentence(sentence)
        time_uncached = time.time() - start
        
        # Caching should be faster
        assert time_cached < time_uncached
        
        # Hit rate should be high for repeated corpus
        assert hit_rate > 0.7  # 70% hit rate target


if __name__ == "__main__":
    pytest.main([__file__, "-v"])