"""
Bayesian Updater service for modifying beliefs in the Knowledge Graph.

This module contains the core logic for taking new evidence and updating
the probabilistic belief distributions (alpha/beta parameters) for
concepts and relationships.
"""
from .graph import KnowledgeGraph, Concept, Relation


class BayesianUpdater:
    """
    Applies Bayesian updates to the beliefs within a KnowledgeGraph.
    """

    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        Initializes the updater with a reference to the graph it will modify.

        Args:
            knowledge_graph: The KnowledgeGraph instance to be updated.
        """
        self.kg = knowledge_graph

    def update_belief(
        self,
        source_concept: Concept,
        target_concept: Concept,
        relation: Relation,
        evidence_is_positive: bool,
        source_credibility: float
    ):
        """
        Updates the belief in a relationship based on new evidence.

        This is the core method for learning. It adjusts the alpha and beta
        parameters of a relationship's belief distribution.

        Args:
            source_concept: The source concept of the relationship.
            target_concept: The target concept of the relationship.
            relation: The type of the relationship.
            evidence_is_positive: True if the evidence supports the relationship,
                                 False if it contradicts it.
            source_credibility: A score from 0.0 to 1.0 representing the
                                trustworthiness of the evidence source.
        """
        # 1. Find the specific edge (relationship) in the graph
        edge_data = self.kg.graph.get_edge_data(source_concept, target_concept)
        
        if edge_data is None:
            # If the relationship doesn't exist, create it with initial priors
            self.kg.add_relation(source_concept, target_concept, relation)
            edge_data = self.kg.graph.get_edge_data(source_concept, target_concept)
        
        # Find the specific edge with the matching relation type
        metadata = None
        for key, data in edge_data.items():
            if data['label'] == relation:
                metadata = data['metadata']
                break
        
        if metadata is None:
            # This shouldn't happen if add_relation worked correctly
            raise ValueError(f"Could not find relationship {source_concept} -> {target_concept} ({relation})")
        
        # 2. Calculate the "strength" of the evidence
        # Base evidence weight of 1.0, multiplied by source credibility
        evidence_strength = 1.0 * source_credibility
        
        # 3. Update alpha or beta based on evidence polarity
        if evidence_is_positive:
            # Positive evidence increases alpha (supporting the relationship)
            metadata.alpha += evidence_strength
        else:
            # Negative evidence increases beta (contradicting the relationship)
            metadata.beta += evidence_strength
    
    def update_concept_belief(
        self,
        concept: Concept,
        evidence_type: str,
        source_credibility: float = 0.8
    ):
        """
        Updates the belief in a concept based on new evidence.
        
        This method adjusts the alpha and beta parameters of a concept's
        belief distribution when we find evidence of its existence.
        
        Args:
            concept: The concept to update
            evidence_type: Type of evidence (e.g., 'function_name_mention', 
                          'docstring_mention', 'comment_mention')
            source_credibility: A score from 0.0 to 1.0 representing the
                               trustworthiness of the evidence source
        """
        # Get concept metadata
        metadata = self.kg.get_concept_metadata(concept)
        
        if metadata is None:
            # If the concept doesn't exist, add it with initial priors
            from .graph import ConceptMetadata
            metadata = ConceptMetadata(
                discovery_method=evidence_type,
                alpha=1.0,  # Initial belief
                beta=1.0    # Initial disbelief
            )
            self.kg.add_concept(concept, metadata)
            metadata = self.kg.get_concept_metadata(concept)
        
        # Calculate evidence strength based on type
        base_strength = {
            'function_name_mention': 1.5,  # Strong evidence
            'docstring_mention': 1.0,      # Good evidence
            'comment_mention': 0.7,        # Moderate evidence
            'identifier_extraction': 0.5    # Weak evidence
        }.get(evidence_type, 0.5)
        
        evidence_strength = base_strength * source_credibility
        
        # For concept existence, we only have positive evidence
        # (finding a mention increases belief)
        metadata.alpha += evidence_strength
        
        # The confidence property is automatically calculated from alpha/beta
        # No need to set it explicitly
    
    def update_relationship_belief(
        self,
        concept1_name: str,
        concept2_name: str,
        evidence_type: str,
        source_credibility: float = 0.8
    ):
        """
        Updates the belief in a co-occurrence relationship between two concepts.
        
        This method creates or strengthens a "RELATED_TO" relationship between
        concepts that appear together in the same context.
        
        Args:
            concept1_name: Name of the first concept
            concept2_name: Name of the second concept
            evidence_type: Type of co-occurrence (e.g., 'co_occurrence_in_name',
                          'co_occurrence_in_docstring', 'co_occurrence_in_comment')
            source_credibility: A score from 0.0 to 1.0 representing the
                               trustworthiness of the evidence source
        """
        # Create concept objects
        concept1 = Concept(concept1_name)
        concept2 = Concept(concept2_name)
        
        # Ensure both concepts exist in the graph
        if concept1 not in self.kg:
            self.update_concept_belief(concept1, 'co_occurrence_discovery', source_credibility * 0.5)
        if concept2 not in self.kg:
            self.update_concept_belief(concept2, 'co_occurrence_discovery', source_credibility * 0.5)
        
        # Check if relationship already exists
        edge_data = self.kg.graph.get_edge_data(concept1, concept2)
        related_metadata = None
        
        if edge_data:
            # Look for existing RELATED_TO relationship
            for key, data in edge_data.items():
                if data['label'] == Relation('RELATED_TO'):
                    related_metadata = data['metadata']
                    break
        
        if related_metadata is None:
            # Create new RELATED_TO relationship
            from .graph import RelationMetadata
            related_metadata = RelationMetadata(
                relation_type='RELATED_TO',
                alpha=1.0,  # Initial belief
                beta=1.0    # Initial disbelief
            )
            self.kg.add_relation(
                concept1, 
                concept2, 
                Relation('RELATED_TO'),
                metadata=related_metadata,
                confidence=0.5,
                evidence=f"Co-occurrence: {concept1_name} and {concept2_name} found together"
            )
            # Refresh metadata reference
            edge_data = self.kg.graph.get_edge_data(concept1, concept2)
            for key, data in edge_data.items():
                if data['label'] == Relation('RELATED_TO'):
                    related_metadata = data['metadata']
                    break
        
        # Calculate evidence strength based on type
        base_strength = {
            'co_occurrence_in_name': 1.2,       # Strong evidence
            'co_occurrence_in_docstring': 0.8,  # Good evidence
            'co_occurrence_in_comment': 0.6,    # Moderate evidence
            'co_occurrence_in_code': 0.5        # Weak evidence
        }.get(evidence_type, 0.5)
        
        evidence_strength = base_strength * source_credibility
        
        # Update belief (co-occurrence is always positive evidence)
        related_metadata.alpha += evidence_strength
        
        # Also update in the reverse direction for undirected relationship
        reverse_edge_data = self.kg.graph.get_edge_data(concept2, concept1)
        if reverse_edge_data:
            for key, data in reverse_edge_data.items():
                if data['label'] == Relation('RELATED_TO'):
                    data['metadata'].alpha += evidence_strength
                    break
        else:
            # Create reverse relationship
            reverse_metadata = RelationMetadata(
                relation_type='RELATED_TO',
                alpha=1.0 + evidence_strength,
                beta=1.0
            )
            self.kg.add_relation(
                concept2,
                concept1,
                Relation('RELATED_TO'),
                metadata=reverse_metadata,
                confidence=(1.0 + evidence_strength) / (2.0 + evidence_strength),
                evidence=f"Co-occurrence: {concept2_name} and {concept1_name} found together"
            )
    
    def update_action_belief(
        self,
        concept_name: str,
        action_verb: str,
        evidence_type: str,
        source_credibility: float = 0.8
    ):
        """
        Updates the belief that a concept performs a specific action.
        
        This method creates or strengthens a "PERFORMS" relationship between
        a concept and an action verb, representing behavior understanding.
        
        Args:
            concept_name: Name of the concept performing the action
            action_verb: The action being performed (lemmatized verb)
            evidence_type: Type of evidence (e.g., 'method_call', 'function_name')
            source_credibility: A score from 0.0 to 1.0 representing the
                               trustworthiness of the evidence source
        """
        # Create concept and action objects
        concept = Concept(concept_name.title())
        action = Concept(action_verb.title())  # Actions are also concepts in the graph
        
        # Ensure both exist in the graph
        if concept not in self.kg:
            self.update_concept_belief(concept, 'action_discovery', source_credibility * 0.7)
        
        # Add action as a special type of concept
        if action not in self.kg:
            from .graph import ConceptMetadata
            action_metadata = ConceptMetadata(
                discovery_method='ACTION_VERB',
                alpha=1.0,
                beta=1.0,
                properties={'is_action': True, 'verb_form': action_verb}
            )
            self.kg.add_concept(action, action_metadata)
        
        # Check if PERFORMS relationship already exists
        edge_data = self.kg.graph.get_edge_data(concept, action)
        performs_metadata = None
        
        if edge_data:
            # Look for existing PERFORMS relationship
            for key, data in edge_data.items():
                if data['label'] == Relation('PERFORMS'):
                    performs_metadata = data['metadata']
                    break
        
        if performs_metadata is None:
            # Create new PERFORMS relationship
            from .graph import RelationMetadata
            performs_metadata = RelationMetadata(
                relation_type='PERFORMS',
                alpha=1.0,  # Initial belief
                beta=1.0    # Initial disbelief
            )
            self.kg.add_relation(
                concept,
                action,
                Relation('PERFORMS'),
                metadata=performs_metadata,
                confidence=0.5,
                evidence=f"{concept_name} performs action: {action_verb}"
            )
            # Refresh metadata reference
            edge_data = self.kg.graph.get_edge_data(concept, action)
            for key, data in edge_data.items():
                if data['label'] == Relation('PERFORMS'):
                    performs_metadata = data['metadata']
                    break
        
        # Calculate evidence strength based on type
        base_strength = {
            'method_call': 1.5,          # Very strong evidence
            'function_name': 1.2,        # Strong evidence
            'ast_analysis': 1.0,         # Good evidence
            'inferred_pattern': 0.7      # Moderate evidence
        }.get(evidence_type, 0.5)
        
        evidence_strength = base_strength * source_credibility
        
        # Update belief (performing action is always positive evidence)
        performs_metadata.alpha += evidence_strength