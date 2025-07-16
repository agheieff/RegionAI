"""
Grammatical pattern extraction service.

This module handles the extraction of grammatical patterns from documentation text,
preparing for future language-to-graph mapping capabilities.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from ...domains.language import nlp_extractor
from ...config import RegionAIConfig, DEFAULT_CONFIG


@dataclass
class ExtractedPattern:
    """A grammatical pattern extracted from text."""
    function: str
    subject: Optional[str]
    verb: str
    object: Optional[str]
    modifiers: List[str]
    sentence: str
    confidence: float


class GrammarExtractor:
    """
    Service for extracting grammatical patterns from text.
    
    This class extracts the grammatical pattern extraction logic from KnowledgeLinker,
    focusing on discovering Subject-Verb-Object triples that can later be mapped
    to the knowledge graph.
    """
    
    def __init__(self, nlp_model, config: RegionAIConfig = None):
        """
        Initialize the grammar extractor.
        
        Args:
            nlp_model: A loaded spaCy model instance
            config: Configuration object
        """
        self.nlp_model = nlp_model
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Track discovered patterns for reporting
        self._discovered_patterns: List[ExtractedPattern] = []
    
    def extract_patterns_from_text(self, text: str, function_name: str,
                                  base_confidence: float) -> List[ExtractedPattern]:
        """
        Extract grammatical patterns from documentation text.
        
        This is the first step in discovering the mapping between language
        and the knowledge graph - breaking sentences into Subject-Verb-Object triples.
        
        Args:
            text: The documentation text to analyze
            function_name: Name of the function being documented
            base_confidence: Base confidence from documentation quality
            
        Returns:
            List of extracted grammatical patterns
        """
        if not self.nlp_model:
            self.logger.warning("No spaCy model available for pattern extraction")
            return []
        
        # Extract patterns with context
        patterns = nlp_extractor.extract_patterns_with_context(
            text, self.nlp_model, function_name, self.config
        )
        
        extracted_patterns = []
        
        # Convert to our ExtractedPattern format and track
        for pattern in patterns:
            extracted = ExtractedPattern(
                function=function_name,
                subject=pattern.subject,
                verb=pattern.verb,
                object=pattern.object,
                modifiers=pattern.modifiers,
                sentence=pattern.raw_sentence,
                confidence=pattern.confidence * base_confidence
            )
            
            # Log the discovered pattern
            self.logger.debug(
                f"Grammar pattern in {function_name}: {pattern} "
                f"[confidence: {extracted.confidence:.2f}]"
            )
            
            # Track for reporting
            self._discovered_patterns.append(extracted)
            extracted_patterns.append(extracted)
        
        return extracted_patterns
    
    def get_discovered_patterns(self) -> List[Dict[str, any]]:
        """Get list of all discovered grammatical patterns for reporting."""
        return [
            {
                'function': pattern.function,
                'subject': pattern.subject,
                'verb': pattern.verb,
                'object': pattern.object,
                'modifiers': pattern.modifiers,
                'sentence': pattern.sentence,
                'confidence': pattern.confidence
            }
            for pattern in self._discovered_patterns
        ]
    
    def clear_tracking(self):
        """Clear tracked patterns (useful for testing)."""
        self._discovered_patterns.clear()
    
    def analyze_pattern_distribution(self) -> Dict[str, any]:
        """
        Analyze the distribution of discovered patterns.
        
        Returns:
            Dictionary with pattern statistics
        """
        if not self._discovered_patterns:
            return {
                'total_patterns': 0,
                'verb_distribution': {},
                'completeness_stats': {
                    'complete': 0,
                    'missing_subject': 0,
                    'missing_object': 0
                }
            }
        
        # Count verb occurrences
        verb_counts = {}
        completeness_stats = {
            'complete': 0,
            'missing_subject': 0,
            'missing_object': 0
        }
        
        for pattern in self._discovered_patterns:
            # Track verb distribution
            verb_counts[pattern.verb] = verb_counts.get(pattern.verb, 0) + 1
            
            # Track completeness
            if pattern.subject and pattern.object:
                completeness_stats['complete'] += 1
            elif not pattern.subject:
                completeness_stats['missing_subject'] += 1
            elif not pattern.object:
                completeness_stats['missing_object'] += 1
        
        # Sort verbs by frequency
        sorted_verbs = sorted(verb_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_patterns': len(self._discovered_patterns),
            'verb_distribution': dict(sorted_verbs[:10]),  # Top 10 verbs
            'completeness_stats': completeness_stats,
            'average_confidence': sum(p.confidence for p in self._discovered_patterns) / len(self._discovered_patterns)
        }