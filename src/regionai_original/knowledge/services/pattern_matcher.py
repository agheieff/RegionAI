"""
Pattern matching service for relationship discovery.

This module handles the pattern-based matching of relationships between concepts
in natural language text, extracting specific relationship types based on
linguistic patterns.
"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

from ...config import RegionAIConfig, DEFAULT_CONFIG
from ..graph import Concept


@dataclass
class RelationshipMatch:
    """Represents a matched relationship pattern."""
    source_concept: Concept
    target_concept: Concept
    relationship_type: str
    evidence: str
    source_function: str
    confidence: float
    pattern_used: str


class RelationshipPatternMatcher:
    """
    Service for matching relationship patterns in text.
    
    This class encapsulates the pattern matching logic previously embedded
    in KnowledgeLinker, making it more focused and testable.
    """
    
    # Patterns that indicate specific relationship types
    PATTERNS = {
        'HAS_ONE': [
            r'{source}\s+has\s+(?:a|an)\s+{target}',
            r'{source}\s+contains\s+(?:a|an)\s+{target}',
            r'{source}\s+includes\s+(?:a|an)\s+{target}',
            r'{source}\s+owns\s+(?:a|an)\s+{target}',
            r'each\s+{source}\s+has\s+(?:a|an)\s+{target}',
            r'{source}\s+has\s+one\s+{target}',
            r'each\s+{source}\s+has\s+one\s+{target}',
            r'{source}\s+has\s+exactly\s+one\s+{target}',
            r'each\s+{source}\s+has\s+exactly\s+one\s+{target}',
        ],
        'HAS_MANY': [
            r'{source}\s+has\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+contains?\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+contain\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}s?\s+contain\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+can\s+have\s+(?:multiple|many|several)\s+{target}s?',
            r'{source}\s+manages\s+{target}s?',
            r'{source}\s+tracks\s+{target}s?',
        ],
        'BELONGS_TO': [
            r'{source}s?\s+belong(?:s)?\s+to\s+(?:a|an|one)?\s*{target}s?',
            r'{source}\s+belongs\s+to\s+(?:a|an|exactly\s+one)?\s*{target}',
            r'{source}\s+is\s+owned\s+by\s+(?:a|an)?\s*{target}',
            r'{source}\s+is\s+part\s+of\s+(?:a|an)?\s*{target}',
            r'{source}\s+is\s+associated\s+with\s+(?:a|an)?\s*{target}',
            r'{target}\s+owns\s+(?:the\s+)?{source}',
            r'each\s+{source}\s+belongs\s+to\s+(?:a|an|exactly\s+one)?\s*{target}',
        ],
        'IS_A': [
            r'{source}\s+is\s+(?:a|an)\s+{target}',
            r'{source}\s+extends\s+{target}',
            r'{source}\s+inherits\s+from\s+{target}',
            r'{source}\s+is\s+a\s+type\s+of\s+{target}',
            r'{source}\s+is\s+a\s+kind\s+of\s+{target}',
        ],
        'USES': [
            r'{source}\s+uses\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+requires\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+depends\s+on\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+needs\s+(?:a|an|the)?\s*{target}',
        ],
        'CREATES': [
            r'{source}\s+creates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+generates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+produces?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+builds?\s+(?:a|an|the)?\s*{target}',
        ],
        'VALIDATES': [
            r'{source}\s+validates?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+verifies?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+checks?\s+(?:a|an|the)?\s*{target}',
            r'{source}\s+ensures?\s+(?:a|an|the)?\s*{target}\s+is\s+valid',
        ]
    }
    
    def __init__(self, concept_variations: Dict[str, Concept], config: RegionAIConfig = None):
        """
        Initialize the pattern matcher.
        
        Args:
            concept_variations: Mapping of concept name variations to canonical concepts
            config: Configuration object
        """
        self.concept_variations = concept_variations
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(__name__)
    
    def find_relationships(self, sentence: str, concepts_in_sentence: List[Tuple[Concept, int, int]],
                          source_function: str, base_confidence: float) -> List[RelationshipMatch]:
        """
        Find relationships between concepts in a sentence.
        
        Args:
            sentence: The sentence to analyze
            concepts_in_sentence: List of (concept, start_pos, end_pos) tuples
            source_function: Function where this sentence was found
            base_confidence: Base confidence from documentation quality
            
        Returns:
            List of RelationshipMatch objects
        """
        matches = []
        
        # Try each pair of concepts
        for i in range(len(concepts_in_sentence)):
            for j in range(i + 1, len(concepts_in_sentence)):
                concept1, _, _ = concepts_in_sentence[i]
                concept2, _, _ = concepts_in_sentence[j]
                
                # Try to match relationship patterns
                for rel_type, patterns in self.PATTERNS.items():
                    for pattern_template in patterns:
                        # Try both directions
                        if self._match_pattern(sentence, concept1, concept2, pattern_template):
                            match = self._create_match(
                                concept1, concept2, rel_type, sentence,
                                source_function, base_confidence, pattern_template
                            )
                            matches.append(match)
                            break
                        
                        # Try reverse direction for asymmetric relationships
                        if rel_type not in ['IS_A', 'BELONGS_TO']:
                            if self._match_pattern(sentence, concept2, concept1, pattern_template):
                                match = self._create_match(
                                    concept2, concept1, rel_type, sentence,
                                    source_function, base_confidence, pattern_template
                                )
                                matches.append(match)
                                break
        
        return matches
    
    def _match_pattern(self, sentence: str, source_concept: Concept, 
                      target_concept: Concept, pattern_template: str) -> bool:
        """
        Check if a sentence matches a relationship pattern.
        
        Args:
            sentence: The sentence to check
            source_concept: The source concept
            target_concept: The target concept
            pattern_template: Pattern template with {source} and {target} placeholders
            
        Returns:
            True if the pattern matches
        """
        sentence_lower = sentence.lower()
        
        # Find all occurrences of the concepts in the sentence
        source_occurrences = []
        target_occurrences = []
        
        # Check all variations of source concept
        for variation, concept in self.concept_variations.items():
            if concept == source_concept:
                # Use word boundaries to find exact matches
                pattern = r'\b' + re.escape(variation) + r'\b'
                for match in re.finditer(pattern, sentence_lower):
                    source_occurrences.append((match.group(), match.start(), match.end()))
                    
            elif concept == target_concept:
                pattern = r'\b' + re.escape(variation) + r'\b'
                for match in re.finditer(pattern, sentence_lower):
                    target_occurrences.append((match.group(), match.start(), match.end()))
        
        # Now check if any combination of source and target occurrences
        # matches the relationship pattern
        for source_word, s_start, s_end in source_occurrences:
            for target_word, t_start, t_end in target_occurrences:
                # Build a pattern using the actual words found
                test_pattern = pattern_template
                
                # Replace {source}s? with a pattern that matches the actual source word
                test_pattern = test_pattern.replace('{source}s?', re.escape(source_word))
                test_pattern = test_pattern.replace('{source}', re.escape(source_word))
                
                # Same for target
                test_pattern = test_pattern.replace('{target}s?', re.escape(target_word))
                test_pattern = test_pattern.replace('{target}', re.escape(target_word))
                
                # Now test if this pattern matches the sentence
                if re.search(test_pattern, sentence_lower):
                    return True
        
        return False
    
    def _create_match(self, source: Concept, target: Concept, rel_type: str,
                     evidence: str, source_function: str, base_confidence: float,
                     pattern_used: str) -> RelationshipMatch:
        """Create a RelationshipMatch object."""
        # Calculate final confidence
        # Higher confidence if the relationship type is explicit
        pattern_confidence = 0.8 if rel_type in ['HAS_ONE', 'HAS_MANY', 'BELONGS_TO'] else 0.7
        final_confidence = base_confidence * pattern_confidence
        
        # Strip and normalize evidence
        evidence_cleaned = ' '.join(evidence.strip().split())
        
        return RelationshipMatch(
            source_concept=source,
            target_concept=target,
            relationship_type=rel_type,
            evidence=evidence_cleaned,
            source_function=source_function,
            confidence=final_confidence,
            pattern_used=pattern_used
        )