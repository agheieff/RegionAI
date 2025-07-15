"""
Centralized context resolution service for RegionAI.

This module provides a single source of truth for determining the context
of functions based on their associated concepts and code patterns.
"""
from typing import Set, Optional
import logging

from ..knowledge.graph import WorldKnowledgeGraph, Concept
from ..knowledge.models import FunctionArtifact
from .context_rules import DEFAULT_CONTEXT_RULES


class ContextResolver:
    """
    Service for determining the context/domain of functions.
    
    This class centralizes all logic for context determination,
    ensuring consistency across the system and preventing
    configuration drift.
    """
    
    def __init__(self):
        """Initialize the context resolver with default rules."""
        self.logger = logging.getLogger(__name__)
        self.context_rules = DEFAULT_CONTEXT_RULES
        
        # Build context indicators from rules for concept-based matching
        self._context_indicators = self._build_context_indicators()
    
    def determine_function_context(self, artifact: FunctionArtifact, 
                                 wkg: WorldKnowledgeGraph) -> str:
        """
        Determine the context/domain of a function based on its related concepts.
        
        This is the single source of truth for context determination logic.
        It considers both the concepts associated with the function and
        the keywords defined in context rules.
        
        Args:
            artifact: The function artifact to analyze
            wkg: World knowledge graph containing concept relationships
            
        Returns:
            Context string like "database-interaction", "file-io", or "general"
        """
        # Get all concepts related to this function
        related_concepts = set(artifact.discovered_concepts) if artifact.discovered_concepts else set()
        
        # Also check for concepts that might be indirectly related
        # by looking at the function node in the graph
        function_node = Concept(f"Function:{artifact.function_name}")
        if function_node in wkg:
            # Get all concepts connected to this function
            for source, target, relation in wkg.get_relations(function_node):
                if source == function_node:
                    related_concepts.add(target)
                else:
                    related_concepts.add(source)
        
        # Convert concepts to lowercase strings for checking
        concept_names = {str(c).lower() for c in related_concepts}
        
        # Check against each context's indicators
        context_scores = {}
        for context_tag, indicators in self._context_indicators.items():
            score = 0
            for indicator in indicators:
                # Check if indicator appears in any concept name
                if any(indicator in name for name in concept_names):
                    score += 1
            if score > 0:
                context_scores[context_tag] = score
        
        # If we have source code, also check against keyword rules
        if artifact.source_code:
            for rule in self.context_rules:
                score = 0
                for keyword in rule.keywords:
                    if keyword.lower() in artifact.source_code.lower():
                        score += 1
                if score > 0:
                    # Add to existing score or create new entry
                    if rule.context_tag in context_scores:
                        context_scores[rule.context_tag] = context_scores[rule.context_tag] + score
                    else:
                        context_scores[rule.context_tag] = score
        
        # Return the context with highest score
        if context_scores:
            best_context = max(context_scores.items(), key=lambda x: x[1])
            return best_context[0]
        
        # Default context
        return "general"
    
    def _build_context_indicators(self) -> dict:
        """
        Build a mapping of contexts to indicator terms.
        
        This extracts key terms from the context rules that can be
        matched against concept names.
        
        Returns:
            Dictionary mapping context tags to sets of indicator terms
        """
        indicators = {}
        
        # Extract meaningful terms from context rule keywords
        for rule in self.context_rules:
            terms = set()
            for keyword in rule.keywords:
                # Extract alphanumeric terms
                term = ''.join(c for c in keyword.lower() if c.isalnum())
                if len(term) > 2:  # Skip very short terms
                    terms.add(term)
                    
                # Also add specific known terms for each context
                if rule.context_tag == "database-interaction":
                    terms.update(['database', 'sql', 'query', 'db', 'table', 'column'])
                elif rule.context_tag == "file-io":
                    terms.update(['file', 'path', 'directory', 'read', 'write', 'io'])
                elif rule.context_tag == "api-design":
                    terms.update(['api', 'http', 'request', 'response', 'endpoint', 'rest'])
                elif rule.context_tag == "testing":
                    terms.update(['test', 'assert', 'mock', 'fixture'])
                elif rule.context_tag == "concurrency":
                    terms.update(['async', 'thread', 'concurrent', 'parallel'])
                elif rule.context_tag == "error-handling":
                    terms.update(['error', 'exception', 'handle', 'catch'])
                    
            indicators[rule.context_tag] = terms
        
        # Add some that might not be in the rules but are in the old logic
        if "authentication" not in indicators:
            indicators["authentication"] = {'auth', 'login', 'password', 'security', 'user', 'permission'}
        
        return indicators
    
    def get_context_keywords(self, context_tag: str) -> Optional[Set[str]]:
        """
        Get the keywords associated with a specific context.
        
        Args:
            context_tag: The context to look up
            
        Returns:
            Set of keywords for the context, or None if not found
        """
        for rule in self.context_rules:
            if rule.context_tag == context_tag:
                return set(rule.keywords)
        
        # Check our derived indicators as fallback
        if context_tag in self._context_indicators:
            return self._context_indicators[context_tag]
        
        return None