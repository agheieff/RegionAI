"""
Grammatical Pattern Extractor for discovering language-to-graph mappings.

This module implements the foundational component of RegionAI's language model—
a tool that deconstructs English sentences into their core grammatical primitives
(Subject-Verb-Object triples), enabling the system to discover mappings between
linguistic patterns and knowledge graph structures.
"""
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from tier1.utils.component_loader import OptionalComponentMixin, get_nlp_model, requires_component


@dataclass
class GrammaticalPattern:
    """Represents a grammatical pattern extracted from text."""
    subject: Optional[str]      # The entity performing the action
    verb: str                   # The action or relationship
    object: Optional[str]       # The entity being acted upon
    modifiers: List[str]        # Additional modifiers (adjectives, adverbs, etc.)
    raw_sentence: str           # Original sentence for reference
    confidence: float           # Confidence in the extraction (0.0 to 1.0)
    
    def __str__(self):
        """String representation of the pattern."""
        subj = self.subject or "?"
        obj = self.object or "?"
        return f"({subj}, {self.verb}, {obj})"
    
    def to_triple(self) -> Tuple[Optional[str], str, Optional[str]]:
        """Return as a simple (subject, verb, object) triple."""
        return (self.subject, self.verb, self.object)


class GrammarPatternExtractor(OptionalComponentMixin):
    """
    Extracts grammatical patterns from natural language text.
    
    This class uses spaCy to parse sentences and extract Subject-Verb-Object
    triples, which form the basis for discovering mappings between language
    and the knowledge graph.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the grammar pattern extractor.
        
        Args:
            model_name: Name of the spaCy model to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        
        # Get the cached NLP model using centralized loader
        self.nlp = get_nlp_model(model_name)
        
        if self.nlp is None:
            raise RuntimeError(
                f"Failed to load required spaCy model '{model_name}'. "
                f"Please install it with: python -m spacy download {model_name}"
            )
        
        self.logger.info(f"Initialized GrammarPatternExtractor with {model_name}")
    
    @requires_component('nlp', "spaCy model is required for pattern extraction")
    def extract_patterns(self, text: str) -> List[GrammaticalPattern]:
        """
        Extract grammatical patterns from text.
        
        This method processes the input text with spaCy and extracts
        Subject-Verb-Object triples from each sentence.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of GrammaticalPattern objects
        """
        if not text or not text.strip():
            return []
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        patterns = []
        
        # Process each sentence
        for sent in doc.sents:
            # Try to extract patterns from this sentence
            sent_patterns = self._extract_from_sentence(sent)
            patterns.extend(sent_patterns)
        
        return patterns
    
    def _extract_from_sentence(self, sent) -> List[GrammaticalPattern]:
        """
        Extract patterns from a single sentence.
        
        Args:
            sent: spaCy sentence Doc
            
        Returns:
            List of patterns found in the sentence
        """
        patterns = []
        
        # Find the main verb(s) in the sentence
        root_verbs = [token for token in sent if token.dep_ == "ROOT" and token.pos_ == "VERB"]
        
        if not root_verbs:
            # Try to find any verb if no root verb
            verbs = [token for token in sent if token.pos_ == "VERB"]
            if verbs:
                root_verbs = [verbs[0]]  # Use the first verb found
        
        for verb in root_verbs:
            pattern = self._extract_svo_from_verb(verb, sent)
            if pattern:
                patterns.append(pattern)
        
        # Also handle copular sentences (e.g., "X is Y")
        copular_patterns = self._extract_copular_patterns(sent)
        patterns.extend(copular_patterns)
        
        return patterns
    
    def _extract_svo_from_verb(self, verb, sent) -> Optional[GrammaticalPattern]:
        """
        Extract Subject-Verb-Object pattern from a verb token.
        
        Args:
            verb: The verb token
            sent: The full sentence
            
        Returns:
            GrammaticalPattern or None if extraction fails
        """
        # Find subject
        subject = None
        subject_modifiers = []
        
        for child in verb.children:
            if child.dep_ in ("nsubj", "nsubjpass"):  # Nominal subject
                subject = child.lemma_.lower()
                # Collect subject modifiers
                subject_modifiers.extend([mod.text.lower() for mod in child.children 
                                        if mod.dep_ in ("det", "amod", "compound")])
                break
        
        # Find object
        obj = None
        object_modifiers = []
        
        for child in verb.children:
            if child.dep_ in ("dobj", "attr", "prep"):  # Direct object or attribute
                if child.dep_ == "prep":
                    # Handle prepositional phrases
                    for grandchild in child.children:
                        if grandchild.dep_ == "pobj":
                            obj = grandchild.lemma_.lower()
                            object_modifiers.extend([mod.text.lower() for mod in grandchild.children
                                                   if mod.dep_ in ("det", "amod", "compound")])
                            break
                else:
                    obj = child.lemma_.lower()
                    object_modifiers.extend([mod.text.lower() for mod in child.children
                                           if mod.dep_ in ("det", "amod", "compound")])
                break
        
        # Get lemmatized verb
        verb_lemma = verb.lemma_.lower()
        
        # Skip auxiliary verbs as main verbs
        if verb_lemma in ("be", "have", "do", "will", "would", "can", "could", "may", "might", "shall", "should"):
            return None
        
        # Calculate confidence based on pattern completeness
        confidence = 0.5  # Base confidence
        if subject:
            confidence += 0.25
        if obj:
            confidence += 0.25
        
        # Combine modifiers
        all_modifiers = subject_modifiers + object_modifiers
        
        return GrammaticalPattern(
            subject=subject,
            verb=verb_lemma,
            object=obj,
            modifiers=all_modifiers,
            raw_sentence=sent.text.strip(),
            confidence=confidence
        )
    
    def _extract_copular_patterns(self, sent) -> List[GrammaticalPattern]:
        """
        Extract patterns from copular sentences (e.g., "X is Y").
        
        Args:
            sent: The sentence to analyze
            
        Returns:
            List of patterns for copular constructions
        """
        patterns = []
        
        # Find copular verbs (forms of "be")
        for token in sent:
            if token.lemma_ == "be" and token.dep_ == "ROOT":
                # Find subject
                subject = None
                for child in token.children:
                    if child.dep_ in ("nsubj", "nsubjpass"):
                        subject = child.lemma_.lower()
                        break
                
                # Find complement (what comes after "is")
                complement = None
                relation_type = None
                
                for child in token.children:
                    if child.dep_ == "attr":  # Attribute (e.g., "X is a Y")
                        complement = child.lemma_.lower()
                        # Check if there's a determiner suggesting type
                        for grandchild in child.children:
                            if grandchild.dep_ == "det" and grandchild.text.lower() in ("a", "an"):
                                relation_type = "is_a"
                                break
                        else:
                            relation_type = "is"
                        break
                    elif child.dep_ == "acomp":  # Adjectival complement
                        complement = child.lemma_.lower()
                        relation_type = "has_property"
                        break
                
                if subject and complement and relation_type:
                    patterns.append(GrammaticalPattern(
                        subject=subject,
                        verb=relation_type,
                        object=complement,
                        modifiers=[],
                        raw_sentence=sent.text.strip(),
                        confidence=0.8  # High confidence for clear copular patterns
                    ))
        
        return patterns
    
    def extract_patterns_with_context(self, text: str, function_name: str = None) -> List[GrammaticalPattern]:
        """
        Extract patterns with additional context information.
        
        Args:
            text: The text to analyze
            function_name: Optional function name for context
            
        Returns:
            List of patterns with enhanced context
        """
        patterns = self.extract_patterns(text)
        
        # If we have a function name, we might boost confidence for patterns
        # that mention concepts related to the function name
        if function_name and patterns:
            function_parts = self._split_identifier(function_name)
            
            for pattern in patterns:
                # Boost confidence if subject or object matches function parts
                if pattern.subject in function_parts or pattern.object in function_parts:
                    pattern.confidence = min(1.0, pattern.confidence + 0.1)
        
        return patterns
    
    def _split_identifier(self, identifier: str) -> List[str]:
        """
        Split a code identifier into meaningful parts.
        
        Args:
            identifier: Code identifier (e.g., "get_user_orders")
            
        Returns:
            List of parts in lowercase
        """
        import re
        
        # Handle snake_case
        if '_' in identifier:
            parts = identifier.lower().split('_')
        else:
            # Handle camelCase
            parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', identifier)
            parts = [p.lower() for p in parts]
        
        # Filter out common prefixes that don't add meaning
        skip_words = {'get', 'set', 'is', 'has', 'create', 'update', 'delete', 'find'}
        return [p for p in parts if p not in skip_words]