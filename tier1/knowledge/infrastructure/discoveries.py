"""
Discovery domain models for structured analysis findings.

This module defines the data structures that represent concrete, verifiable
discoveries made during code analysis. This replaces simple string discoveries
with structured, actionable information.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum

from tier1.knowledge.infrastructure.reasoning_graph import FunctionArtifact


class Severity(Enum):
    """Severity levels for discoveries."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    def __lt__(self, other):
        """Allow severity comparison."""
        if not isinstance(other, Severity):
            return NotImplemented
        order = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4
        }
        return order[self] < order[other]


@dataclass
class Discovery:
    """
    Represents a concrete finding from code analysis.
    
    A Discovery contains structured information about an issue or insight
    found during analysis, including its type, severity, and specific metadata.
    
    Examples:
        Discovery(
            finding_id="MISSING_DOCSTRING",
            description="Function 'process_data' has no docstring",
            target_artifact=<FunctionArtifact>,
            severity=Severity.MEDIUM,
            metadata={'line_number': 42}
        )
    """
    finding_id: str
    description: str
    target_artifact: FunctionArtifact
    severity: Severity
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate discovery data."""
        if not self.finding_id:
            raise ValueError("Discovery must have a finding_id")
        if not self.description:
            raise ValueError("Discovery must have a description")
        if not self.target_artifact:
            raise ValueError("Discovery must have a target_artifact")
        if not isinstance(self.severity, Severity):
            raise ValueError(f"Severity must be a Severity enum, got {type(self.severity)}")
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the discovery."""
        return (f"[{self.severity.value}] {self.finding_id} in {self.target_artifact.function_name}: "
                f"{self.description}")
    
    def is_actionable(self) -> bool:
        """Check if this discovery represents an actionable issue."""
        # INFO level discoveries are typically not actionable
        return self.severity != Severity.INFO
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery to dictionary for serialization."""
        return {
            'finding_id': self.finding_id,
            'description': self.description,
            'function_name': self.target_artifact.function_name,
            'file_path': self.target_artifact.file_path,
            'severity': self.severity.value,
            'metadata': self.metadata
        }


# Common finding IDs for consistency
class FindingID:
    """Standard finding identifiers for common issues."""
    
    # Documentation issues
    MISSING_DOCSTRING = "MISSING_DOCSTRING"
    INCOMPLETE_PARAMETER_DOCS = "INCOMPLETE_PARAMETER_DOCS"
    MISSING_RETURN_DOC = "MISSING_RETURN_DOC"
    UNCLEAR_DOCSTRING = "UNCLEAR_DOCSTRING"
    
    # Complexity issues
    HIGH_CYCLOMATIC_COMPLEXITY = "HIGH_CYCLOMATIC_COMPLEXITY"
    LONG_FUNCTION = "LONG_FUNCTION"
    TOO_MANY_PARAMETERS = "TOO_MANY_PARAMETERS"
    DEEPLY_NESTED_CODE = "DEEPLY_NESTED_CODE"
    
    # Security issues
    HARDCODED_SECRET = "HARDCODED_SECRET"
    INSECURE_SSL_VERIFICATION = "INSECURE_SSL_VERIFICATION"
    SQL_INJECTION_RISK = "SQL_INJECTION_RISK"
    PATH_TRAVERSAL_RISK = "PATH_TRAVERSAL_RISK"
    
    # Code quality issues
    UNUSED_VARIABLE = "UNUSED_VARIABLE"
    UNUSED_IMPORT = "UNUSED_IMPORT"
    DUPLICATE_CODE = "DUPLICATE_CODE"
    MAGIC_NUMBER = "MAGIC_NUMBER"
    
    # Architecture issues
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    HIGH_COUPLING = "HIGH_COUPLING"
    LOW_COHESION = "LOW_COHESION"
    VIOLATION_OF_PRINCIPLE = "VIOLATION_OF_PRINCIPLE"