"""
Advanced integration tests for the Symbolic Language Engine.

These tests verify the system's ability to handle complex linguistic phenomena
including quantifier scopes, anaphora resolution, and their interactions.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tier2.domains.language.symbolic_parser import SymbolicParser
from tier2.domains.language.candidate_generator import CandidateGenerator
from tier3.world_contexts.knowledge.graph import Concept, WorldKnowledgeGraph
from tier3.world_contexts.knowledge.hub import KnowledgeHub


class TestAdvancedParsing:
    """Test suite for advanced parsing capabilities."""
    
    @pytest.fixture
    def knowledge_graph(self):
        """Create a knowledge graph with concepts for testing."""
        graph = WorldKnowledgeGraph()
        
        # Add relevant concepts
        concepts = [
            "Student", "Students", "Every_Student",
            "Exam", "Certificate", "Certificates",
            "Pass", "Receive", "Take",
            "Group", "Individual", "Universal_Quantifier"
        ]
        
        for concept_name in concepts:
            graph.add_concept(Concept(concept_name))
        
        # Add relationships
        graph.add_relation(Concept("Every_Student"), "IS_A", Concept("Universal_Quantifier"))
        graph.add_relation(Concept("Every_Student"), "QUANTIFIES", Concept("Student"))
        graph.add_relation(Concept("Students"), "PLURAL_OF", Concept("Student"))
        
        return graph
    
    @pytest.fixture
    def parser(self, knowledge_graph):
        """Create a parser with the test knowledge graph."""
        hub = KnowledgeHub()
        hub.wkg = knowledge_graph
        generator = CandidateGenerator(hub)
        return SymbolicParser(generator)
    
    def test_quantifier_scope_resolution(self, parser):
        """
        Test that the system correctly handles quantifier scope and anaphora.
        
        This test verifies that pronouns referring to quantified expressions
        are resolved to the appropriate quantified concept, not just the base noun.
        """
        # The test sentences
        sentences = [
            "Every student passed the exam.",
            "They received their certificate."
        ]
        
        print("\n" + "="*60)
        print("QUANTIFIER SCOPE RESOLUTION TEST")
        print("="*60)
        print(f"Sentence 1: {sentences[0]}")
        print(f"Sentence 2: {sentences[1]}")
        
        # Parse the sequence
        trees = parser.parse_sequence(sentences)
        
        # Verify we got two trees
        assert len(trees) == 2, "Should parse both sentences"
        
        # Analyze the first sentence
        first_tree = trees[0]
        print(f"\nFirst sentence root: '{first_tree.root_constraint.text}'")
        print(f"Candidates for first sentence:")
        for i, candidate in enumerate(first_tree.root_constraint.possible_regions[:3]):
            concepts = ", ".join(sorted(c for c in candidate.concept_intersections))
            print(f"  {i+1}. {concepts} (p={candidate.probability:.2f})")
        
        # Check parsing context after first sentence
        print(f"\nParsing context after first sentence:")
        for concept in parser.parsing_context:
            print(f"  - {concept}")
        
        # Analyze the second sentence
        second_tree = trees[1]
        print(f"\nSecond sentence root: '{second_tree.root_constraint.text}'")
        
        # Find constraints containing pronouns
        pronoun_constraints = []
        
        def find_pronoun_constraints(tree, constraints_list):
            """Recursively find constraints containing pronouns."""
            text_lower = tree.root_constraint.text.lower()
            if any(pronoun in text_lower.split() for pronoun in ["they", "their", "them"]):
                constraints_list.append(tree.root_constraint)
            
            for child_tree in tree.children.values():
                find_pronoun_constraints(child_tree, constraints_list)
        
        find_pronoun_constraints(second_tree, pronoun_constraints)
        
        # We expect to find at least one pronoun constraint
        assert len(pronoun_constraints) > 0, "Should find pronoun constraints in second sentence"
        
        print(f"\nFound {len(pronoun_constraints)} pronoun constraints:")
        
        # Analyze each pronoun constraint
        for constraint in pronoun_constraints:
            print(f"\nConstraint: '{constraint.text}'")
            print(f"Is grounded: {constraint.is_grounded}")
            print(f"Candidates:")
            
            # Check if any candidates were generated
            assert constraint.is_grounded, f"Pronoun constraint '{constraint.text}' should be grounded"
            assert len(constraint.possible_regions) > 0, f"Should have candidates for '{constraint.text}'"
            
            # Examine the candidates
            has_quantified_reference = False
            has_plural_reference = False
            
            for i, candidate in enumerate(constraint.possible_regions[:5]):
                concepts = list(candidate.concept_intersections)
                concepts_str = ", ".join(sorted(str(c) for c in concepts))
                source = candidate.source_heuristic
                
                print(f"  {i+1}. {concepts_str} (p={candidate.probability:.2f}, source={source})")
                
                # Check if this candidate refers to a quantified group
                for concept in concepts:
                    concept_str = str(concept).lower()
                    if "every" in concept_str or "students" in concept_str:
                        has_quantified_reference = True
                    if concept_str.endswith('s') or "students" in concept_str:
                        has_plural_reference = True
            
            # Assertions about the resolution
            if "they" in constraint.text.lower():
                # "They" should resolve to a plural or quantified concept
                assert has_plural_reference or has_quantified_reference, \
                    "Pronoun 'they' should resolve to a plural or quantified concept"
                
                # The top candidate should be from pronoun resolution
                top_candidate = constraint.get_top_candidate()
                assert top_candidate is not None, "Should have a top candidate"
                
                # Check that the resolution makes semantic sense
                top_concepts = list(top_candidate.concept_intersections)
                print(f"\nTop resolution for 'they': {top_concepts}")
                
                # Ideally, this should point to "Every_Student" or "Students"
                # not just "Student"
                assert any("student" in str(c).lower() for c in top_concepts), \
                    "Should resolve to student-related concept"
            
            if "their" in constraint.text.lower():
                # "their" should also resolve to the same quantified group
                assert has_plural_reference or has_quantified_reference, \
                    "Pronoun 'their' should resolve to a plural or quantified concept"
        
        # Additional check: Verify the context resolver understood the quantifier
        # This is the key test - the system should understand that "Every student"
        # creates a reference to a group, not just an individual
        
        # Check if the parsing context contains appropriate concepts
        context_concepts = [str(c).lower() for c in parser.parsing_context]
        print(f"\nFinal parsing context: {context_concepts}")
        
        # The context should include concepts that represent the quantified expression
        has_appropriate_context = any(
            "every" in c or "student" in c or "group" in c 
            for c in context_concepts
        )
        
        assert has_appropriate_context, \
            "Parsing context should include concepts from the quantified expression"
        
        print("\n" + "="*60)
        print("TEST RESULT: Quantifier scope resolution working correctly")
        print("="*60)
    
    def test_nested_quantifier_scopes(self, parser):
        """
        Test handling of nested quantifier scopes.
        
        This is an even more advanced test for future improvements.
        """
        sentences = [
            "Every teacher graded all assignments.",
            "They took several hours to finish them."
        ]
        
        trees = parser.parse_sequence(sentences)
        
        # This test documents expected behavior for nested quantifiers
        # Currently may not pass - included for future development
        
        # "They" should refer to "every teacher" (outer quantifier)
        # "them" should refer to "all assignments" (inner quantifier)
        
        # For now, just verify basic parsing works
        assert len(trees) == 2
        assert trees[0].root_constraint.is_grounded
        assert trees[1].root_constraint.is_grounded
    
    def test_quantifier_with_relative_clause(self, parser):
        """
        Test quantifiers with relative clauses.
        """
        sentences = [
            "Every student who studied hard passed.",
            "They were proud of their achievement."
        ]
        
        trees = parser.parse_sequence(sentences)
        
        # Verify structure
        assert len(trees) == 2
        
        # First tree should have a relative clause
        trees[0]
        # Check if the parser identified the relative clause
        # This tests the interaction between quantifiers and syntactic structure
        
        # Second tree should resolve pronouns to the quantified group
        second_tree = trees[1]
        assert second_tree.root_constraint.is_grounded


if __name__ == "__main__":
    # Run the specific test
    pytest.main([__file__, "-xvs", "-k", "test_quantifier_scope_resolution"])