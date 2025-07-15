"""
Contextual Resolver for Anaphora Resolution.

This module implements context-aware resolution of pronouns and other
anaphoric expressions. It maintains a memory of recently mentioned concepts
and uses simple heuristics to resolve references like "it", "they", "their"
to their most likely antecedents.

This is a crucial component for understanding connected discourse, allowing
the system to track entities across sentence boundaries.
"""

from typing import List
from .symbolic import RegionCandidate
from tier1.knowledge.infrastructure.world_graph import Concept


class ContextResolver:
    """
    Resolves pronouns and other context-dependent expressions.
    
    The ContextResolver maintains a memory of recently mentioned concepts
    and provides methods to resolve anaphoric references. This V1 implementation
    uses simple recency and compatibility heuristics.
    """
    
    # Pronoun categories for compatibility checking
    SINGULAR_PRONOUNS = {"it", "its", "itself"}
    PLURAL_PRONOUNS = {"they", "them", "their", "theirs", "themselves"}
    MALE_PRONOUNS = {"he", "him", "his", "himself"}
    FEMALE_PRONOUNS = {"she", "her", "hers", "herself"}
    
    # Animate vs inanimate hints (can be expanded)
    ANIMATE_HINTS = {"cat", "dog", "person", "man", "woman", "child", "animal", "student", "teacher"}
    INANIMATE_HINTS = {"mat", "chair", "table", "house", "car", "book", "computer"}
    
    # Quantifier patterns that create plural references
    UNIVERSAL_QUANTIFIERS = {"every", "all", "each"}
    EXISTENTIAL_QUANTIFIERS = {"some", "many", "several", "few"}
    
    def __init__(self):
        """Initialize the context resolver."""
        # For V1, we don't need any special initialization
    
    def resolve_pronoun(
        self, 
        pronoun: str, 
        recent_concepts: List[Concept]
    ) -> List[RegionCandidate]:
        """
        Resolve a pronoun to its most likely antecedent.
        
        This implementation uses heuristics:
        1. Recency - more recent mentions are preferred
        2. Animacy - match animate pronouns with animate concepts
        3. Number agreement - singular/plural matching
        4. Quantifier awareness - "every X" creates plural reference
        
        Args:
            pronoun: The pronoun to resolve (e.g., "it", "they")
            recent_concepts: List of recently mentioned concepts, 
                           ordered from most to least recent
                           
        Returns:
            List of RegionCandidate objects representing possible antecedents,
            ordered by likelihood (highest probability first)
        """
        pronoun_lower = pronoun.lower()
        candidates = []
        
        # Score each recent concept
        for i, concept in enumerate(recent_concepts):
            # Calculate compatibility score
            compatibility = self._calculate_compatibility(pronoun_lower, concept)
            
            if compatibility > 0:
                # Recency bonus: more recent = higher score
                # Decrease by 0.1 for each position back
                recency_score = max(0.1, 1.0 - (i * 0.1))
                
                # Combined score
                final_score = compatibility * recency_score
                
                # Create candidate
                candidate = RegionCandidate(
                    concept_intersections={concept},
                    probability=min(0.95, final_score),  # Cap at 0.95
                    source_heuristic="pronoun_resolution"
                )
                candidates.append(candidate)
        
        # Sort by probability
        candidates.sort(key=lambda c: c.probability, reverse=True)
        
        # Return top candidates (beam search compatible)
        return candidates
    
    def _calculate_compatibility(self, pronoun: str, concept: Concept) -> float:
        """
        Calculate compatibility between a pronoun and a concept.
        
        Args:
            pronoun: The pronoun (lowercase)
            concept: The potential antecedent
            
        Returns:
            Compatibility score between 0.0 and 1.0
        """
        concept_lower = concept.lower()
        
        # Check basic compatibility
        if pronoun in self.SINGULAR_PRONOUNS:
            # "it" generally refers to inanimate or non-human animate things
            if self._is_likely_inanimate(concept_lower):
                return 0.9
            elif self._is_likely_animate_nonhuman(concept_lower):
                return 0.8
            else:
                return 0.3  # Low score for human concepts
                
        elif pronoun in self.PLURAL_PRONOUNS:
            # Check for quantified expressions first
            if self._is_quantified_expression(concept_lower):
                return 0.95  # Very high score for quantified expressions
            # Simple heuristic: check if concept seems plural
            elif concept_lower.endswith('s') and not concept_lower.endswith('ss'):
                return 0.8
            else:
                return 0.2  # Low score for singular concepts
                
        elif pronoun in self.MALE_PRONOUNS:
            # Check for male indicators
            if any(hint in concept_lower for hint in ["man", "boy", "male", "he"]):
                return 0.9
            elif self._is_likely_animate_nonhuman(concept_lower):
                return 0.5  # Some animals can be referred to as he
            else:
                return 0.1
                
        elif pronoun in self.FEMALE_PRONOUNS:
            # Check for female indicators
            if any(hint in concept_lower for hint in ["woman", "girl", "female", "she"]):
                return 0.9
            elif self._is_likely_animate_nonhuman(concept_lower):
                return 0.5  # Some animals can be referred to as she
            else:
                return 0.1
        
        # Default: unknown pronoun
        return 0.5
    
    def _is_quantified_expression(self, concept_text: str) -> bool:
        """
        Check if a concept represents a quantified expression.
        
        Args:
            concept_text: The concept text to check
            
        Returns:
            True if this appears to be a quantified expression
        """
        # Check for universal quantifiers
        for quantifier in self.UNIVERSAL_QUANTIFIERS:
            if quantifier in concept_text:
                return True
        
        # Check for existential quantifiers
        for quantifier in self.EXISTENTIAL_QUANTIFIERS:
            if quantifier in concept_text:
                return True
        
        # Check for explicit quantifier markers
        if "_quantifier" in concept_text or "quantified" in concept_text:
            return True
        
        return False
    
    def _is_likely_inanimate(self, concept_text: str) -> bool:
        """Check if a concept is likely inanimate."""
        # Check against known inanimate hints
        return any(hint in concept_text for hint in self.INANIMATE_HINTS)
    
    def _is_likely_animate_nonhuman(self, concept_text: str) -> bool:
        """Check if a concept is likely an animate non-human."""
        # Simple heuristic: contains animal-related words
        return any(hint in concept_text for hint in ["cat", "dog", "animal", "pet", "bird"])
    
    def resolve_definite_reference(
        self, 
        noun_phrase: str, 
        recent_concepts: List[Concept]
    ) -> List[RegionCandidate]:
        """
        Resolve definite references like "the cat" to previously mentioned cats.
        
        This handles cases where the same entity is referred to again with
        a definite article, indicating it's the same one mentioned before.
        
        Args:
            noun_phrase: The definite noun phrase (e.g., "the cat")
            recent_concepts: List of recently mentioned concepts
            
        Returns:
            List of RegionCandidate objects for previously mentioned instances
        """
        # Extract the core noun (simple approach for V1)
        core_noun = noun_phrase.lower().replace("the ", "").strip()
        
        candidates = []
        
        for i, concept in enumerate(recent_concepts):
            concept_lower = concept.lower()
            
            # Check if the concept matches the core noun
            if core_noun in concept_lower or concept_lower in core_noun:
                # High confidence for exact matches
                if core_noun == concept_lower:
                    score = 0.95
                else:
                    score = 0.7
                
                # Apply recency bonus
                recency_factor = max(0.5, 1.0 - (i * 0.1))
                final_score = score * recency_factor
                
                candidate = RegionCandidate(
                    concept_intersections={concept},
                    probability=final_score,
                    source_heuristic="definite_reference_resolution"
                )
                candidates.append(candidate)
        
        # Sort by probability
        candidates.sort(key=lambda c: c.probability, reverse=True)
        
        return candidates
    
    def update_context(
        self, 
        concepts: List[Concept],
        context_window: int = 10
    ) -> List[Concept]:
        """
        Update and maintain a context window of recent concepts.
        
        This helper method manages the size of the context window,
        ensuring we don't keep too much history.
        
        Args:
            concepts: New concepts to add to context
            context_window: Maximum number of concepts to keep
            
        Returns:
            Updated context list
        """
        # For V1, this is a simple list operation
        # In future versions, this could maintain more sophisticated state
        return concepts[-context_window:]
    
    def _enhance_concepts_with_quantifiers(self, concepts: List[Concept]) -> List[Concept]:
        """
        Enhance concept list by adding quantifier-aware interpretations.
        
        For concepts like "Every_Student", this adds additional interpretation
        that they can be referenced by plural pronouns.
        
        Args:
            concepts: Original concept list
            
        Returns:
            Enhanced concept list
        """
        enhanced = concepts.copy()
        
        for concept in concepts:
            concept_lower = concept.lower()
            
            # If this is a quantified expression, add a plural interpretation
            if self._is_quantified_expression(concept_lower):
                # Extract the base noun if possible
                for quantifier in self.UNIVERSAL_QUANTIFIERS:
                    if quantifier in concept_lower:
                        # Try to extract base noun
                        base = concept_lower.replace(quantifier + "_", "").replace(quantifier + " ", "")
                        if base and base != concept_lower:
                            # Add plural form
                            if not base.endswith('s'):
                                plural_concept = Concept(base + "s")
                                if plural_concept not in enhanced:
                                    enhanced.append(plural_concept)
        
        return enhanced