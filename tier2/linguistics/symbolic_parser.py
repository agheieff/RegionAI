"""
Symbolic Parser for the Natural Language Understanding Pipeline.

This module implements the parsing stage that converts sentences into hierarchical
ParseTree structures. It uses the CandidateGenerator to obtain possible meanings
for phrases and assembles them into a nested representation suitable for
downstream reasoning.
"""

import re
import functools
from typing import List, Tuple, Optional, TYPE_CHECKING, Dict, Any

# Type checking import for cache info type hint
if TYPE_CHECKING:
    from functools import _CacheInfo  # noqa: F401
from .symbolic import SymbolicConstraint, ParseTree, RegionCandidate
from .candidate_generator import CandidateGenerator
from .context_resolver import ContextResolver
from tier1.knowledge.infrastructure.world_graph import Concept


class SymbolicParser:
    """
    Parses natural language sentences into hierarchical symbolic structures.
    
    The SymbolicParser takes full sentences and builds ParseTree structures
    that represent the nested linguistic relationships. It uses the
    CandidateGenerator to obtain possible meanings for individual phrases
    and organizes them hierarchically based on syntactic structure.
    
    This is the component that transforms flat text into the structured
    representation our reasoning engine operates on.
    """
    
    def __init__(self, candidate_generator: CandidateGenerator, config=None):
        """
        Initialize the parser with a candidate generator.
        
        Args:
            candidate_generator: The CandidateGenerator instance to use
                               for obtaining phrase interpretations
            config: Configuration object. If None, uses DEFAULT_CONFIG
        """
        from tier1.config import DEFAULT_CONFIG
        config = config or DEFAULT_CONFIG
        
        self.candidate_generator = candidate_generator
        self.context_resolver = ContextResolver()
        
        # Beam width for candidate generation (can be configured)
        self.default_beam_width = 5
        
        # Parsing context: recently identified concepts
        self.parsing_context: set[Concept] = set()
        self.context_window_size = 10  # Keep last 10 concepts
        
        # Create the cached version of _parse_sentence_impl
        self._cached_parse = functools.lru_cache(maxsize=1024)(self._parse_sentence_impl)
        
        # Track successful resolutions for learning
        self.successful_resolutions: List[Dict[str, Any]] = []
        self.learning_threshold = config.symbolic_parser_learning_threshold  # Configurable threshold
    
    def parse_sentence(self, sentence: str) -> ParseTree:
        """
        Parse a sentence into a hierarchical ParseTree.
        
        This method is the public interface that handles caching.
        It converts the parsing context to a hashable form and
        delegates to the cached implementation.
        
        Args:
            sentence: The input sentence to parse
            
        Returns:
            A ParseTree representing the hierarchical structure
        """
        # Create a hashable context fingerprint
        context_fingerprint = self._create_context_fingerprint()
        
        # Call the cached implementation
        return self._cached_parse(sentence, context_fingerprint)
    
    def _create_context_fingerprint(self) -> Tuple[str, ...]:
        """
        Create a stable, hashable representation of the parsing context.
        
        Returns:
            A sorted tuple of concept names
        """
        # Convert concepts to their string representation and sort
        # This ensures a stable fingerprint regardless of order
        return tuple(sorted(str(concept) for concept in self.parsing_context))
    
    def _parse_sentence_impl(self, sentence: str, context_fingerprint: Tuple[str, ...]) -> ParseTree:
        """
        Implementation of parse_sentence that can be cached.
        
        This method performs the actual parsing. The context fingerprint
        is passed as a parameter to make the function pure and cacheable.
        
        Args:
            sentence: The input sentence to parse
            context_fingerprint: Hashable representation of context
            
        Returns:
            A ParseTree representing the hierarchical structure
        """
        # Save the current context to restore later
        saved_context = self.parsing_context.copy()
        
        try:
            # Perform the parsing (this may modify self.parsing_context)
            tree = self._do_parse_sentence(sentence)
            
            # Store any new concepts discovered during this parse
            new_concepts = self.parsing_context - saved_context
            
            # Restore the original context for cache consistency
            self.parsing_context = saved_context
            
            # Add the new concepts after restoring
            # This ensures the cache key remains valid
            for concept in new_concepts:
                self.parsing_context.add(concept)
                    
            # Maintain context window
            updated_context = self.context_resolver.update_context(
                list(self.parsing_context),
                self.context_window_size
            )
            self.parsing_context = set(updated_context)
            
            return tree
        except Exception:
            # Restore context even on error
            self.parsing_context = saved_context
            raise
    
    def _do_parse_sentence(self, sentence: str) -> ParseTree:
        """
        Parse a sentence into a hierarchical ParseTree.
        
        This method performs basic sentence chunking and builds a tree
        structure representing the linguistic relationships. For V1,
        we use simple rule-based chunking.
        
        Args:
            sentence: The input sentence to parse
            
        Returns:
            A ParseTree representing the hierarchical structure
        """
        # Clean the sentence
        sentence = sentence.strip()
        
        # Chunk the sentence into main clause and sub-clauses
        chunks = self._chunk_sentence(sentence)
        
        if not chunks:
            # Empty sentence - return minimal tree
            empty_constraint = SymbolicConstraint(text="")
            return ParseTree(root_constraint=empty_constraint)
        
        # Create constraints for each chunk
        constraints = []
        for chunk_text, chunk_type in chunks:
            constraint = self._create_constraint_for_chunk(chunk_text, chunk_type)
            constraints.append((constraint, chunk_type))
        
        # Build the tree structure
        tree = self._build_tree_from_constraints(constraints)
        
        return tree
    
    def _chunk_sentence(self, sentence: str) -> List[Tuple[str, str]]:
        """
        Perform basic sentence chunking.
        
        For V1, we use simple rules:
        - Text between commas that starts with "which", "who", "that" is a relative clause
        - Text after certain punctuation (;, :) is a dependent clause
        - Everything else is part of the main clause
        
        Args:
            sentence: The sentence to chunk
            
        Returns:
            List of (chunk_text, chunk_type) tuples where chunk_type is one of:
            'main', 'relative', 'dependent'
        """
        chunks = []
        
        # First, identify relative clauses (text between commas starting with which/who/that)
        relative_pattern = r',\s*(which|who|that)\s+[^,]+(?:,|$)'
        relative_matches = list(re.finditer(relative_pattern, sentence))
        
        # Build a list of all chunks with their positions
        chunk_positions = []
        
        # Add relative clauses
        for match in relative_matches:
            # Remove leading comma and trailing comma if present
            text = match.group().strip(',').strip()
            chunk_positions.append((match.start(), match.end(), text, 'relative'))
        
        # Sort by position
        chunk_positions.sort(key=lambda x: x[0])
        
        # Extract main clause parts (everything not in a relative clause)
        main_parts = []
        last_end = 0
        
        for start, end, _, _ in chunk_positions:
            if last_end < start:
                main_parts.append(sentence[last_end:start])
            last_end = end
        
        # Don't forget the final part
        if last_end < len(sentence):
            main_parts.append(sentence[last_end:])
        
        # Clean and join main parts
        main_text = ' '.join(part.strip(' ,') for part in main_parts if part.strip(' ,'))
        
        # Check for dependent clauses in the main text (after ; or :)
        if ';' in main_text or ':' in main_text:
            # Split on semicolon or colon
            parts = re.split(r'[;:]', main_text)
            if len(parts) > 1:
                # First part is main, rest are dependent
                chunks.append((parts[0].strip(), 'main'))
                for part in parts[1:]:
                    if part.strip():
                        chunks.append((part.strip(), 'dependent'))
            else:
                chunks.append((main_text, 'main'))
        else:
            if main_text:
                chunks.append((main_text, 'main'))
        
        # Add the relative clauses
        for _, _, text, chunk_type in chunk_positions:
            chunks.append((text, chunk_type))
        
        return chunks
    
    def _create_constraint_for_chunk(self, chunk_text: str, chunk_type: str) -> SymbolicConstraint:
        """
        Create a SymbolicConstraint for a text chunk.
        
        This method uses the CandidateGenerator to obtain possible meanings
        and creates a constraint with appropriate memoization key.
        
        Args:
            chunk_text: The text of the chunk
            chunk_type: The type of chunk ('main', 'relative', 'dependent')
            
        Returns:
            A SymbolicConstraint with candidates from the generator
        """
        # Check if this chunk contains pronouns that need resolution
        if self._contains_pronoun(chunk_text):
            # Extract the pronoun and resolve it
            pronoun = self._extract_pronoun(chunk_text)
            if pronoun and self.parsing_context:
                candidates = self.context_resolver.resolve_pronoun(pronoun, list(self.parsing_context))
                
                # Track successful high-confidence resolutions
                if candidates and candidates[0].probability >= self.learning_threshold:
                    # Record this successful resolution
                    for concept in candidates[0].concept_intersections:
                        resolution = {
                            'word': pronoun,
                            'concept': concept,
                            'probability': candidates[0].probability,
                            'sentence': chunk_text
                        }
                        self.successful_resolutions.append(resolution)
                        
                        # If we have access to the knowledge graph, learn immediately
                        if hasattr(self.candidate_generator.knowledge_graph, 'learn_mapping'):
                            self.candidate_generator.knowledge_graph.learn_mapping(
                                pronoun, concept, candidates[0].probability
                            )
            else:
                # Fall back to regular generation if no context
                candidates = self._generate_candidates_with_context(chunk_text)
        else:
            # Regular candidate generation
            candidates = self._generate_candidates_with_context(chunk_text)
        
        # Create memoization key that includes chunk type for context
        memoization_key = f"{chunk_type}_{chunk_text.lower().replace(' ', '_')}"
        
        # Create the constraint
        constraint = SymbolicConstraint(
            text=chunk_text,
            memoization_key=memoization_key
        )
        
        # Add candidates with beam width limit
        for candidate in candidates[:self.default_beam_width]:
            constraint.add_candidate(candidate)
        
        # Mark as grounded since we've generated candidates
        if candidates:
            constraint.is_grounded = True
        
        # Update parsing context with identified concepts
        if candidates:
            # Add top concepts to parsing context
            for candidate in candidates[:3]:  # Keep top 3
                for concept in candidate.concept_intersections:
                    self.parsing_context.add(concept)
            
            # Maintain context window size
            updated_context = self.context_resolver.update_context(
                list(self.parsing_context), 
                self.context_window_size
            )
            self.parsing_context = set(updated_context)
        
        return constraint
    
    def _build_tree_from_constraints(
        self, 
        constraints: List[Tuple[SymbolicConstraint, str]]
    ) -> ParseTree:
        """
        Build a ParseTree from a list of constraints.
        
        For V1, we use a simple hierarchy:
        - Main clause is the root
        - Relative and dependent clauses are children of the main clause
        
        Args:
            constraints: List of (constraint, chunk_type) tuples
            
        Returns:
            A ParseTree representing the hierarchical structure
        """
        # Find the main clause (should be first)
        main_constraint = None
        other_constraints = []
        
        for constraint, chunk_type in constraints:
            if chunk_type == 'main':
                main_constraint = constraint
            else:
                other_constraints.append((constraint, chunk_type))
        
        # If no main clause, use the first constraint as root
        if main_constraint is None:
            if constraints:
                main_constraint = constraints[0][0]
                other_constraints = constraints[1:]
            else:
                # No constraints at all - shouldn't happen but handle gracefully
                return ParseTree(root_constraint=SymbolicConstraint(text=""))
        
        # Create the root tree
        tree = ParseTree(root_constraint=main_constraint)
        
        # Add other constraints as children
        for constraint, chunk_type in other_constraints:
            # Create a subtree for each child
            child_tree = ParseTree(root_constraint=constraint)
            tree.children[constraint] = child_tree
        
        return tree
    
    def parse_with_context(
        self, 
        sentence: str, 
        context: Optional[str] = None
    ) -> ParseTree:
        """
        Parse a sentence with additional context.
        
        This enhanced method considers surrounding context when generating
        candidates for better disambiguation.
        
        Args:
            sentence: The sentence to parse
            context: Optional context (e.g., previous sentences)
            
        Returns:
            A ParseTree with context-aware candidate generation
        """
        # Store the original context state
        _saved_context = getattr(self, '_parsing_context', None)
        self._parsing_context = context or sentence
        
        try:
            # Parse with context available
            tree = self.parse_sentence(sentence)
        finally:
            # Restore context state
            self._parsing_context = _saved_context
        
        return tree
    
    def parse_sequence(self, sentences: List[str]) -> List[ParseTree]:
        """
        Parse a sequence of sentences with maintained context.
        
        This method parses multiple sentences in order, maintaining
        the parsing context between sentences to enable pronoun resolution
        and other cross-sentence references.
        
        Args:
            sentences: List of sentences to parse in order
            
        Returns:
            List of ParseTree objects, one for each sentence
        """
        trees = []
        
        for sentence in sentences:
            # Parse the sentence with current context
            tree = self.parse_sentence(sentence)
            trees.append(tree)
            
            # Context is automatically updated in _create_constraint_for_chunk
        
        return trees
    
    def _contains_pronoun(self, text: str) -> bool:
        """
        Check if text contains a pronoun that needs resolution.
        
        Args:
            text: The text to check
            
        Returns:
            True if text contains a resolvable pronoun
        """
        # Common pronouns to check for
        pronouns = {
            "it", "its", "itself",
            "they", "them", "their", "theirs", "themselves",
            "he", "him", "his", "himself",
            "she", "her", "hers", "herself"
        }
        
        # Simple word-based check
        words = text.lower().split()
        return any(word in pronouns for word in words)
    
    def _extract_pronoun(self, text: str) -> Optional[str]:
        """
        Extract the first pronoun from text.
        
        Args:
            text: The text to extract from
            
        Returns:
            The first pronoun found, or None
        """
        pronouns = {
            "it", "its", "itself",
            "they", "them", "their", "theirs", "themselves",
            "he", "him", "his", "himself",
            "she", "her", "hers", "herself"
        }
        
        words = text.lower().split()
        for word in words:
            if word in pronouns:
                return word
        
        return None
    
    def _generate_candidates_with_context(self, chunk_text: str) -> List[RegionCandidate]:
        """
        Generate candidates using the appropriate context.
        
        Args:
            chunk_text: The text to generate candidates for
            
        Returns:
            List of RegionCandidate objects
        """
        if hasattr(self, '_parsing_context') and self._parsing_context:
            return self.candidate_generator.generate_candidates_with_context(
                chunk_text, self._parsing_context
            )
        else:
            return self.candidate_generator.generate_candidates_for_phrase(chunk_text)
    
    def clear_context(self):
        """
        Clear the parsing context.
        
        This should be called when starting a new document or conversation
        to avoid incorrect cross-references.
        """
        self.parsing_context.clear()
    
    def clear_cache(self):
        """
        Clear the parsing cache.
        
        This should be called when the knowledge graph changes or
        when you want to force re-parsing of sentences.
        """
        self._cached_parse.cache_clear()
    
    def get_cache_info(self):
        """
        Get information about the cache performance.
        
        Returns:
            A named tuple with hits, misses, maxsize, and currsize
        """
        return self._cached_parse.cache_info()
    
    def enable_caching(self, maxsize: int = 1024):
        """
        Enable caching with specified maximum size.
        
        Args:
            maxsize: Maximum number of cached results to keep
        """
        self._cached_parse = functools.lru_cache(maxsize=maxsize)(self._parse_sentence_impl)
    
    def disable_caching(self):
        """
        Disable caching by replacing with uncached version.
        """
        # Create an uncached wrapper
        def uncached_wrapper(sentence: str, context_fingerprint: Tuple[str, ...]) -> ParseTree:
            return self._parse_sentence_impl(sentence, context_fingerprint)
        
        # Add dummy cache methods for compatibility
        uncached_wrapper.cache_clear = lambda: None
        uncached_wrapper.cache_info = lambda: functools._CacheInfo(0, 0, 0, 0)
        
        self._cached_parse = uncached_wrapper
    
    def get_successful_resolutions(self) -> List[Dict[str, Any]]:
        """
        Get all successful pronoun resolutions tracked by this parser.
        
        Returns:
            List of dictionaries containing resolution information:
            - word: The pronoun that was resolved
            - concept: The concept it resolved to
            - probability: The confidence of the resolution
            - sentence: The sentence context
        """
        return self.successful_resolutions.copy()
    
    def apply_learned_mappings(self, knowledge_graph):
        """
        Apply all learned mappings to a knowledge graph.
        
        This method takes all successful resolutions and adds them
        to the knowledge graph as learned mappings.
        
        Args:
            knowledge_graph: The WorldKnowledgeGraph to update
        """
        for resolution in self.successful_resolutions:
            if hasattr(knowledge_graph, 'learn_mapping'):
                knowledge_graph.learn_mapping(
                    resolution['word'],
                    resolution['concept'],
                    resolution['probability']
                )
    
    def clear_resolutions(self):
        """Clear the list of successful resolutions."""
        self.successful_resolutions.clear()