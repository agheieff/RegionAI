"""
Action discovery coordination service.

This module coordinates the discovery of actions from code and their integration
into the knowledge graph as behavioral understanding.
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

from ..action_discoverer import ActionDiscoverer, DiscoveredAction
from ..bayesian_updater import BayesianUpdater
from ...config import RegionAIConfig, DEFAULT_CONFIG


@dataclass
class ActionDiscoveryResult:
    """Results from action discovery."""
    actions: List[DiscoveredAction]
    sequences: List[Tuple[DiscoveredAction, DiscoveredAction]]
    relationships_created: int


class ActionCoordinator:
    """
    Service for coordinating action discovery and integration.
    
    This class extracts the action discovery coordination logic from KnowledgeLinker,
    managing the process of finding actions in code and updating the knowledge graph.
    """
    
    def __init__(self, bayesian_updater: BayesianUpdater, config: RegionAIConfig = None):
        """
        Initialize the action coordinator.
        
        Args:
            bayesian_updater: Service for updating beliefs
            config: Configuration object
        """
        self.bayesian_updater = bayesian_updater
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Initialize action discoverer
        self.action_discoverer = ActionDiscoverer(self.config)
        
        # Track discovered actions for reporting
        self._discovered_actions: List[Dict[str, any]] = []
        self._discovered_sequences: List[Dict[str, any]] = []
    
    def discover_actions_from_code(self, source_code: str, function_name: str,
                                  base_confidence: float) -> ActionDiscoveryResult:
        """
        Discover actions performed in the function code.
        
        Args:
            source_code: The source code of the function
            function_name: Name of the function
            base_confidence: Base confidence from documentation quality
            
        Returns:
            ActionDiscoveryResult with discovered actions and sequences
        """
        # Parse AST once and discover both actions and sequences
        import ast
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            self.logger.warning(f"Failed to parse function {function_name}: {e}")
            return ActionDiscoveryResult(actions=[], sequences=[], relationships_created=0)
        
        # Find the function definition
        discovered_actions = []
        sequences = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Use the unified discovery method
                result = self.action_discoverer.discover_all_from_function_ast(node)
                discovered_actions = result['actions']
                sequences = result['sequences']
                break  # Only process the first function
        
        # Update beliefs for each action
        for action in discovered_actions:
            self._update_action_belief(action, function_name, base_confidence)
        
        relationships_created = 0
        if sequences:
            relationships_created = self._process_action_sequences(
                sequences, function_name, base_confidence
            )
        
        return ActionDiscoveryResult(
            actions=discovered_actions,
            sequences=sequences,
            relationships_created=relationships_created
        )
    
    def _update_action_belief(self, action: DiscoveredAction, function_name: str,
                             base_confidence: float):
        """
        Update belief in an action relationship.
        
        Args:
            action: The discovered action
            function_name: Name of the function where action was found
            base_confidence: Base confidence from documentation quality
        """
        # Update belief in the action relationship
        self.bayesian_updater.update_action_belief(
            action.concept,
            action.verb,
            'method_call' if '.' in action.method_name else 'function_name',
            base_confidence * action.confidence
        )
        
        # Track for reporting
        self._discovered_actions.append({
            'concept': action.concept,
            'action': action.verb,
            'method': action.method_name,
            'confidence': action.confidence * base_confidence,
            'source_function': function_name
        })
    
    def _process_action_sequences(self, sequences: List[Tuple[DiscoveredAction, DiscoveredAction]],
                                 function_name: str, base_confidence: float) -> int:
        """
        Process discovered action sequences to create PRECEDES relationships.
        
        Args:
            sequences: List of (action1, action2) tuples
            function_name: Name of the function where sequences were found
            base_confidence: Base confidence from documentation quality
            
        Returns:
            Number of sequence relationships created
        """
        relationships_created = 0
        
        for action1, action2 in sequences:
            # Create PRECEDES relationship between the actions
            combined_confidence = min(action1.confidence, action2.confidence) * base_confidence
            
            self.bayesian_updater.update_sequence_belief(
                action1.verb,
                action2.verb,
                'sequential_execution',
                combined_confidence
            )
            
            # Track for reporting
            self._discovered_sequences.append({
                'action1': action1.verb,
                'action2': action2.verb,
                'confidence': combined_confidence,
                'evidence': f"{action1.verb} -> {action2.verb} in {function_name}",
                'source_function': function_name
            })
            
            relationships_created += 1
        
        return relationships_created
    
    def get_discovered_actions(self) -> List[Dict[str, any]]:
        """Get list of all discovered actions for reporting."""
        return self._discovered_actions.copy()
    
    def get_discovered_sequences(self) -> List[Dict[str, any]]:
        """Get list of all discovered action sequences for reporting."""
        return self._discovered_sequences.copy()
    
    def clear_tracking(self):
        """Clear tracked discoveries (useful for testing)."""
        self._discovered_actions.clear()
        self._discovered_sequences.clear()