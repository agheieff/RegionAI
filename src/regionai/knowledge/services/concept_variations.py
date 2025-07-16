"""
Concept variation builder service.

This module handles building variations of concept names (singular, plural, with articles)
to improve matching in natural language text.
"""
from typing import Dict, Set, List, Tuple
import logging

from ..graph import Concept
from ...utils.text_utils import to_singular, to_plural, is_plural


class ConceptVariationBuilder:
    """
    Service for building concept name variations.
    
    This class extracts the concept variation logic from KnowledgeLinker,
    making it reusable and independently testable.
    """
    
    def __init__(self):
        """Initialize the variation builder."""
        self.logger = logging.getLogger(__name__)
    
    def build_variations(self, concepts: Set[Concept]) -> Dict[str, Concept]:
        """
        Build a mapping of concept name variations to canonical concepts.
        
        Uses the inflect library for robust pluralization handling.
        
        Args:
            concepts: Set of concepts to build variations for
            
        Returns:
            Dictionary mapping variations to canonical concepts
        """
        variations = {}
        
        # First, build a map of all concepts to their canonical (singular) form
        canonical_map = {}
        for concept in concepts:
            concept_str = str(concept)
            
            # Determine if this concept is plural
            if is_plural(concept_str):
                # Find the singular form in our concept set
                singular_form = to_singular(concept_str)
                for other in concepts:
                    if str(other).lower() == singular_form.lower():
                        canonical_map[concept] = other
                        break
                else:
                    # No singular form found, use this as canonical
                    canonical_map[concept] = concept
            else:
                # Already singular, use as canonical
                canonical_map[concept] = concept
        
        # Now build variations for each canonical concept
        processed_canonicals = set()
        
        for concept in concepts:
            canonical = canonical_map[concept]
            
            # Skip if we've already processed this canonical form
            if canonical in processed_canonicals:
                continue
            processed_canonicals.add(canonical)
            
            canonical_str = str(canonical)
            
            # Get both singular and plural forms
            singular_form = to_singular(canonical_str)
            plural_form = to_plural(singular_form)
            
            # Add variations for singular form
            variations[singular_form.lower()] = canonical
            variations[singular_form] = canonical  # Keep original case
            
            # Add variations for plural form
            variations[plural_form.lower()] = canonical
            variations[plural_form] = canonical  # Keep original case
            
            # Add variations with articles (using singular form)
            variations[f"a {singular_form.lower()}"] = canonical
            variations[f"an {singular_form.lower()}"] = canonical
            variations[f"the {singular_form.lower()}"] = canonical
            
            # Add variations with articles (using plural form)
            variations[f"the {plural_form.lower()}"] = canonical
        
        self.logger.debug(f"Built {len(variations)} variations for {len(concepts)} concepts")
        
        return variations
    
    def find_concepts_in_sentence(self, sentence: str, concept_variations: Dict[str, Concept]) -> List[Tuple[Concept, int, int]]:
        """
        Find all known concepts mentioned in a sentence.
        
        Args:
            sentence: The sentence to search
            concept_variations: Mapping of variations to canonical concepts
            
        Returns:
            List of (concept, start_pos, end_pos) tuples
        """
        import re
        
        sentence_lower = sentence.lower()
        found_concepts = []
        
        # Look for each concept variation
        for variation, concept in concept_variations.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variation) + r'\b'
            for match in re.finditer(pattern, sentence_lower):
                found_concepts.append((concept, match.start(), match.end()))
        
        # Remove overlapping matches, keeping the longest
        found_concepts = self._remove_overlapping_matches(found_concepts)
        
        return found_concepts
    
    def _remove_overlapping_matches(self, matches: List[Tuple[Concept, int, int]]) -> List[Tuple[Concept, int, int]]:
        """Remove overlapping concept matches, keeping the longest."""
        if not matches:
            return []
        
        # Sort by start position, then by length (descending)
        sorted_matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1])))
        
        result = []
        last_end = -1
        
        for concept, start, end in sorted_matches:
            if start >= last_end:
                result.append((concept, start, end))
                last_end = end
        
        return result