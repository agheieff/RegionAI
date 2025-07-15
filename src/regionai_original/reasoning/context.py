"""
Analysis context for the RegionAI reasoning engine.

This module provides context information that allows the reasoning engine
to make sophisticated, situation-aware decisions about which heuristics
to apply.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class AnalysisContext:
    """
    Context information for guiding the reasoning engine's decisions.
    
    The context allows the engine to understand what type of problem it's
    analyzing and select heuristics that are most effective for that
    specific situation.
    """
    current_context_tag: str
    
    def __post_init__(self):
        """Validate the context tag."""
        if not self.current_context_tag:
            raise ValueError("current_context_tag cannot be empty")
        
        # Normalize the tag to lowercase for consistency
        self.current_context_tag = self.current_context_tag.lower()
    
    @classmethod
    def default(cls) -> 'AnalysisContext':
        """Create a default context for general analysis."""
        return cls(current_context_tag="default")
    
    @classmethod
    def for_domain(cls, domain: str) -> 'AnalysisContext':
        """Create a context for a specific domain."""
        return cls(current_context_tag=domain.lower())


@dataclass
class ContextRule:
    """
    A rule for detecting a specific context based on keywords in code.
    
    When any of the keywords are found in the code, this rule's context_tag
    is considered applicable.
    """
    context_tag: str
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate the rule."""
        if not self.context_tag:
            raise ValueError("context_tag cannot be empty")
        if not self.keywords:
            raise ValueError("keywords list cannot be empty")


class ContextDetector:
    """
    Automatically detects the appropriate AnalysisContext from code.
    
    This allows the reasoning engine to autonomously determine what type
    of code it's analyzing and select appropriate heuristics.
    """
    
    def __init__(self, rules: List[ContextRule]):
        """
        Initialize the detector with a set of rules.
        
        Args:
            rules: List of context detection rules
        """
        self.rules = rules
        if not rules:
            raise ValueError("ContextDetector requires at least one rule")
    
    def detect(self, code_snippet: str) -> AnalysisContext:
        """
        Detect the most appropriate context for the given code.
        
        Scans the code for keywords defined in the rules. The first
        rule with a matching keyword determines the context.
        
        Args:
            code_snippet: The source code to analyze
            
        Returns:
            The detected AnalysisContext
        """
        # Check each rule in order
        for rule in self.rules:
            for keyword in rule.keywords:
                if keyword in code_snippet:
                    return AnalysisContext(current_context_tag=rule.context_tag)
        
        # No matching rule found, return default context
        return AnalysisContext.default()