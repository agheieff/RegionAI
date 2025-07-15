"""
Common interfaces and base types for the knowledge module.

This module contains shared types that are used across the knowledge
subsystem to avoid circular dependencies.
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class NaturalLanguageContext:
    """
    Natural language documentation and comments extracted from code.
    
    This is a simplified version to break circular dependencies.
    The full implementation remains in pipeline.documentation_extractor.
    """
    docstring: Optional[str] = None
    inline_comments: List[str] = None
    preceding_comment: Optional[str] = None
    
    def __post_init__(self):
        if self.inline_comments is None:
            self.inline_comments = []
            
    def to_string(self) -> str:
        """Convert all context to a single string."""
        parts = []
        if self.preceding_comment:
            parts.append(self.preceding_comment)
        if self.docstring:
            parts.append(self.docstring)
        if self.inline_comments:
            parts.extend(self.inline_comments)
        return "\n".join(parts)
    
    def is_empty(self) -> bool:
        """Check if this context contains any documentation."""
        return (not self.docstring and 
                not self.inline_comments and 
                not self.preceding_comment)