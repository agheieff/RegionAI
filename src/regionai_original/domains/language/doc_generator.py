"""
Documentation Generator using Knowledge Graph insights.

This module implements the ability to generate human-readable documentation
by leveraging the semantic understanding captured in the Knowledge Graph.
It represents the system's ability to explain its understanding of code.
"""
from typing import List, Tuple, Optional
from ..knowledge.graph import WorldKnowledgeGraph, Concept


class DocumentationGenerator:
    """
    Generates natural language documentation from a Knowledge Graph.
    
    This class represents RegionAI's ability to communicate its understanding
    of code structure and relationships back to humans in plain English.
    """
    
    def __init__(self, knowledge_graph: WorldKnowledgeGraph):
        """
        Initialize the documentation generator.
        
        Args:
            knowledge_graph: The enriched knowledge graph containing
                           concepts and their relationships
        """
        self.kg = knowledge_graph
    
    def generate_summary(self, function_name: str) -> str:
        """
        Generate a plain-English summary for a given function.
        
        This method analyzes the concepts related to a function and
        produces a human-readable description of what the function
        appears to be doing based on the knowledge graph.
        
        Args:
            function_name: Name of the function to summarize
            
        Returns:
            A human-readable summary of the function's purpose
        """
        # Find concepts related to this function
        related_concepts = self._find_function_concepts(function_name)
        
        if not related_concepts:
            return f"The function '{function_name}' has no identified concepts in the knowledge graph."
        
        # Sort by certainty score and take top 3-5
        top_concepts = related_concepts[:min(5, len(related_concepts))]
        
        # Generate summary based on number of concepts
        if len(top_concepts) == 1:
            concept_name, confidence = top_concepts[0]
            return (f"This function appears to be primarily concerned with "
                   f"the concept of {concept_name} (confidence: {confidence:.2f}).")
        
        elif len(top_concepts) == 2:
            return (f"This function appears to be primarily concerned with "
                   f"the concepts of {top_concepts[0][0]} and {top_concepts[1][0]}.")
        
        else:
            # Format list of concepts
            concept_list = ", ".join(c[0] for c in top_concepts[:-1])
            last_concept = top_concepts[-1][0]
            
            return (f"This function appears to be primarily concerned with "
                   f"the concepts of {concept_list}, and {last_concept}.")
    
    def _find_function_concepts(self, function_name: str) -> List[Tuple[str, float]]:
        """
        Find concepts related to a function based on the knowledge graph.
        
        This method searches for concepts that:
        1. Are extracted from the function name itself
        2. Are strongly related to concepts in the function name
        3. Have high co-occurrence with function-related concepts
        
        Args:
            function_name: The function name to analyze
            
        Returns:
            List of (concept_name, confidence) tuples sorted by confidence
        """
        # Extract potential concepts from the function name
        function_parts = self._split_function_name(function_name)
        
        related_concepts = {}
        
        # First, find direct concept matches from function parts
        for part in function_parts:
            # Try different variations including singular/plural
            variations = [
                part.title(),           # Title case
                part.lower(),           # Lower case
                part.upper(),           # Upper case
            ]
            
            # Add singular/plural variations
            if part.endswith('s'):
                # Try singular form
                singular = part[:-1]
                variations.extend([singular.title(), singular.lower(), singular.upper()])
            else:
                # Try plural form
                plural = part + 's'
                variations.extend([plural.title(), plural.lower(), plural.upper()])
            
            for variation in variations:
                concept = Concept(variation)
                if concept in self.kg:
                    metadata = self.kg.get_concept_metadata(concept)
                    if metadata:
                        # Direct match gets full confidence
                        related_concepts[str(concept)] = metadata.confidence
        
        # If no direct matches found, look for all concepts that might be related
        if not related_concepts:
            # Check all concepts in the graph
            for concept in self.kg.get_concepts():
                metadata = self.kg.get_concept_metadata(concept)
                if metadata:
                    # Check if this concept was discovered from this function
                    if function_name in metadata.source_functions:
                        related_concepts[str(concept)] = metadata.confidence
        
        # Then, find concepts related to the matched concepts
        for concept_name in list(related_concepts.keys()):
            concept = Concept(concept_name)
            relations = self.kg.get_relations_with_confidence(concept)
            
            for relation in relations:
                if str(relation['relation']) == "RELATED_TO":
                    target = str(relation['target'])
                    confidence = relation['confidence']
                    
                    # Add related concept with reduced confidence
                    if target not in related_concepts:
                        target_metadata = self.kg.get_concept_metadata(target)
                        if target_metadata:
                            # Weight by both relationship confidence and concept confidence
                            combined_confidence = confidence * target_metadata.confidence * 0.8
                            related_concepts[target] = combined_confidence
        
        # Sort by confidence and return as list of tuples
        sorted_concepts = sorted(
            related_concepts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_concepts
    
    def _split_function_name(self, function_name: str) -> List[str]:
        """
        Split a function name into meaningful parts.
        
        Handles both snake_case and camelCase naming conventions.
        
        Args:
            function_name: The function name to split
            
        Returns:
            List of individual words/parts
        """
        import re
        
        # First split by underscore (snake_case)
        parts = function_name.split('_')
        
        # Then split each part by camelCase
        all_parts = []
        for part in parts:
            # Find camelCase boundaries
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', part)
            if camel_parts:
                all_parts.extend(camel_parts)
            elif part:  # Keep the part if no camelCase found
                all_parts.append(part)
        
        # Filter out common prefixes like 'get', 'set', 'is'
        filtered_parts = []
        skip_words = {'get', 'set', 'is', 'has', 'create', 'update', 'delete', 'find'}
        for part in all_parts:
            if part.lower() not in skip_words:
                filtered_parts.append(part)
        
        return filtered_parts if filtered_parts else all_parts
    
    def generate_detailed_summary(self, function_name: str) -> str:
        """
        Generate a more detailed summary including relationships.
        
        This method provides a richer description by including information
        about how concepts relate to each other.
        
        Args:
            function_name: Name of the function to summarize
            
        Returns:
            A detailed human-readable summary
        """
        # Get basic summary first
        basic_summary = self.generate_summary(function_name)
        
        # Find concepts and their relationships
        related_concepts = self._find_function_concepts(function_name)
        
        if len(related_concepts) < 2:
            return basic_summary
        
        # Find relationships between top concepts
        top_concepts = related_concepts[:3]
        relationships = []
        
        for i, (concept1, _) in enumerate(top_concepts):
            for concept2, _ in top_concepts[i+1:]:
                # Check if there's a specific relationship
                rel_info = self._find_relationship(concept1, concept2)
                if rel_info:
                    relationships.append(rel_info)
        
        if not relationships:
            return basic_summary
        
        # Add relationship information
        rel_summary = " Additionally, "
        rel_descriptions = []
        
        for rel in relationships:
            if rel['type'] == 'HAS_MANY':
                rel_descriptions.append(f"{rel['source']} can have multiple {rel['target']}s")
            elif rel['type'] == 'BELONGS_TO':
                rel_descriptions.append(f"{rel['source']} belongs to {rel['target']}")
            elif rel['type'] == 'HAS_ONE':
                rel_descriptions.append(f"{rel['source']} has one {rel['target']}")
            elif rel['type'] == 'RELATED_TO':
                rel_descriptions.append(f"{rel['source']} is related to {rel['target']}")
        
        if rel_descriptions:
            rel_summary += " and ".join(rel_descriptions) + "."
            return basic_summary + rel_summary
        
        return basic_summary
    
    def _find_relationship(self, concept1: str, concept2: str) -> Optional[dict]:
        """
        Find the strongest relationship between two concepts.
        
        Args:
            concept1: First concept name
            concept2: Second concept name
            
        Returns:
            Dictionary with relationship info or None
        """
        c1 = Concept(concept1)
        c2 = Concept(concept2)
        
        # Check both directions
        relations = self.kg.get_relations_with_confidence(c1)
        
        best_relation = None
        best_confidence = 0
        
        for rel in relations:
            if str(rel['target']) == concept2:
                if rel['confidence'] > best_confidence:
                    best_confidence = rel['confidence']
                    best_relation = {
                        'source': concept1,
                        'target': concept2,
                        'type': str(rel['relation']),
                        'confidence': rel['confidence']
                    }
        
        # Also check reverse direction
        relations = self.kg.get_relations_with_confidence(c2)
        for rel in relations:
            if str(rel['target']) == concept1:
                if rel['confidence'] > best_confidence:
                    best_confidence = rel['confidence']
                    best_relation = {
                        'source': concept2,
                        'target': concept1,
                        'type': str(rel['relation']),
                        'confidence': rel['confidence']
                    }
        
        return best_relation
    
    def generate_behavioral_summary(self, function_name: str) -> str:
        """
        Generate a behavioral summary describing what actions the function performs.
        
        This method analyzes the concepts in a function and describes the key
        actions (verbs) associated with those concepts based on PERFORMS
        relationships in the knowledge graph.
        
        Args:
            function_name: Name of the function to summarize
            
        Returns:
            A human-readable summary describing the function's behavior
        """
        # Find concepts related to this function
        related_concepts = self._find_function_concepts(function_name)
        
        if not related_concepts:
            return f"The function '{function_name}' has no identified concepts or behaviors in the knowledge graph."
        
        # Take top 2-3 concepts
        top_concepts = related_concepts[:min(3, len(related_concepts))]
        
        # Build behavioral descriptions for each concept
        behavioral_parts = []
        
        for concept_name, concept_confidence in top_concepts:
            # Find actions this concept performs
            concept_actions = self._find_concept_actions(concept_name)
            
            if concept_actions:
                # Take top 1-2 actions
                top_actions = concept_actions[:min(2, len(concept_actions))]
                
                # Format action list
                if len(top_actions) == 1:
                    action_desc = f"'{top_actions[0][0]}'"
                else:
                    action_desc = f"'{top_actions[0][0]}' and '{top_actions[1][0]}'"
                
                # Build description for this concept
                part = f"the '{concept_name.lower()}' concept, which primarily performs the actions {action_desc}"
                behavioral_parts.append(part)
            else:
                # Concept has no known actions
                part = f"the '{concept_name.lower()}' concept"
                behavioral_parts.append(part)
        
        # Construct the full summary
        if not behavioral_parts:
            return self.generate_summary(function_name)  # Fallback to basic summary
        
        if len(behavioral_parts) == 1:
            return f"This function focuses on {behavioral_parts[0]}."
        elif len(behavioral_parts) == 2:
            return f"This function focuses on {behavioral_parts[0]}. It also involves {behavioral_parts[1]}."
        else:
            # Multiple concepts
            main_part = behavioral_parts[0]
            other_parts = behavioral_parts[1:]
            
            # Format the list of other concepts
            if len(other_parts) == 1:
                others_desc = other_parts[0]
            else:
                others_desc = ", ".join(other_parts[:-1]) + f", and {other_parts[-1]}"
            
            return f"This function focuses on {main_part}. It also involves {others_desc}."
    
    def _find_concept_actions(self, concept_name: str) -> List[Tuple[str, float]]:
        """
        Find actions performed by a concept, sorted by confidence.
        
        Args:
            concept_name: Name of the concept
            
        Returns:
            List of (action_name, confidence) tuples sorted by confidence
        """
        concept = Concept(concept_name)
        
        # Get all relationships for this concept
        relations = self.kg.get_relations_with_confidence(concept)
        
        # Filter for PERFORMS relationships
        performs_actions = []
        for rel in relations:
            if str(rel['relation']) == "PERFORMS":
                # Extract action name (target is an action concept)
                action_name = str(rel['target']).lower()
                confidence = rel['confidence']
                performs_actions.append((action_name, confidence))
        
        # Sort by confidence descending
        performs_actions.sort(key=lambda x: x[1], reverse=True)
        
        return performs_actions