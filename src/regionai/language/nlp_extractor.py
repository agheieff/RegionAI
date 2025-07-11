"""
NLP extraction utilities for intelligent part-of-speech tagging.

This module provides natural language processing capabilities to extract
meaningful words from code identifiers, replacing hardcoded term lists
with intelligent POS tagging.
"""
import re
from typing import List, Set, Optional
import spacy
from spacy.language import Language


class NLPExtractor:
    """
    Extracts meaningful words from code identifiers using NLP.
    
    This class uses spaCy's POS tagging to intelligently identify nouns
    and other parts of speech from snake_case and camelCase identifiers,
    replacing brittle hardcoded lists with proper NLP.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the NLP extractor with a spaCy model.
        
        Args:
            model_name: Name of the spaCy model to load (default: en_core_web_sm)
        """
        self.nlp = self._load_model(model_name)
        
    def _load_model(self, model_name: str) -> Language:
        """
        Load the spaCy model with error handling.
        
        Args:
            model_name: Name of the spaCy model to load
            
        Returns:
            Loaded spaCy Language object
            
        Raises:
            OSError: If the model is not installed
        """
        try:
            return spacy.load(model_name)
        except OSError:
            raise OSError(
                f"spaCy model '{model_name}' not found. "
                f"Please install it with: python -m spacy download {model_name}"
            )
    
    def extract_nouns_from_identifier(self, identifier: str) -> List[str]:
        """
        Extract nouns from a code identifier using POS tagging.
        
        Args:
            identifier: A snake_case or camelCase identifier
            
        Returns:
            List of nouns found in the identifier
        """
        # Split the identifier into words
        words = self._split_identifier(identifier)
        
        # Filter to meaningful words (length > 2)
        words = [w for w in words if len(w) > 2]
        
        if not words:
            return []
        
        # Join words into a sentence-like string for NLP processing
        text = " ".join(words)
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract nouns based on POS tags
        nouns = []
        for token in doc:
            # Look for nouns: NOUN (common noun) or PROPN (proper noun)
            if token.pos_ in ["NOUN", "PROPN"]:
                # Skip if it's an acronym (all uppercase)
                if not token.text.isupper():
                    nouns.append(token.text.lower())
        
        return nouns
    
    def extract_parts_of_speech(self, identifier: str) -> dict:
        """
        Extract all parts of speech from an identifier.
        
        This method provides more detailed POS information for advanced uses.
        
        Args:
            identifier: A snake_case or camelCase identifier
            
        Returns:
            Dictionary mapping POS tags to lists of words
        """
        # Split the identifier into words
        words = self._split_identifier(identifier)
        
        # Filter to meaningful words
        words = [w for w in words if len(w) > 2]
        
        if not words:
            return {}
        
        # Process with spaCy
        text = " ".join(words)
        doc = self.nlp(text)
        
        # Group by POS
        pos_groups = {}
        for token in doc:
            pos = token.pos_
            if pos not in pos_groups:
                pos_groups[pos] = []
            pos_groups[pos].append(token.text.lower())
        
        return pos_groups
    
    def _split_identifier(self, identifier: str) -> List[str]:
        """
        Split a code identifier into individual words.
        
        Handles both snake_case and camelCase identifiers.
        
        Args:
            identifier: The identifier to split
            
        Returns:
            List of individual words
        """
        # First split by underscore (snake_case)
        underscore_parts = identifier.split('_')
        all_parts = []
        
        for part in underscore_parts:
            # Then split each part by camelCase
            # This regex finds transitions from lowercase to uppercase
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', part)
            if camel_parts:
                all_parts.extend(camel_parts)
            else:
                # If no camelCase found, keep the part as is
                if part:
                    all_parts.append(part)
        
        # Convert to lowercase for consistency
        return [part.lower() for part in all_parts if part]
    
    def is_noun_heavy(self, identifier: str, threshold: float = 0.5) -> bool:
        """
        Check if an identifier is primarily composed of nouns.
        
        Useful for identifying entity-like identifiers.
        
        Args:
            identifier: The identifier to check
            threshold: Minimum ratio of nouns to total words
            
        Returns:
            True if the identifier has a high ratio of nouns
        """
        words = self._split_identifier(identifier)
        words = [w for w in words if len(w) > 2]
        
        if not words:
            return False
        
        nouns = self.extract_nouns_from_identifier(identifier)
        noun_ratio = len(nouns) / len(words)
        
        return noun_ratio >= threshold
    
    def extract_verbs_from_text(self, text: str) -> List[str]:
        """
        Extract verbs from natural language text using POS tagging.
        
        This method identifies all verbs in the text and returns their
        lemmatized (base) forms. For example, "updating", "updated", 
        and "updates" all become "update".
        
        Args:
            text: Natural language text to analyze
            
        Returns:
            List of lemmatized verbs found in the text
        """
        # Process the text with spaCy
        doc = self.nlp(text)
        
        # Extract verbs and lemmatize them
        verbs = []
        for token in doc:
            # Check if token is a verb (including auxiliary verbs)
            if token.pos_ == "VERB":
                # Get the lemma (base form) of the verb
                lemma = token.lemma_.lower()
                
                # Skip common auxiliary verbs and be-verbs
                if lemma not in {"be", "have", "do", "will", "would", "could", 
                                "should", "might", "may", "can", "must"}:
                    verbs.append(lemma)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_verbs = []
        for verb in verbs:
            if verb not in seen:
                seen.add(verb)
                unique_verbs.append(verb)
        
        return unique_verbs
    
    def extract_verbs_from_identifier(self, identifier: str) -> List[str]:
        """
        Extract verbs from a code identifier.
        
        Similar to extract_nouns_from_identifier but focuses on verbs.
        Useful for analyzing function names to understand actions.
        
        Args:
            identifier: A snake_case or camelCase identifier
            
        Returns:
            List of lemmatized verbs found in the identifier
        """
        # Split the identifier into words
        words = self._split_identifier(identifier)
        
        if not words:
            return []
        
        # Join words and process as text
        text = " ".join(words)
        
        # Extract verbs using the text method
        return self.extract_verbs_from_text(text)