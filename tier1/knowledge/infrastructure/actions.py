"""
Action domain models for autonomous code generation.

This module defines the data structures that represent code fixes and
modifications. These models enable RegionAI to transition from passive
analysis to active code generation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

from tier1.knowledge.infrastructure.reasoning_graph import FunctionArtifact


@dataclass
class FixSuggestion:
    """
    Represents a suggested fix for a detected vulnerability or issue.
    
    A FixSuggestion contains all the information needed to generate
    a code fix, including the type of vulnerability, affected function,
    and specific context data required for the fix.
    
    Examples:
        FixSuggestion(
            vulnerability_id="INSECURE_SSL_VERIFICATION",
            description="SSL verification is disabled, making the connection insecure",
            target_artifact=<FunctionArtifact for make_request>,
            context_data={'parameter_name': 'verify', 'safe_value': True}
        )
    """
    vulnerability_id: str
    description: str
    target_artifact: FunctionArtifact
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fix suggestion data."""
        if not self.vulnerability_id:
            raise ValueError("FixSuggestion must have a vulnerability_id")
        if not self.description:
            raise ValueError("FixSuggestion must have a description")
        if not self.target_artifact:
            raise ValueError("FixSuggestion must have a target_artifact")
        
        # Ensure we have source code to work with
        if not hasattr(self.target_artifact, 'source_code') or not self.target_artifact.source_code:
            raise ValueError("Target artifact must have source code for fix generation")
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the fix."""
        return (f"Fix for {self.vulnerability_id} in {self.target_artifact.function_name}: "
                f"{self.description}")


@dataclass
class GeneratedFix:
    """
    Represents the result of code generation for a fix.
    
    This encapsulates the modified source code along with metadata
    about what was changed and why.
    """
    original_suggestion: FixSuggestion
    modified_source: str
    changes_made: list[str] = field(default_factory=list)
    
    def add_change(self, change_description: str):
        """Add a description of a change that was made."""
        self.changes_made.append(change_description)
    
    def get_summary(self) -> str:
        """Get a summary of the generated fix."""
        changes_str = "\n  - ".join(self.changes_made) if self.changes_made else "No changes"
        return (f"Generated fix for {self.original_suggestion.target_artifact.function_name}:\n"
                f"  - {changes_str}")