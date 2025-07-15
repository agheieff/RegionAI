"""
Candidate Generator for the Symbolic Language Engine.

This module implements the candidate generation stage of the natural language
understanding pipeline. It takes text phrases and generates potential meanings
(RegionCandidate objects) by searching the WorldKnowledgeGraph for matching concepts.

This is the gateway through which language enters our system, converting raw text
into structured, probabilistic representations suitable for reasoning.
"""

from typing import List, Optional, Set
from .symbolic import RegionCandidate
from tier1.knowledge.infrastructure.world_graph import Concept
from tier1.knowledge.infrastructure.hub_v1 import KnowledgeHub


class CandidateGenerator:
    """
    Generates candidate interpretations for text phrases.
    
    The CandidateGenerator searches the WorldKnowledgeGraph to find concepts
    that might correspond to a given text phrase. It implements various
    matching strategies (exact match, substring match, etc.) and assigns
    probabilities based on match quality.
    
    This is the first stage in our beam search pipeline, producing the initial
    set of candidates that will be refined through subsequent processing.
    """
    
    def __init__(self, knowledge_hub: KnowledgeHub):
        """
        Initialize the generator with a knowledge source.
        
        Args:
            knowledge_hub: The KnowledgeHub containing the world knowledge graph
                          to search for concept matches
        """
        self.knowledge_hub = knowledge_hub
        self.knowledge_graph = knowledge_hub.wkg
        
        # Probability scores for different match types
        self.EXACT_MATCH_PROBABILITY = 0.9
        self.SUBSTRING_MATCH_PROBABILITY = 0.6
        self.PARTIAL_WORD_MATCH_PROBABILITY = 0.4
    
    def generate_candidates_for_phrase(self, phrase: str) -> List[RegionCandidate]:
        """
        Generate candidate interpretations for a text phrase.
        
        This method searches the knowledge graph for concepts that match the
        given phrase using various strategies:
        1. Exact match (highest probability)
        2. Substring match (medium probability)
        3. Partial word match (lower probability)
        
        Args:
            phrase: The text phrase to find interpretations for
            
        Returns:
            List of RegionCandidate objects representing possible meanings,
            sorted by probability (highest first)
        """
        candidates = []
        
        # Normalize the phrase for matching
        normalized_phrase = phrase.lower().strip()
        
        # Get all concepts from the knowledge graph
        all_concepts = set(self.knowledge_graph.get_concepts())
        
        # Special handling for quantified expressions
        if any(q in normalized_phrase for q in ["every", "all", "each", "some", "many"]):
            # Try to find quantified concepts
            words = normalized_phrase.split()
            for i, word in enumerate(words):
                if word in ["every", "all", "each"] and i + 1 < len(words):
                    # Create quantified concept name
                    quantified = f"{word.capitalize()}_{words[i+1].capitalize()}"
                    quantified_concept = Concept(quantified)
                    if quantified_concept in all_concepts:
                        candidates.append(RegionCandidate(
                            concept_intersections={quantified_concept},
                            probability=0.9,
                            source_heuristic="quantifier_match"
                        ))
        
        for concept in all_concepts:
            # Normalize concept name for comparison
            concept_name_lower = concept.lower()
            
            # Strategy 1: Exact match
            if concept_name_lower == normalized_phrase:
                candidate = RegionCandidate(
                    concept_intersections={concept},
                    probability=self.EXACT_MATCH_PROBABILITY,
                    source_heuristic="exact_match"
                )
                candidates.append(candidate)
            
            # Strategy 2: Substring match (concept contains phrase)
            elif normalized_phrase in concept_name_lower:
                candidate = RegionCandidate(
                    concept_intersections={concept},
                    probability=self.SUBSTRING_MATCH_PROBABILITY,
                    source_heuristic="substring_match"
                )
                candidates.append(candidate)
            
            # Strategy 3: Partial word match (any word in phrase matches)
            else:
                phrase_words = set(normalized_phrase.split())
                # Handle both underscore and space separated concepts
                concept_words = set(concept_name_lower.replace('_', ' ').split())
                
                # If any word from the phrase appears in the concept
                if phrase_words.intersection(concept_words):
                    candidate = RegionCandidate(
                        concept_intersections={concept},
                        probability=self.PARTIAL_WORD_MATCH_PROBABILITY,
                        source_heuristic="partial_word_match"
                    )
                    candidates.append(candidate)
        
        # Find related concepts through relationships
        candidates.extend(self._find_related_concepts(normalized_phrase, all_concepts))
        
        # Remove duplicates (same concept from different strategies)
        unique_candidates = self._deduplicate_candidates(candidates)
        
        # Sort by probability (highest first)
        unique_candidates.sort(key=lambda c: c.probability, reverse=True)
        
        return unique_candidates
    
    def _find_related_concepts(self, phrase: str, all_concepts: Set[Concept]) -> List[RegionCandidate]:
        """
        Find concepts related to the phrase through graph relationships.
        
        This method looks for concepts that might be connected to the phrase
        through relationships like IS_A, PART_OF, etc.
        
        Args:
            phrase: The normalized phrase to search for
            all_concepts: Set of all concepts in the graph
            
        Returns:
            List of RegionCandidate objects for related concepts
        """
        related_candidates = []
        
        # For now, we'll implement a simple version
        # In the future, this could traverse relationships more deeply
        
        for concept in all_concepts:
            concept_lower = concept.lower()
            
            # Check if the phrase might be a property or attribute
            if phrase in concept_lower.split('_'):
                # Get concepts this one is related to
                relations = self.knowledge_graph.get_relations(concept)
                
                for source, target, relation in relations:
                    if relation == "IS_A" or relation == "TYPE_OF":
                        # For outgoing relations, concept is the source
                        if source == concept:
                            candidate = RegionCandidate(
                                concept_intersections={concept, target},
                                probability=0.5,  # Medium confidence for related concepts
                                source_heuristic="relationship_inference"
                            )
                            related_candidates.append(candidate)
        
        return related_candidates
    
    def _deduplicate_candidates(self, candidates: List[RegionCandidate]) -> List[RegionCandidate]:
        """
        Remove duplicate candidates, keeping the one with highest probability.
        
        Two candidates are considered duplicates if they have the same
        concept_intersections set.
        
        Args:
            candidates: List of potentially duplicate candidates
            
        Returns:
            List of unique candidates
        """
        # Use a dict to track best candidate for each concept set
        best_candidates = {}
        
        for candidate in candidates:
            # Create a hashable key from the concept set
            concepts_key = frozenset(candidate.concept_intersections)
            
            # Keep the candidate with highest probability
            if concepts_key not in best_candidates:
                best_candidates[concepts_key] = candidate
            elif candidate.probability > best_candidates[concepts_key].probability:
                best_candidates[concepts_key] = candidate
        
        return list(best_candidates.values())
    
    def generate_candidates_with_context(
        self, 
        phrase: str, 
        context: Optional[str] = None
    ) -> List[RegionCandidate]:
        """
        Generate candidates considering additional context.
        
        This enhanced method takes into account surrounding context to
        improve candidate generation accuracy.
        
        Args:
            phrase: The text phrase to interpret
            context: Optional context string (e.g., the full sentence)
            
        Returns:
            List of RegionCandidate objects with context-adjusted probabilities
        """
        # Get base candidates
        candidates = self.generate_candidates_for_phrase(phrase)
        
        if not context:
            return candidates
        
        # Adjust probabilities based on context
        # This is a placeholder for more sophisticated context analysis
        context_lower = context.lower()
        
        for candidate in candidates:
            # Boost candidates whose concepts appear elsewhere in context
            for concept in candidate.concept_intersections:
                if concept.lower() in context_lower:
                    # Boost probability by 10%, capped at 0.95
                    candidate.probability = min(0.95, candidate.probability * 1.1)
        
        # Re-sort after adjustment
        candidates.sort(key=lambda c: c.probability, reverse=True)
        
        return candidates