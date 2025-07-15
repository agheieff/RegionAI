"""
Utility updater service for adaptive heuristic utility adjustment.

This service implements a feedback mechanism that updates heuristic utility
scores based on their actual performance during plan execution. Successful
heuristics see their utilities increase, while unsuccessful ones decrease.
"""

from typing import Dict, Optional
import logging

from tier1.knowledge.infrastructure.reasoning_graph import Heuristic


logger = logging.getLogger(__name__)


class UtilityUpdater:
    """
    Updates heuristic utility scores based on execution feedback.
    
    This service implements a simple Bayesian-inspired update mechanism:
    - Success: Increase utility by moving it toward 1.0
    - Failure: Decrease utility by a multiplicative factor
    
    The updates are context-specific, allowing heuristics to have
    different utilities for different types of problems.
    """
    
    def __init__(self):
        """Initialize the updater with context-specific utilities."""
        # Track context-specific utilities for each heuristic
        # Format: {heuristic_name: {context: utility}}
        self.context_utilities: Dict[str, Dict[str, float]] = {}
        
        # Learning parameters
        self.success_rate = 0.1  # How much to increase on success
        self.failure_rate = 0.95  # Multiplicative factor on failure
    
    def update_heuristic_utility(self, heuristic: Heuristic, context: str, 
                                successful: bool) -> float:
        """
        Update a heuristic's utility based on execution outcome.
        
        Args:
            heuristic: The heuristic that was executed
            context: The context in which it was applied (e.g., "database-interaction")
            successful: Whether the heuristic found something meaningful
            
        Returns:
            The new utility value for this heuristic in this context
        """
        # Initialize tracking for this heuristic if needed
        if heuristic.name not in self.context_utilities:
            self.context_utilities[heuristic.name] = {}
        
        # Get current utility (use base utility if no context-specific one exists)
        current_utility = self.context_utilities[heuristic.name].get(
            context, heuristic.expected_utility
        )
        
        # Calculate new utility based on outcome
        if successful:
            # Success: Move utility toward 1.0
            # new_utility = old_utility + (1 - old_utility) * learning_rate
            new_utility = current_utility + (1.0 - current_utility) * self.success_rate
        else:
            # Failure: Reduce utility multiplicatively
            # This prevents utilities from dropping too quickly
            new_utility = current_utility * self.failure_rate
        
        # Ensure utility stays in valid range [0.1, 1.0]
        # We keep a minimum of 0.1 so heuristics are never completely abandoned
        new_utility = max(0.1, min(1.0, new_utility))
        
        # Store the updated utility
        self.context_utilities[heuristic.name][context] = new_utility
        
        return new_utility
    
    def get_context_utility(self, heuristic: Heuristic, context: str) -> float:
        """
        Get the current utility of a heuristic for a specific context.
        
        Args:
            heuristic: The heuristic to query
            context: The context to check
            
        Returns:
            The context-specific utility, or base utility if none exists
        """
        if heuristic.name in self.context_utilities:
            return self.context_utilities[heuristic.name].get(
                context, heuristic.expected_utility
            )
        return heuristic.expected_utility
    
    def get_all_utilities(self, heuristic_name: str) -> Dict[str, float]:
        """
        Get all context-specific utilities for a heuristic.
        
        Args:
            heuristic_name: Name of the heuristic
            
        Returns:
            Dictionary mapping contexts to utilities
        """
        return self.context_utilities.get(heuristic_name, {}).copy()
    
    def reset_utilities(self, heuristic_name: Optional[str] = None):
        """
        Reset utility scores to defaults.
        
        Args:
            heuristic_name: If provided, reset only this heuristic.
                          Otherwise, reset all heuristics.
        """
        if heuristic_name:
            if heuristic_name in self.context_utilities:
                del self.context_utilities[heuristic_name]
        else:
            self.context_utilities.clear()
    
    def get_learning_summary(self) -> str:
        """
        Get a summary of what the system has learned.
        
        Returns:
            Human-readable summary of utility adjustments
        """
        if not self.context_utilities:
            return "No learning has occurred yet."
        
        lines = ["Heuristic Learning Summary:"]
        lines.append("-" * 50)
        
        for heuristic_name, contexts in sorted(self.context_utilities.items()):
            lines.append(f"\n{heuristic_name}:")
            for context, utility in sorted(contexts.items()):
                lines.append(f"  {context}: {utility:.3f}")
        
        return "\n".join(lines)
    
    def get_effective_utility(self, heuristic: Heuristic, context: str) -> float:
        """
        Get the effective utility for planning purposes.
        
        This method returns the context-specific utility if available,
        otherwise falls back to the heuristic's base utility.
        
        Args:
            heuristic: The heuristic to query
            context: The context to check
            
        Returns:
            The effective utility value to use for planning
        """
        return self.get_context_utility(heuristic, context)
    
    def handle_exponential_failure(self, heuristic_name: str, context: str, 
                                  details: str = "") -> float:
        """
        Handle a heuristic that caused exponential search behavior.
        
        This applies a significant negative utility adjustment to discourage
        the use of this heuristic in similar contexts. The penalty is more
        severe than a normal failure.
        
        Args:
            heuristic_name: Name of the heuristic that caused the issue
            context: The context in which the exponential behavior occurred
            details: Additional details about the failure
            
        Returns:
            The new utility value after penalization
        """
        logger.warning(
            f"Penalizing heuristic '{heuristic_name}' for exponential behavior "
            f"in context '{context}': {details}"
        )
        
        # Initialize tracking if needed
        if heuristic_name not in self.context_utilities:
            self.context_utilities[heuristic_name] = {}
        
        # Get current utility (default to 0.5 if not set)
        current_utility = self.context_utilities[heuristic_name].get(context, 0.5)
        
        # Apply severe penalty: subtract 10 points worth of utility
        # This is much more severe than a normal failure
        penalty = 10.0
        new_utility = max(0.1, current_utility - penalty * 0.05)  # Scale penalty
        
        # Store the updated utility
        self.context_utilities[heuristic_name][context] = new_utility
        
        # Log the adjustment for tracking
        logger.info(
            f"Utility for '{heuristic_name}' in '{context}' adjusted: "
            f"{current_utility:.3f} -> {new_utility:.3f} (exponential penalty)"
        )
        
        return new_utility