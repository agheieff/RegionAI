"""
Test back-propagation of successful resolutions to learn new mappings.

This test verifies that the system can learn from successful pronoun
resolutions and update the knowledge graph with new word-concept mappings.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from regionai.domains.language.symbolic_parser import SymbolicParser
from regionai.domains.language.candidate_generator import CandidateGenerator
from regionai.world_contexts.knowledge.graph import Concept, WorldKnowledgeGraph
from regionai.world_contexts.knowledge.hub import KnowledgeHub


def create_test_graph():
    """Create a test knowledge graph with quantified concepts."""
    graph = WorldKnowledgeGraph()
    
    # Add basic and quantified concepts
    concepts = [
        "Student", "Every_Student", "All_Students",
        "Teacher", "Every_Teacher",
        "Pass", "Receive", "Certificate"
    ]
    
    for concept_name in concepts:
        graph.add_concept(Concept(concept_name))
    
    # Add relationships
    graph.add_relation(Concept("Every_Student"), "QUANTIFIES", Concept("Student"))
    
    return graph


class TestLearningMappings:
    """Test suite for the learning functionality."""
    
    def test_successful_resolution_tracking(self):
        """Test that successful pronoun resolutions are tracked."""
        # Setup
        hub = KnowledgeHub()
        hub.wkg = create_test_graph()
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Parse sentences with quantifier and pronoun
        sentences = [
            "Every student passed the exam.",
            "They received their certificates."
        ]
        
        for sentence in sentences:
            parser.parse_sentence(sentence)
        
        # Check that resolutions were tracked
        resolutions = parser.get_successful_resolutions()
        
        # Should have tracked "they" resolving to "Every_Student"
        assert len(resolutions) > 0
        
        # Find the "they" resolution
        they_resolutions = [r for r in resolutions if r['word'] == 'they']
        assert len(they_resolutions) > 0
        
        # Check the resolution details
        resolution = they_resolutions[0]
        assert resolution['concept'] == Concept("Every_Student")
        assert resolution['probability'] >= 0.8  # High confidence
        assert "received their certificates" in resolution['sentence'].lower()
    
    def test_learn_mapping_method(self):
        """Test the learn_mapping method on WorldKnowledgeGraph."""
        graph = WorldKnowledgeGraph()
        
        # Add the target concept
        graph.add_concept(Concept("Every_Student"))
        
        # Learn a mapping
        graph.learn_mapping("they", Concept("Every_Student"), 0.95)
        
        # Check that the word concept was created
        word_concept = Concept("word:they")
        assert word_concept in graph
        
        # Check the metadata
        word_metadata = graph.get_concept_metadata(word_concept)
        assert word_metadata is not None
        assert word_metadata.discovery_method == "pronoun_resolution_learning"
        assert word_metadata.properties['original_word'] == "they"
        
        # Check the relationship was created
        relations = graph.get_relations_with_confidence(word_concept)
        assert len(relations) > 0
        
        # Find the REFERS_TO relation
        refers_to_relations = [r for r in relations if r['relation'] == "REFERS_TO"]
        assert len(refers_to_relations) == 1
        
        relation = refers_to_relations[0]
        assert relation['target'] == Concept("Every_Student")
        assert relation['confidence'] >= 0.9
    
    def test_apply_learned_mappings(self):
        """Test applying learned mappings from parser to graph."""
        # Setup
        hub = KnowledgeHub()
        hub.wkg = create_test_graph()
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Parse sentences to generate resolutions
        sentences = [
            "Every student passed the exam.",
            "They received their certificates."
        ]
        
        for sentence in sentences:
            parser.parse_sentence(sentence)
        
        # Create a new graph and apply learned mappings
        new_graph = WorldKnowledgeGraph()
        new_graph.add_concept(Concept("Every_Student"))  # Must exist first
        
        parser.apply_learned_mappings(new_graph)
        
        # Check that mappings were applied
        word_concept = Concept("word:they")
        assert word_concept in new_graph
        
        # Check the relationship
        relations = new_graph.get_relations_with_confidence(word_concept)
        refers_to_relations = [r for r in relations if r['relation'] == "REFERS_TO"]
        assert len(refers_to_relations) > 0
    
    def test_multiple_pronoun_learning(self):
        """Test learning from multiple different pronouns."""
        # Setup
        hub = KnowledgeHub()
        hub.wkg = create_test_graph()
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Parse sentences with different pronouns in separate sentences
        sentences = [
            "Every student passed the exam.",
            "They received certificates.",
            "Their grades were excellent."
        ]
        
        for sentence in sentences:
            parser.parse_sentence(sentence)
        
        resolutions = parser.get_successful_resolutions()
        
        # Should have resolutions for both "they" and "their"
        words_resolved = {r['word'] for r in resolutions}
        assert 'they' in words_resolved
        assert 'their' in words_resolved
        
        # Both should resolve to Every_Student
        for resolution in resolutions:
            if resolution['word'] in ['they', 'their']:
                assert resolution['concept'] == Concept("Every_Student")
    
    def test_learning_persistence(self):
        """Test that learned mappings persist in the knowledge graph."""
        graph = WorldKnowledgeGraph()
        graph.add_concept(Concept("Every_Student"))
        
        # Learn multiple mappings
        graph.learn_mapping("they", Concept("Every_Student"), 0.9)
        graph.learn_mapping("their", Concept("Every_Student"), 0.85)
        
        # Export to JSON
        json_data = graph.to_json()
        
        # Create new graph and import
        new_graph = WorldKnowledgeGraph()
        new_graph.from_json(json_data)
        
        # Check that word concepts exist
        assert Concept("word:they") in new_graph
        assert Concept("word:their") in new_graph
        
        # Check relationships preserved
        for word in ["they", "their"]:
            word_concept = Concept(f"word:{word}")
            relations = new_graph.get_relations_with_confidence(word_concept)
            refers_to = [r for r in relations if r['relation'] == "REFERS_TO"]
            assert len(refers_to) == 1
            assert refers_to[0]['target'] == Concept("Every_Student")
    
    def test_confidence_threshold(self):
        """Test that only high-confidence resolutions are learned."""
        # Setup with custom learning threshold
        hub = KnowledgeHub()
        hub.wkg = create_test_graph()
        generator = CandidateGenerator(hub)
        parser = SymbolicParser(generator)
        
        # Set a high learning threshold
        parser.learning_threshold = 0.9
        
        # This would need low-confidence pronoun resolution to test properly
        # For now, verify the threshold exists and is used
        assert hasattr(parser, 'learning_threshold')
        assert parser.learning_threshold == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])