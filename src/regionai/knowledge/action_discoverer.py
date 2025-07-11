"""
Action Discovery from Code Analysis.

This module implements the ability to identify actions (verbs) performed
in code and link them to the concepts they operate on. It represents
RegionAI's understanding of behavior - not just what exists, but what happens.
"""
import ast
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
import logging

from ..language.nlp_extractor import NLPExtractor


@dataclass
class DiscoveredAction:
    """Represents an action discovered in code."""
    verb: str  # The action being performed (lemmatized)
    concept: str  # The concept being acted upon
    method_name: str  # The full method call (e.g., "save_to_db")
    confidence: float  # Confidence in this action inference
    
    def __str__(self):
        return f"{self.concept}.{self.verb}()"


class ActionDiscoverer:
    """
    Discovers actions (verbs) from function bodies by analyzing AST.
    
    This class traverses the Abstract Syntax Tree of functions to find
    method calls and extracts both the concept being acted upon and
    the action being performed.
    """
    
    def __init__(self):
        """Initialize the action discoverer."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize NLP extractor for verb analysis
        try:
            self.nlp_extractor = NLPExtractor()
        except OSError:
            self.logger.warning("spaCy model not found. Using fallback verb extraction.")
            self.nlp_extractor = None
        
        # Common action verbs in programming (fallback list)
        self.common_action_verbs = {
            'get', 'set', 'create', 'update', 'delete', 'save', 'load',
            'send', 'receive', 'process', 'validate', 'check', 'verify',
            'calculate', 'compute', 'filter', 'sort', 'search', 'find',
            'add', 'remove', 'insert', 'append', 'push', 'pop', 'clear',
            'open', 'close', 'read', 'write', 'connect', 'disconnect',
            'start', 'stop', 'run', 'execute', 'trigger', 'handle',
            'parse', 'format', 'encode', 'decode', 'encrypt', 'decrypt',
            'build', 'destroy', 'initialize', 'configure', 'setup'
        }
    
    def discover_actions(self, function_code: str, function_name: str) -> List[DiscoveredAction]:
        """
        Discover actions performed in a function by analyzing its AST.
        
        Args:
            function_code: The source code of the function
            function_name: Name of the function being analyzed
            
        Returns:
            List of discovered actions with their associated concepts
        """
        try:
            # Parse the code into an AST
            tree = ast.parse(function_code)
        except SyntaxError as e:
            self.logger.warning(f"Failed to parse function {function_name}: {e}")
            return []
        
        discovered_actions = []
        
        # Find all function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Analyze the function body
                actions = self._analyze_function_body(node)
                discovered_actions.extend(actions)
        
        # Also extract actions from the function name itself
        name_actions = self._extract_actions_from_name(function_name)
        discovered_actions.extend(name_actions)
        
        # Remove duplicates while preserving order
        unique_actions = []
        seen = set()
        for action in discovered_actions:
            key = (action.verb, action.concept)
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)
        
        return unique_actions
    
    def _analyze_function_body(self, func_node: ast.FunctionDef) -> List[DiscoveredAction]:
        """
        Analyze a function's body to find method calls and extract actions.
        
        Args:
            func_node: AST node representing the function
            
        Returns:
            List of discovered actions
        """
        actions = []
        
        # Walk through all nodes in the function body
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Handle method calls (e.g., obj.method())
                if isinstance(node.func, ast.Attribute):
                    action = self._extract_action_from_attribute(node.func)
                    if action:
                        actions.append(action)
                
                # Handle function calls that might indicate actions
                elif isinstance(node.func, ast.Name):
                    action = self._extract_action_from_function_call(node.func)
                    if action:
                        actions.append(action)
        
        return actions
    
    def _extract_action_from_attribute(self, attr_node: ast.Attribute) -> Optional[DiscoveredAction]:
        """
        Extract action from an attribute access (e.g., customer.save()).
        
        Args:
            attr_node: AST Attribute node
            
        Returns:
            DiscoveredAction or None
        """
        method_name = attr_node.attr
        
        # Extract the concept (object being acted upon)
        concept = self._extract_concept_from_value(attr_node.value)
        if not concept:
            return None
        
        # Extract verb from method name
        verbs = self._extract_verbs_from_method_name(method_name)
        if not verbs:
            return None
        
        # Use the first/primary verb
        primary_verb = verbs[0]
        
        # Calculate confidence based on how clear the action is
        confidence = self._calculate_action_confidence(primary_verb, method_name)
        
        return DiscoveredAction(
            verb=primary_verb,
            concept=concept,
            method_name=method_name,
            confidence=confidence
        )
    
    def _extract_concept_from_value(self, value_node) -> Optional[str]:
        """
        Extract the concept name from an AST value node.
        
        Args:
            value_node: AST node representing the object
            
        Returns:
            Concept name or None
        """
        if isinstance(value_node, ast.Name):
            # Direct variable reference (e.g., customer)
            return value_node.id.lower()
        elif isinstance(value_node, ast.Attribute):
            # Chained attribute (e.g., self.customer)
            return value_node.attr.lower()
        elif isinstance(value_node, ast.Subscript):
            # Subscript access (e.g., customers[0])
            if isinstance(value_node.value, ast.Name):
                name = value_node.value.id.lower()
                # Remove plural 's' to get singular concept
                if name.endswith('s'):
                    return name[:-1]
                return name
        
        return None
    
    def _extract_verbs_from_method_name(self, method_name: str) -> List[str]:
        """
        Extract verbs from a method name.
        
        Args:
            method_name: Name of the method (e.g., "save_to_database")
            
        Returns:
            List of lemmatized verbs
        """
        if self.nlp_extractor:
            verbs = self.nlp_extractor.extract_verbs_from_identifier(method_name)
            if verbs:
                return verbs
        
        # Fallback: Check against common verbs
        method_lower = method_name.lower()
        found_verbs = []
        
        for verb in self.common_action_verbs:
            if method_lower.startswith(verb):
                found_verbs.append(verb)
                break
            elif f"_{verb}_" in method_lower or method_lower.endswith(f"_{verb}"):
                found_verbs.append(verb)
        
        return found_verbs if found_verbs else [method_lower.split('_')[0]]
    
    def _extract_action_from_function_call(self, name_node: ast.Name) -> Optional[DiscoveredAction]:
        """
        Extract action from a direct function call (e.g., save_user()).
        
        Args:
            name_node: AST Name node
            
        Returns:
            DiscoveredAction or None
        """
        func_name = name_node.id
        
        # Try to extract verb and concept from function name
        parts = func_name.lower().split('_')
        if len(parts) < 2:
            return None
        
        # Common pattern: verb_concept (e.g., save_user)
        potential_verb = parts[0]
        potential_concept = '_'.join(parts[1:])
        
        if potential_verb in self.common_action_verbs:
            return DiscoveredAction(
                verb=potential_verb,
                concept=potential_concept,
                method_name=func_name,
                confidence=0.7  # Lower confidence for inferred pattern
            )
        
        return None
    
    def _extract_actions_from_name(self, function_name: str) -> List[DiscoveredAction]:
        """
        Extract actions from the function name itself.
        
        Args:
            function_name: Name of the function
            
        Returns:
            List of discovered actions
        """
        actions = []
        
        # Extract verbs from function name
        if self.nlp_extractor:
            verbs = self.nlp_extractor.extract_verbs_from_identifier(function_name)
            nouns = self.nlp_extractor.extract_nouns_from_identifier(function_name)
            
            # Try to pair verbs with nouns
            for verb in verbs:
                for noun in nouns:
                    actions.append(DiscoveredAction(
                        verb=verb,
                        concept=noun,
                        method_name=function_name,
                        confidence=0.8  # Good confidence for function name patterns
                    ))
        
        # Fallback pattern matching
        if not actions:
            parts = function_name.lower().split('_')
            if len(parts) >= 2 and parts[0] in self.common_action_verbs:
                concept = '_'.join(parts[1:])
                actions.append(DiscoveredAction(
                    verb=parts[0],
                    concept=concept,
                    method_name=function_name,
                    confidence=0.7
                ))
        
        return actions
    
    def _calculate_action_confidence(self, verb: str, method_name: str) -> float:
        """
        Calculate confidence score for an action inference.
        
        Args:
            verb: The extracted verb
            method_name: The full method name
            
        Returns:
            Confidence score between 0 and 1
        """
        # Higher confidence if verb is at the start of method name
        if method_name.lower().startswith(verb):
            return 0.9
        
        # Good confidence if verb is clearly separated
        if f"_{verb}_" in method_name.lower() or method_name.lower().endswith(f"_{verb}"):
            return 0.8
        
        # Medium confidence if verb is a common action
        if verb in self.common_action_verbs:
            return 0.7
        
        # Lower confidence otherwise
        return 0.6