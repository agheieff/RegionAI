"""
Custom exceptions for the RegionAI domain.

This module defines project-specific exceptions that represent
various failure modes and error conditions in the RegionAI system.
"""


class RegionAIException(Exception):
    """Base exception for all RegionAI-specific errors."""


class ExponentialSearchException(RegionAIException):
    """
    Raised when a search process exhibits exponential growth behavior.
    
    This exception is used to abort searches that are consuming
    excessive computational resources, typically in proof search
    or planning algorithms.
    
    Attributes:
        message: Description of the exponential behavior
        elapsed_time: Time elapsed before detection (seconds)
        steps_taken: Number of steps taken before abort
        context: Additional context about the search state
    """
    
    def __init__(self, message: str, elapsed_time: float = 0.0, 
                 steps_taken: int = 0, context: dict = None):
        super().__init__(message)
        self.elapsed_time = elapsed_time
        self.steps_taken = steps_taken
        self.context = context or {}
        
    def __str__(self):
        base_msg = super().__str__()
        details = [base_msg]
        
        if self.elapsed_time > 0:
            details.append(f"Elapsed time: {self.elapsed_time:.2f}s")
            
        if self.steps_taken > 0:
            details.append(f"Steps taken: {self.steps_taken}")
            
        if self.context:
            details.append(f"Context: {self.context}")
            
        return " | ".join(details)


class ProofTimeoutException(RegionAIException):
    """
    Raised when a proof attempt exceeds the time budget.
    
    This is a specific case of resource exhaustion focused on
    time limits rather than exponential growth detection.
    """
    
    def __init__(self, message: str, timeout_limit: float, actual_time: float):
        super().__init__(message)
        self.timeout_limit = timeout_limit
        self.actual_time = actual_time
        
    def __str__(self):
        return (f"{super().__str__()} "
                f"(limit: {self.timeout_limit}s, actual: {self.actual_time:.2f}s)")


class InvalidProofStateException(RegionAIException):
    """
    Raised when a proof reaches an invalid or inconsistent state.
    
    This can happen when tactics produce malformed goals or when
    the proof state becomes corrupted.
    """


class HeuristicFailureException(RegionAIException):
    """
    Raised when a heuristic fails in an unexpected way.
    
    This is different from a heuristic simply not finding a solution;
    this represents a failure in the heuristic's execution itself.
    """
    
    def __init__(self, heuristic_name: str, message: str):
        super().__init__(message)
        self.heuristic_name = heuristic_name
        
    def __str__(self):
        return f"Heuristic '{self.heuristic_name}' failed: {super().__str__()}"


class ResourceExhaustionException(RegionAIException):
    """
    General exception for resource exhaustion scenarios.
    
    This covers memory limits, thread limits, or other system
    resource constraints.
    """
    
    def __init__(self, resource_type: str, message: str):
        super().__init__(message)
        self.resource_type = resource_type
        
    def __str__(self):
        return f"Resource exhaustion ({self.resource_type}): {super().__str__()}"


class ConfigurationException(RegionAIException):
    """
    Raised when there's an error in system configuration.
    
    This includes missing configuration values, invalid settings,
    or incompatible configuration combinations.
    """


class DiscoveryException(RegionAIException):
    """
    Raised when the discovery process encounters an error.
    
    This covers failures in transformation discovery, concept
    discovery, or pattern recognition.
    """


class AbstractInterpretationException(RegionAIException):
    """
    Raised when abstract interpretation fails.
    
    This includes failures in domain operations, fixpoint
    computation, or property verification.
    """


class LanguageParsingException(RegionAIException):
    """
    Raised when natural language parsing fails.
    
    This covers syntax errors, ambiguity resolution failures,
    or constraint generation errors.
    """
